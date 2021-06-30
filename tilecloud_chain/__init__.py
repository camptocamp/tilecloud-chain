from argparse import ArgumentParser, Namespace
import collections
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from fractions import Fraction
from hashlib import sha1
from io import BytesIO
from itertools import product
import json
import logging
import logging.config
from math import ceil, sqrt
import os
import pkgutil
import queue
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    TextIO,
    Tuple,
    Union,
    cast,
)

from PIL import Image
import boto3
import botocore.client
from c2cwsgiutils import sentry, stats
from jsonschema_gentypes import validate
import psycopg2
from ruamel.yaml import YAML  # type: ignore
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon
from shapely.ops import cascaded_union
from shapely.wkb import loads as loads_wkb
from typing_extensions import TypedDict

from tilecloud import BoundingPyramid, Tile, TileCoord, TileGrid, TileStore, consume
from tilecloud.filter.error import LogErrors, MaximumConsecutiveErrors
from tilecloud.filter.logger import Logger
from tilecloud.grid.free import FreeTileGrid
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.store.mbtiles import MBTilesTileStore
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.store.redis import RedisTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.sqs import SQSTileStore, maybe_stop
import tilecloud_chain.configuration
from tilecloud_chain.multitilestore import MultiTileStore
from tilecloud_chain.timedtilestore import TimedTileStoreWrapper

logger = logging.getLogger(__name__)


def formated_metadata(tile: Tile) -> str:
    metadata = dict(tile.metadata)
    if "tiles" in metadata:
        metadata["tiles"] = metadata["tiles"].keys()  # type: ignore
    return " ".join([f"{k}={metadata[k]}" for k in sorted(metadata.keys())])


setattr(Tile, "formated_metadata", property(formated_metadata))


def add_comon_options(
    parser: ArgumentParser,
    tile_pyramid: bool = True,
    no_geom: bool = True,
    near: bool = True,
    time: bool = True,  # pylint: disable=redefined-outer-name
    dimensions: bool = False,
    cache: bool = True,
) -> None:
    parser.add_argument(
        "-c",
        "--config",
        default=os.environ.get("TILEGENERATION_CONFIGFILE", "tilegeneration/config.yaml"),
        help="path to the configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--ignore-error",
        action="store_true",
        help="continue if there is an error in the configuration",
    )
    parser.add_argument("-l", "--layer", metavar="NAME", help="the layer to generate")
    if tile_pyramid:
        parser.add_argument(
            "-b",
            "--bbox",
            nargs=4,
            type=float,
            metavar=("MINX", "MINY", "MAXX", "MAXY"),
            help="restrict to specified bounding box",
        )
        parser.add_argument(
            "-z",
            "--zoom",
            help="restrict to specified zoom level, or a zooms range (2-5), or a zooms list (2,4,5)",
        )
        parser.add_argument(
            "-t", "--test", type=int, help="test with generating N tiles, and add log messages", metavar="N"
        )
        if near:
            parser.add_argument(
                "--near",
                type=float,
                nargs=2,
                metavar=("X", "Y"),
                help="This option is a good replacement of --bbox, to used with "
                "--time or --test and --zoom, implies --no-geom. "
                "It automatically measure a bbox around the X Y position that corresponds to the metatiles.",
            )
        if time:
            parser.add_argument(
                "--time",
                "--measure-generation-time",
                dest="time",
                metavar="N",
                type=int,
                help="Measure the generation time by creating N tiles to warm-up, "
                "N tile to do the measure and N tiles to slow-down",
            )
    if no_geom:
        parser.add_argument(
            "--no-geom",
            default=True,
            action="store_false",
            dest="geom",
            help="Don't the geometry available in the SQL",
        )
    if dimensions:
        parser.add_argument(
            "--dimensions",
            nargs="+",
            metavar="DIMENSION=VALUE",
            default=[],
            help="overwrite the dimensions values specified in the config file",
        )
    if cache:
        parser.add_argument("--cache", dest="cache", metavar="NAME", help="The cache name to use")
    parser.add_argument(
        "--logging-configuration-file",
        help="Configuration file for Python logging.",
        default="/app/production.ini",
    )
    parser.add_argument("-q", "--quiet", default=False, action="store_true", help="Display only errors.")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="Display info message.")
    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action="store_true",
        help="Display debug message, and stop on first error.",
    )


def get_tile_matrix_identifier(
    grid: tilecloud_chain.configuration.Grid, resolution: Optional[float] = None, zoom: Optional[int] = None
) -> str:
    if grid is None or grid["matrix_identifier"] == "zoom":
        return str(zoom)
    else:
        assert zoom is not None
        if resolution is None:
            resolution = grid["resolutions"][zoom]
        if int(resolution) == resolution:
            return str(int(resolution))
        else:
            return str(resolution).replace(".", "_")


class Run:
    _re_rm_xml_tag = re.compile("(<[^>]*>|\n)")

    def __init__(
        self,
        gene: "TileGeneration",
        functions: List[Callable[[Tile], Tile]],
        queue_store: Optional[Any] = None,
    ) -> None:
        self.gene = gene
        self.functions = functions
        self.safe = gene.options is None or not gene.options.debug
        daemon = gene.options is not None and getattr(gene.options, "daemon", False)
        self.max_consecutive_errors = (
            MaximumConsecutiveErrors(gene.config["generation"]["maxconsecutive_errors"])
            if not daemon and gene.maxconsecutive_errors
            else None
        )
        self.queue_store = queue_store
        self.error = 0
        self.error_lock = threading.Lock()
        self.error_logger = LogErrors(
            logger, logging.ERROR, "Error in tile: %(tilecoord)s, %(formated_metadata)s, %(error)r"
        )

    def __call__(self, tile: Optional[Tile]) -> Optional[Tile]:
        if tile is None:
            return None

        if "tiles" in tile.metadata:
            tile.metadata["tiles"][tile.tilecoord] = tile  # type: ignore

        tilecoord = tile.tilecoord
        logger.debug("[%s] Metadata: %s", tilecoord, tile.formated_metadata)
        for func in self.functions:
            try:
                logger.debug("[%s] Run: %s", tilecoord, func)
                n = datetime.now()
                if self.safe:
                    try:
                        tile = func(tile)
                    except Exception as e:
                        logger.exception("[%s] Fail to process function %s", tilecoord, func)
                        tile.error = e
                else:
                    tile = func(tile)
                if getattr(func, "time_message", None) is not None:
                    logger.debug("[%s] %s in %s", tilecoord, func.time_message, str(datetime.now() - n))  # type: ignore
                if tile is None:
                    logger.debug("[%s] Drop", tilecoord)
                    return None
                if tile.error:
                    if tile.content_type and tile.content_type.startswith("application/vnd.ogc.se_xml"):
                        assert isinstance(tile.error, str)
                        tile.error = "WMS server error: {}".format(self._re_rm_xml_tag.sub("", tile.error))
                    logger.warning("Error with tile %s:\n%s", tile.tilecoord, tile.error)
                    if stats.BACKENDS:
                        stats.increment_counter(["error", tile.metadata.get("layer", "None")])

                    if "error_file" in self.gene.config["generation"]:
                        self.gene.log_tiles_error(tile=tile, message=repr(tile.error))

                    if self.max_consecutive_errors is not None:
                        self.max_consecutive_errors(tile)

                    if self.queue_store is not None:
                        self.queue_store.delete_one(tile)
                    with self.error_lock:
                        self.error += 1
                    return tile
            except Exception:
                logger.exception("Run error")
                raise

        if self.max_consecutive_errors is not None:
            self.max_consecutive_errors(tile)

        return tile


class Close:
    def __init__(self, db: Any) -> None:
        self.db = db

    def __call__(self) -> None:
        self.db.close()


class Legend(TypedDict, total=False):
    mime_type: str
    href: str
    max_resolution: float
    min_resolution: float
    width: int
    height: int


class TileGeneration:
    _geom = None
    tilestream: Optional[Iterator[Tile]] = None
    duration: timedelta = timedelta()
    error = 0
    queue_store = None
    daemon = False
    config: tilecloud_chain.configuration.Configuration

    def __init__(
        self,
        config_file: str,
        options: Optional[Namespace] = None,
        layer_name: Optional[str] = None,
        base_config: Optional[tilecloud_chain.configuration.Configuration] = None,
        configure_logging: bool = True,
        multi_thread: bool = True,
        maxconsecutive_errors: bool = True,
    ):
        self.geoms: Dict[str, Dict[Union[str, int], BaseGeometry]] = {}
        self._close_actions: List["Close"] = []
        self._layers_geoms: Dict[str, BaseGeometry] = {}
        self.error_lock = threading.Lock()
        self.error_files_: Dict[str, TextIO] = {}
        self.functions_tiles: List[Callable[[Tile], Tile]] = []
        self.functions_metatiles: List[Callable[[Tile], Tile]] = []
        self.functions = self.functions_metatiles
        self.metatilesplitter_thread_pool: Optional[ThreadPoolExecutor] = None
        self.multi_thread = multi_thread
        self.maxconsecutive_errors = maxconsecutive_errors
        self.grid_obj: Dict[str, TileGrid] = {}
        self.layer_legends: Dict[str, List[Legend]] = {}

        self.options: Namespace = options or collections.namedtuple(  # type: ignore
            "Options",
            ["verbose", "debug", "quiet", "bbox", "zoom", "test", "near", "time", "geom", "ignore_error"],
        )(
            False, False, False, None, None, None, None, None, True, False  # type: ignore
        )
        del options
        if not hasattr(self.options, "bbox"):
            self.options.bbox = None
        if not hasattr(self.options, "zoom"):
            self.options.zoom = None
        if not hasattr(self.options, "test"):
            self.options.test = None
        if not hasattr(self.options, "near"):
            self.options.near = None
        if not hasattr(self.options, "time"):
            self.options.time = None
        if not hasattr(self.options, "geom"):
            self.options.geom = True
        if not hasattr(self.options, "ignore_error"):
            self.options.ignore_error = False

        if configure_logging:
            self._configure_logging(self.options, "%(levelname)s:%(name)s:%(funcName)s:%(message)s")

        with open(config_file) as f:
            self.config = {}
            self.config.update({} if base_config is None else base_config)
            ruamel = YAML()
            self.config.update(ruamel.load(f))

        self.validate_config(config_file, self.options.ignore_error)

        error = False
        self.grids = self.config["grids"]
        for gname, grid in sorted(self.grids.items()):
            if "resolution_scale" in grid:
                scale = grid["resolution_scale"]
                for resolution in grid["resolutions"]:
                    if resolution * scale % 1 != 0.0:
                        logger.error(
                            "The resolution %s * resolution_scale %s is not an integer.", resolution, scale
                        )
                        error = True
            else:
                grid["resolution_scale"] = self._resolution_scale(grid["resolutions"])

            srs = int(grid["srs"].split(":")[1])
            if "proj4_literal" not in grid:
                if srs == 3857:
                    grid["proj4_literal"] = (
                        "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 "
                        "+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over"
                    )
                elif srs == 21781:
                    grid["proj4_literal"] = (
                        "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 "
                        "+x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 "
                        "+units=m +no_defs"
                    )
                elif srs == 2056:
                    grid["proj4_literal"] = (
                        "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 "
                        "+x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 "
                        "+units=m +no_defs"
                    )
                else:
                    grid["proj4_literal"] = "+init={}".format(grid["srs"])

            scale = grid["resolution_scale"]
            if not error:
                self.grid_obj[gname] = FreeTileGrid(
                    resolutions=cast(List[int], [r * scale for r in grid["resolutions"]]),
                    scale=scale,
                    max_extent=cast(Tuple[int, int, int, int], grid["bbox"]),
                    tile_size=grid["tile_size"],
                )

        self.layers = self.config["layers"]
        for lname, layer in sorted(self.layers.items()):
            if "headers" not in layer and layer["type"] == "wms":
                layer["headers"] = {
                    "Cache-Control": "no-cache, no-store",
                    "Pragma": "no-cache",
                }
            if layer["type"] == "mapnik" and layer.get("output_format", "png") == "grid" and layer["meta"]:
                logger.error("The layer '%s' is of type Mapnik/Grid, that can't support matatiles.", lname)
                error = True

        self.caches = self.config["caches"]
        self.metadata = self.config.get("metadata")
        self.provider = self.config.get("provider")

        if error:
            sys.exit(1)

        if configure_logging and "log_format" in self.config.get("generation", {}):
            self._configure_logging(self.options, self.config["generation"]["log_format"])

        if self.options is not None and self.options.zoom is not None:
            error_message = (
                "The zoom argument '%s' has incorrect format, "
                "it can be a single value, a range (3-9), a list of values (2,5,7)."
            ) % self.options.zoom
            if self.options.zoom.find("-") >= 0:
                splitted_zoom: List[str] = self.options.zoom.split("-")
                if len(splitted_zoom) != 2:
                    logger.error(error_message)
                    error = True
                try:
                    self.options.zoom = range(int(splitted_zoom[0]), int(splitted_zoom[1]) + 1)
                except ValueError:
                    logger.error(error_message, exc_info=True)
                    error = True
            elif self.options.zoom.find(",") >= 0:
                try:
                    self.options.zoom = [int(z) for z in self.options.zoom.split(",")]
                except ValueError:
                    logger.error(error_message, exc_info=True)
                    error = True
            else:
                try:
                    self.options.zoom = [int(self.options.zoom)]
                except ValueError:
                    logger.error(error_message, exc_info=True)
                    error = True

        if error:
            sys.exit(1)

        if layer_name and not error:
            self.init_layer(layer_name, self.options)

    def validate_config(self, config_file: str, ignore_error: bool) -> None:
        # Generate base structure
        if "defaults" in self.config:
            del self.config["defaults"]
        if "generation" not in self.config:
            self.config["generation"] = {}
        if "cost" in self.config:
            if "s3" not in self.config["cost"]:
                self.config["cost"]["s3"] = {}
            if "cloudfront" not in self.config["cost"]:
                self.config["cost"]["cloudfront"] = {}
            if "sqs" not in self.config["cost"]:
                self.config["cost"]["sqs"] = {}

        schema_data = pkgutil.get_data("tilecloud_chain", "schema.json")
        assert schema_data
        errors, _ = validate.validate(
            config_file, cast(Dict[str, Any], self.config), json.loads(schema_data), default=True
        )

        if errors:
            logger.error("The config file is invalid:\n%s", "\n".join(errors))
            if not (
                ignore_error
                or os.environ.get("TILEGENERATION_IGNORE_CONFIG_ERROR", "FALSE").lower() == "true"
            ):
                sys.exit(1)

    def init(self, queue_store: Optional[Any] = None, daemon: bool = False) -> None:
        self.queue_store = queue_store
        self.daemon = daemon

    @staticmethod
    def _primefactors(x: int) -> List[int]:
        factorlist = []
        loop = 2
        while loop <= x:
            if x % loop == 0:
                x = round(x / loop)
                factorlist.append(loop)
            else:
                loop += 1
        return factorlist

    def _resolution_scale(self, resolutions: Union[List[float], List[int]]) -> int:
        prime_fact = {}
        for resolution in resolutions:
            denominator = Fraction(str(resolution)).denominator
            prime_factors = self._primefactors(denominator)
            for factor in set(prime_factors):
                if factor not in prime_fact:
                    prime_fact[factor] = 0

                prime_fact[factor] = max(prime_fact[factor], len([f for f in prime_factors if f == factor]))

        result = 1
        for fact, nb in prime_fact.items():
            result *= fact ** nb
        return result

    @staticmethod
    def _configure_logging(options: Namespace, format_: str) -> None:
        if os.environ.get("CI", "false").lower() == "true":
            pass
        elif (
            options is not None
            and options.logging_configuration_file
            and os.path.exists(options.logging_configuration_file)
        ):  # pragma: nocover
            logging.config.fileConfig(options.logging_configuration_file, defaults=dict(os.environ))
        else:  # pragma: nocover
            level = logging.WARNING
            other_level = logging.CRITICAL
            if options is not None and options.quiet:
                level = logging.ERROR
            elif options is not None and options.verbose:
                level = logging.INFO
            elif options is not None and options.debug:
                level = logging.DEBUG
                other_level = logging.INFO
            logging.config.dictConfig(
                {
                    "version": 1,
                    "disable_existing_loggers": False,  # Without that, existing loggers are silent
                    "loggers": {"tilecloud": {"level": level}, "tilecloud_chain": {"level": level}},
                    "root": {"level": other_level, "handlers": [os.environ.get("LOG_TYPE", "console")]},
                    "handlers": {
                        "console": {
                            "class": "logging.StreamHandler",
                            "formatter": "default",
                            "stream": "ext://sys.stdout",
                        },
                        "json": {
                            "class": "c2cwsgiutils.pyramid_logging.JsonLogHandler",
                            "stream": "ext://sys.stdout",
                        },
                    },
                    "formatters": {"default": {"format": format_}},
                }
            )
        if os.environ.get("CI", "false").lower() != "true":
            sentry.init()

    def get_all_dimensions(self, layer: tilecloud_chain.configuration.Layer) -> List[Dict[str, str]]:
        assert layer is not None

        options_dimensions = {}
        for opt_dim in self.options.dimensions:
            opt_dim = opt_dim.split("=")
            if len(opt_dim) != 2:
                sys.exit("the DIMENSIONS option should be like this DATE=2013 VERSION=13.")
            options_dimensions[opt_dim[0]] = opt_dim[1]

        all_dimensions = [
            [(dim["name"], d) for d in dim["generate"]]
            for dim in layer.get("dimensions", [])
            if dim["name"] not in options_dimensions
        ]
        all_dimensions += [[p] for p in options_dimensions.items()]
        return [{}] if len(all_dimensions) == 0 else [dict(d) for d in product(*all_dimensions)]

    def get_store(
        self, cache: tilecloud_chain.configuration.Cache, layer_name: str, read_only: bool = False
    ) -> TileStore:
        layer = self.config["layers"][layer_name]
        grid = self.config["grids"][layer["grid"]]
        layout = WMTSTileLayout(
            layer=layer_name,
            url=cache["folder"],
            style=layer["wmts_style"],
            format="." + layer["extension"],
            dimensions_name=[dimension["name"] for dimension in layer.get("dimensions", [])],
            tile_matrix_set=layer["grid"],
            tile_matrix=lambda z: get_tile_matrix_identifier(grid, zoom=z),  # type: ignore
            request_encoding="REST",
        )
        # store
        if cache["type"] == "s3":
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
            # on s3
            cache_tilestore: TileStore = S3TileStore(
                cache_s3["bucket"],
                layout,  # type: ignore
                s3_host=cache.get("host", "s3-eu-west-1.amazonaws.com"),
                cache_control=cache.get("cache_control"),
            )
        elif cache["type"] == "mbtiles":
            metadata = {}
            for dimension in layer["dimensions"]:
                metadata["dimension_" + dimension["name"]] = dimension["default"]
            # on mbtiles file
            filename = (
                layout.filename(TileCoord(0, 0, 0), metadata=metadata).replace("/0/0/0", "") + ".mbtiles"
            )
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            cache_tilestore = MBTilesTileStore(
                sqlite3.connect(filename),
                content_type=layer["mime_type"],
                tilecoord_in_topleft=True,
            )
        elif cache["type"] == "bsddb":
            metadata = {}
            for dimension in layer["dimensions"]:
                metadata["dimension_" + dimension["name"]] = dimension["default"]
            import bsddb3 as bsddb  # pylint: disable=import-outside-toplevel,import-error

            from tilecloud.store.bsddb import BSDDBTileStore  # pylint: disable=import-outside-toplevel

            # on bsddb file
            filename = layout.filename(TileCoord(0, 0, 0), metadata=metadata).replace("/0/0/0", "") + ".bsddb"
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            db = bsddb.hashopen(
                filename,
                # and os.path.exists(filename) to avoid error on non existing file
                "r" if read_only and os.path.exists(filename) else "c",
            )

            self._close_actions.append(Close(db))

            cache_tilestore = BSDDBTileStore(
                db,
                content_type=layer["mime_type"],
            )
        elif cache["type"] == "filesystem":
            # on filesystem
            cache_tilestore = FilesystemTileStore(
                layout,
                content_type=layer["mime_type"],
            )
        else:
            sys.exit("unknown cache type: " + cache["type"])

        return cache_tilestore

    def init_layer(self, layer_name: str, options: Namespace) -> None:
        layer = self.config["layers"][layer_name]
        self.create_log_tiles_error(layer_name)

        if options.near is not None or (
            options.time is not None and "bbox" in layer and options.zoom is not None
        ):
            if options.zoom is None or len(options.zoom) != 1:
                sys.exit("Option --near needs the option --zoom with one value.")
            if not (options.time is not None or options.test is not None):
                sys.exit("Option --near needs the option --time or --test.")
            position = (
                options.near
                if options.near is not None
                else [(layer["bbox"][0] + layer["bbox"][2]) / 2, (layer["bbox"][1] + layer["bbox"][3]) / 2]
            )
            bbox = self.config["grids"][layer["grid"]]["bbox"]
            diff = [position[0] - bbox[0], position[1] - bbox[1]]
            resolution = self.config["grids"][layer["grid"]]["resolutions"][options.zoom[0]]
            mt_to_m = layer["meta_size"] * self.config["grids"][layer["grid"]]["tile_size"] * resolution
            mt = [float(d) / mt_to_m for d in diff]

            nb_tile = options.time * 3 if options.time is not None else options.test
            nb_mt = nb_tile / (layer["meta_size"] ** 2)
            nb_sqrt_mt = ceil(sqrt(nb_mt))

            mt_origin = [round(m - nb_sqrt_mt / 2) for m in mt]
            self.init_geom(
                layer_name,
                [
                    bbox[0] + mt_origin[0] * mt_to_m,
                    bbox[1] + mt_origin[1] * mt_to_m,
                    bbox[0] + (mt_origin[0] + nb_sqrt_mt) * mt_to_m,
                    bbox[1] + (mt_origin[1] + nb_sqrt_mt) * mt_to_m,
                ],
            )
        elif options.bbox is not None:
            self.init_geom(layer_name, options.bbox)
        elif "bbox" in layer:
            self.init_geom(layer_name, layer["bbox"])
        else:
            self.init_geom(layer_name, self.config["grids"][layer["grid"]]["bbox"])

    def get_grid(
        self, layer: tilecloud_chain.configuration.Layer, name: Optional[Any] = None
    ) -> tilecloud_chain.configuration.Grid:
        if name is None:
            name = layer["grid"]

        return self.grids[name]

    def get_tilesstore(self, cache_name: str) -> TimedTileStoreWrapper:
        cache = self.caches[cache_name]
        cache_tilestore = TimedTileStoreWrapper(
            MultiTileStore({lname: self.get_store(cache, lname) for lname in self.layers.keys()}),
            stats_name="store",
        )
        return cache_tilestore

    def init_geom(
        self,
        layer_name: str,
        extent: Optional[Union[List[float], List[int]]] = None,
    ) -> None:
        self.geoms[layer_name] = self.get_geoms(layer_name, extent)

    def get_geoms(
        self,
        layer_name: str,
        extent: Optional[Union[List[float], List[int]]] = None,
    ) -> Any:
        layer = self.config["layers"][layer_name]
        if layer_name in self._layers_geoms:
            # already build
            return self._layers_geoms[layer_name]

        layer_geoms: Dict[int, BaseGeometry] = {}
        self._layers_geoms[layer_name] = layer_geoms
        if extent:
            geom = Polygon(
                (
                    (extent[0], extent[1]),
                    (extent[0], extent[3]),
                    (extent[2], extent[3]),
                    (extent[2], extent[1]),
                )
            )
            for z, r in enumerate(self.config["grids"][layer["grid"]]["resolutions"]):
                layer_geoms[z] = geom

        if self.options.near is None and self.options.geom:
            for g in layer.get("geoms", []):
                with stats.timer_context(["geoms_get", layer_name]):
                    connection = psycopg2.connect(g["connection"])
                    cursor = connection.cursor()
                    sql = "SELECT ST_AsBinary(geom) FROM (SELECT {}) AS g".format(g["sql"])
                    logger.info("Execute SQL: %s.", sql)
                    cursor.execute(sql)
                    geoms = [loads_wkb(bytes(r[0])) for r in cursor.fetchall()]
                    geom = cascaded_union(geoms)
                    if extent:
                        geom = geom.intersection(
                            Polygon(
                                (
                                    (extent[0], extent[1]),
                                    (extent[0], extent[3]),
                                    (extent[2], extent[3]),
                                    (extent[2], extent[1]),
                                )
                            )
                        )
                    for z, r in enumerate(self.config["grids"][layer["grid"]]["resolutions"]):
                        if ("min_resolution" not in g or g["min_resolution"] <= r) and (
                            "max_resolution" not in g or g["max_resolution"] >= r
                        ):
                            layer_geoms[z] = geom
                    cursor.close()
                    connection.close()
        return layer_geoms

    def get_geoms_filter(
        self,
        layer: tilecloud_chain.configuration.Layer,
        grid_name: str,
        geoms: Dict[str, Dict[Union[str, int], BaseGeometry]],
    ) -> "IntersectGeometryFilter":
        return IntersectGeometryFilter(
            grid=self.config["grids"][grid_name],
            tile_grid=self.grid_obj[grid_name],
            geoms=geoms,
            px_buffer=(layer["px_buffer"] + layer["meta_buffer"] if layer["meta"] else 0),
        )

    def add_geom_filter(self) -> None:
        self.imap(
            MultiAction(
                {
                    layer_name: self.get_geoms_filter(layer=layer, grid_name=layer["grid"], geoms=self.geoms)
                    for layer_name, layer in self.layers.items()
                }
            ),
            "Intersect with geom",
        )

    def add_logger(self) -> None:
        if (
            not self.options.quiet
            and not self.options.verbose
            and not self.options.debug
            and os.environ.get("FRONTEND") != "noninteractive"
        ):

            def log_tiles(tile: Tile) -> Tile:
                variables = dict()
                variables.update(tile.__dict__)
                variables.update(tile.tilecoord.__dict__)
                variables["formated_metadata"] = tile.formated_metadata
                sys.stdout.write(
                    "{tilecoord} {formated_metadata}                         \r".format(**variables)
                )
                sys.stdout.flush()
                return tile

            self.imap(log_tiles)
        elif not self.options.quiet:
            self.imap(Logger(logger, logging.INFO, "%(tilecoord)s, %(formated_metadata)s"))

    def add_metatile_splitter(self, store: Optional[TileStore] = None) -> None:
        assert self.functions != self.functions_tiles, "add_metatile_splitter should not be called twice"
        if store is None:
            splitters: Dict[str, Optional[TileStore]] = {}
            for lname, layer in self.layers.items():
                if layer.get("meta"):
                    splitters[lname] = MetaTileSplitterTileStore(
                        layer["mime_type"],
                        self.config["grids"][layer["grid"]]["tile_size"],
                        layer["meta_buffer"],
                    )

            store = TimedTileStoreWrapper(MultiTileStore(splitters), stats_name="splitter")

        run = Run(self, self.functions_tiles, self.queue_store)
        nb_thread = int(os.environ.get("TILE_NB_THREAD", "1"))
        if nb_thread == 1 or not self.multi_thread:

            def meta_get(metatile: Tile) -> Tile:
                assert store is not None
                substream = store.get((metatile,))

                if getattr(self.options, "role", "") == "hash":
                    tile = next(substream)
                    assert tile is not None
                    run(tile)
                else:
                    for tile in substream:
                        assert tile is not None
                        tile.metadata.update(metatile.metadata)
                        run(tile)
                with self.error_lock:
                    self.error += run.error
                return metatile

        else:

            def meta_get(metatile: Tile) -> Tile:
                assert store is not None
                if self.metatilesplitter_thread_pool is None:
                    self.metatilesplitter_thread_pool = ThreadPoolExecutor(nb_thread)

                substream = store.get((metatile,))

                for _ in self.metatilesplitter_thread_pool.map(
                    run, substream, chunksize=int(os.environ.get("TILE_CHUNK_SIZE", "1"))
                ):
                    pass

                with self.error_lock:
                    self.error += run.error
                return metatile

        self.imap(meta_get)
        self.functions = self.functions_tiles

    def create_log_tiles_error(self, layer: str) -> Optional[TextIO]:
        if "error_file" in self.config["generation"]:
            now = datetime.now()
            time_ = now.strftime("%d-%m-%Y %H:%M:%S")
            error_file = open(self.config["generation"]["error_file"].format(layer=layer, datetime=now), "a")
            error_file.write(f"# [{time_}] Start the layer '{layer}' generation\n")
            self.error_files_[layer] = error_file
            return error_file
        return None

    def close(self) -> None:
        for file_ in self.error_files_.values():
            file_.close()

    def get_log_tiles_error_file(self, layer: str) -> Optional[TextIO]:
        return self.error_files_[layer] if layer in self.error_files_ else self.create_log_tiles_error(layer)

    def log_tiles_error(self, tile: Optional[Tile] = None, message: Optional[str] = None) -> None:
        if "error_file" in self.config["generation"]:
            assert tile is not None

            time_ = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            if self.get_log_tiles_error_file(tile.metadata["layer"]) is None:
                raise Exception("Missing error file")

            tilecoord = "" if tile.tilecoord is None else f"{tile.tilecoord} {tile.formated_metadata} "
            message = "" if message is None else f" {message}"

            io = self.get_log_tiles_error_file(tile.metadata["layer"])
            assert io is not None
            io.write("{}# [{}]{}\n".format(tilecoord, time_, message.replace("\n", " ")))

    def init_tilecoords(self, layer_name: str) -> None:
        layer = self.config["layers"][layer_name]
        resolutions = self.config["grids"][layer["grid"]]["resolutions"]

        if self.options.time is not None and self.options.zoom is None:
            if "min_resolution_seed" in layer:
                self.options.zoom = [resolutions.index(layer["min_resolution_seed"])]
            else:
                self.options.zoom = [len(resolutions) - 1]

        if self.options.zoom is not None:
            zoom_max = len(resolutions) - 1
            for zoom in self.options.zoom:
                if zoom > zoom_max:
                    logger.warning(
                        "zoom %i is greater than the maximum zoom %i" " of grid %s of layer %s, ignored.",
                        zoom,
                        zoom_max,
                        layer["grid"],
                        layer_name,
                    )
            self.options.zoom = [z for z in self.options.zoom if z <= zoom_max]

        if "min_resolution_seed" in layer:
            if self.options.zoom is None:
                self.options.zoom = []
                for z, resolution in enumerate(resolutions):
                    if resolution >= layer["min_resolution_seed"]:
                        self.options.zoom.append(z)
            else:
                for zoom in self.options.zoom:
                    resolution = resolutions[zoom]
                    if resolution < layer["min_resolution_seed"]:
                        logger.warning(
                            "zoom %i corresponds to resolution %s is smaller"
                            " than the 'min_resolution_seed' %s of layer %s, ignored.",
                            zoom,
                            resolution,
                            layer["min_resolution_seed"],
                            layer_name,
                        )
                self.options.zoom = [
                    z for z in self.options.zoom if resolutions[z] >= layer["min_resolution_seed"]
                ]

        if self.options.zoom is None:
            self.options.zoom = [z for z, r in enumerate(resolutions)]

        # Fill the bounding pyramid
        tilegrid = self.grid_obj[layer["grid"]]
        bounding_pyramid = BoundingPyramid(tilegrid=tilegrid)
        geoms = self.geoms[layer_name]
        for zoom in self.options.zoom:
            if zoom in geoms:
                extent = geoms[zoom].bounds

                if len(extent) == 0:
                    logger.warning("bounds empty for zoom %s", zoom)
                else:
                    minx, miny, maxx, maxy = extent
                    px_buffer = layer["px_buffer"]
                    m_buffer = px_buffer * resolutions[zoom]
                    minx -= m_buffer
                    miny -= m_buffer
                    maxx += m_buffer
                    maxy += m_buffer
                    bounding_pyramid.add(
                        tilegrid.tilecoord(
                            zoom,
                            max(minx, tilegrid.max_extent[0]),
                            max(miny, tilegrid.max_extent[1]),
                        )
                    )
                    bounding_pyramid.add(
                        tilegrid.tilecoord(
                            zoom,
                            min(maxx, tilegrid.max_extent[2]),
                            min(maxy, tilegrid.max_extent[3]),
                        )
                    )

        if layer["meta"]:
            self.set_tilecoords(bounding_pyramid.metatilecoords(layer["meta_size"]), layer_name)
        else:
            self.set_tilecoords(bounding_pyramid, layer_name)

    @staticmethod
    def _tilestream(
        tilecoords: Iterable[TileCoord],
        default_metadata: Dict[str, str],
        all_dimensions: List[Dict[str, str]],
    ) -> Iterator[Tile]:
        for tilecoord in tilecoords:
            for dimensions in all_dimensions:
                metadata = {}
                if default_metadata is not None:
                    metadata.update(default_metadata)
                for k, v in dimensions.items():
                    metadata["dimension_" + k] = v
                yield Tile(tilecoord, metadata=metadata)

    def set_tilecoords(self, tilecoords: Iterable[TileCoord], layer_name: str) -> None:
        assert tilecoords is not None
        layer = self.config["layers"][layer_name]

        self.tilestream = self._tilestream(tilecoords, {"layer": layer_name}, self.get_all_dimensions(layer))

    def set_store(self, store: TileStore) -> None:
        self.tilestream = cast(Iterator[Tile], store.list())

    def counter(self) -> "Count":
        count = Count()
        self.imap(count)
        return count

    def counter_size(self) -> "CountSize":
        count = CountSize()
        self.imap(count)
        return count

    def process(self, name: Optional[str] = None, key: str = "post_process") -> None:
        processes = {}
        for lname, layer in self.layers.items():
            name_ = name
            if name_ is None:
                name_ = layer.get(key)  # type: ignore
            if name_ is not None:
                processes[lname] = Process(self.config["process"][name_], self.options)
        if processes:
            self.imap(MultiAction(processes))

    def get(self, store: TileStore, time_message: Optional[str] = None) -> None:
        assert store is not None
        self.imap(store.get_one, time_message)

    def put(self, store: TileStore, time_message: Optional[str] = None) -> None:
        assert store is not None

        def put_internal(tile: Tile) -> Tile:
            store.put_one(tile)
            return tile

        self.imap(put_internal, time_message)

    def delete(self, store: TileStore, time_message: Optional[str] = None) -> None:
        assert store is not None

        def delete_internal(tile: Tile) -> Tile:
            store.delete_one(tile)
            return tile

        self.imap(delete_internal, time_message)

    def imap(self, func: Any, time_message: Optional[str] = None) -> None:
        assert func is not None

        class Func:
            def __init__(self, func: Callable[[Tile], Tile], time_message: Optional[str]) -> None:
                self.func = func
                self.time_message = time_message

            def __call__(self, tile: Tile) -> Tile:
                return self.func(tile)

            def __str__(self) -> str:
                return f"Func: {self.func}"

        self.functions.append(Func(func, time_message))

    def consume(self, test: Optional[int] = None) -> None:
        assert self.tilestream is not None
        assert threading.active_count() == 1, ", ".join([str(t) for t in threading.enumerate()])

        test = self.options.test if test is None else test

        start = datetime.now()

        run = Run(self, self.functions_metatiles)

        if test is None:
            if TYPE_CHECKING:
                buffer: queue.Queue[Tile] = queue.Queue(  # pylint: disable=unsubscriptable-object
                    int(os.environ.get("TILE_QUEUE_SIZE", "2"))
                )
            else:
                buffer = queue.Queue(int(os.environ.get("TILE_QUEUE_SIZE", "2")))
            end = False

            nb_thread = int(os.environ.get("METATILE_NB_THREAD", "1"))

            if nb_thread == 1 or not self.multi_thread:
                consume(map(run, self.tilestream), None)
            else:

                def target() -> None:
                    logger.debug("Start run")
                    while not end or not buffer.empty():
                        try:
                            run(buffer.get(timeout=1))
                        except queue.Empty:
                            pass
                    logger.debug("End run")

                threads = [threading.Thread(target=target, name=f"Run {i}") for i in range(nb_thread)]
                for thread in threads:
                    thread.start()

                for tile in self.tilestream:
                    buffer.put(tile)

                end = True

                for thread in threads:
                    thread.join(30)

            if self.metatilesplitter_thread_pool is not None:
                self.metatilesplitter_thread_pool.shutdown()
                self.metatilesplitter_thread_pool = None

            assert buffer.empty(), buffer.qsize()

        else:
            for _ in range(test):
                run(next(self.tilestream))

        if self.metatilesplitter_thread_pool is not None:
            self.metatilesplitter_thread_pool.shutdown()
            self.metatilesplitter_thread_pool = None

        assert threading.active_count() == 1, ", ".join([str(t) for t in threading.enumerate()])

        self.error += run.error
        self.duration = datetime.now() - start
        for ca in self._close_actions:
            ca()


class Count:
    def __init__(self) -> None:
        self.nb = 0
        self.lock = threading.Lock()

    def __call__(self, tile: Optional[Tile] = None) -> Optional[Tile]:
        with self.lock:
            self.nb += 1
        return tile


class CountSize:
    def __init__(self) -> None:
        self.nb = 0
        self.size = 0
        self.lock = threading.Lock()

    def __call__(self, tile: Optional[Tile] = None) -> Optional[Tile]:
        if tile and tile.data:
            with self.lock:
                self.nb += 1
                self.size += len(tile.data)
        return tile


class HashDropper:
    """
    Create a filter to remove the tiles data where they have the specified size and hash.

    Used to drop the empty tiles.

    The ``store`` is used to delete the empty tiles.
    """

    def __init__(
        self,
        size: int,
        sha1code: str,
        store: Optional[TileStore] = None,
        queue_store: Optional[TileStore] = None,
        count: Optional[Count] = None,
    ) -> None:
        self.size = size
        self.sha1code = sha1code
        self.store = store
        self.queue_store = queue_store
        self.count = count

    def __call__(self, tile: Tile) -> Optional[Tile]:
        assert tile.data
        if len(tile.data) != self.size or sha1(tile.data).hexdigest() != self.sha1code:
            return tile
        else:
            if self.store is not None:
                if tile.tilecoord.n != 1:
                    for tilecoord in tile.tilecoord:
                        self.store.delete_one(Tile(tilecoord, metadata=tile.metadata))
                else:
                    self.store.delete_one(tile)
            logger.info("The tile %s %s is dropped", tile.tilecoord, tile.formated_metadata)
            if hasattr(tile, "metatile"):
                metatile: Tile = tile.metatile  # type: ignore
                metatile.elapsed_togenerate -= 1  # type: ignore
                if metatile.elapsed_togenerate == 0 and self.queue_store is not None:  # type: ignore
                    self.queue_store.delete_one(metatile)
            elif self.queue_store is not None:
                self.queue_store.delete_one(tile)

            if self.count:
                self.count()

            return None


class MultiAction:
    """
    Used to perform an action based on the tile's layer name.

    E.g a HashDropper or Process
    """

    def __init__(self, actions: Mapping[str, Callable[[Tile], Optional[Tile]]]) -> None:
        self.actions = actions

    def __call__(self, tile: Tile) -> Optional[Tile]:
        layer = tile.metadata["layer"]
        if layer in self.actions:
            action = self.actions[layer]
            logger.debug("[%s] Run action %s.", tile.tilecoord, action)
            return action(tile)
        else:
            logger.debug(
                "[%s] Action not found for layer %s, in [%s].",
                tile.tilecoord,
                layer,
                ", ".join(self.actions.keys()),
            )
            return tile


class HashLogger:
    """
    Log the tile size and hash.
    """

    def __init__(self, block: str) -> None:
        self.block = block

    def __call__(self, tile: Tile) -> Tile:
        ref = None
        try:
            assert tile.data
            image = Image.open(BytesIO(tile.data))
        except OSError as ex:
            assert tile.data
            logger.error("%s: %s", str(ex), tile.data, exc_info=True)
            raise
        for px in image.getdata():
            if ref is None:
                ref = px
            elif px != ref:
                sys.exit("Error: image is not uniform.")

        assert tile.data
        print(
            """Tile: {} {}
    {}:
        size: {}
        hash: {}""".format(
                tile.tilecoord,
                tile.formated_metadata,
                self.block,
                len(tile.data),
                sha1(tile.data).hexdigest(),
            )
        )
        return tile


class LocalProcessFilter:
    def __init__(self, nb_process: int, process_nb: int) -> None:
        self.nb_process = nb_process
        self.process_nb = int(process_nb)

    def filter(self, tilecoord: TileCoord) -> bool:
        nb = round(tilecoord.z + tilecoord.x / tilecoord.n + tilecoord.y / tilecoord.n)
        return nb % self.nb_process == self.process_nb

    def __call__(self, tile: Tile) -> Optional[Tile]:
        return tile if self.filter(tile.tilecoord) else None


class IntersectGeometryFilter:
    def __init__(
        self,
        grid: tilecloud_chain.configuration.Grid,
        tile_grid: TileGrid,
        geoms: Dict[str, Dict[Union[str, int], BaseGeometry]],
        px_buffer: int = 0,
    ) -> None:
        assert grid is not None
        assert geoms is not None
        self.grid = grid
        self.tile_grid = tile_grid
        self.geoms = geoms
        self.px_buffer = px_buffer

    def filter_tilecoord(self, tilecoord: TileCoord, layer_name: str) -> bool:
        return self.bbox_polygon(  # type: ignore
            self.tile_grid.extent(tilecoord, self.grid["resolutions"][tilecoord.z] * self.px_buffer)
        ).intersects(self.geoms[layer_name][tilecoord.z])

    def __call__(self, tile: Tile) -> Optional[Tile]:
        return tile if self.filter_tilecoord(tile.tilecoord, tile.metadata["layer"]) else None

    @staticmethod
    def bbox_polygon(bbox: Tuple[float, float, float, float]) -> Polygon:
        return Polygon(((bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1])))


class DropEmpty:
    """
    Create a filter for dropping all tiles with errors.
    """

    def __init__(self, gene: TileGeneration) -> None:
        self.gene = gene

    def __call__(self, tile: Tile) -> Optional[Tile]:
        if not tile or not tile.data:
            logger.error(
                "The tile: %s%s is empty",
                tile.tilecoord if tile else "not defined",
                " " + tile.formated_metadata if tile else "",
            )
            if "error_file" in self.gene.config["generation"] and tile:
                self.gene.log_tiles_error(tile=tile, message="The tile is empty")
            return None
        else:
            return tile


def quote(arg: str) -> str:
    if " " in arg:
        if "'" in arg:
            if '"' in arg:
                return "'{}'".format(arg.replace("'", "\\'"))
            else:
                return f'"{arg}"'
        else:
            return f"'{arg}'"
    elif arg == "":
        return "''"
    else:
        return arg


def parse_tilecoord(string_representation: str) -> TileCoord:
    parts = string_representation.split(":")
    coords = [int(v) for v in parts[0].split("/")]
    if len(coords) != 3:
        raise ValueError("Wrong number of coordinates")
    z, x, y = coords
    if len(parts) == 1:
        tilecoord = TileCoord(z, x, y)
    elif len(parts) == 2:
        meta = parts[1].split("/")
        if len(meta) != 2:
            raise ValueError("No one '/' in meta coordinates")
        tilecoord = TileCoord(z, x, y, int(meta[0]))
    else:
        raise ValueError("More than on ':' in the tilecoord")
    return tilecoord


class Process:
    def __init__(self, config: tilecloud_chain.configuration.ProcessCommand, options: Namespace) -> None:
        self.config = config
        self.options = options

    def __call__(self, tile: Tile) -> Optional[Tile]:
        if tile and tile.data:
            fd_in, name_in = tempfile.mkstemp()
            with open(name_in, "wb") as file_in:
                file_in.write(tile.data)

            for cmd in self.config:
                args = []
                if (
                    not self.options.verbose and not self.options.debug and not self.options.quiet
                ) and "default" in cmd["arg"]:
                    args.append(cmd["arg"]["default"])
                if self.options.verbose and "verbose" in cmd["arg"]:
                    args.append(cmd["arg"]["verbose"])
                if self.options.debug and "debug" in cmd["arg"]:
                    args.append(cmd["arg"]["debug"])
                if self.options.quiet and "quiet" in cmd["arg"]:
                    args.append(cmd["arg"]["quiet"])

                if cmd["need_out"]:
                    fd_out, name_out = tempfile.mkstemp()
                    os.unlink(name_out)
                else:
                    name_out = name_in

                command = cmd["cmd"] % {
                    "in": name_in,
                    "out": name_out,
                    "args": " ".join(args),
                    "x": tile.tilecoord.x,
                    "y": tile.tilecoord.y,
                    "z": tile.tilecoord.z,
                }
                logger.debug("[%s] process: %s", tile.tilecoord, command)
                result = subprocess.run(  # pylint: disable=subprocess-run-check
                    command, shell=True, capture_output=True
                )
                if result.returncode != 0:
                    tile.error = "Command '{}' on tile {} return error code {}:\n{!s}\n{!s}".format(
                        command, tile.tilecoord, result.returncode, result.stderr, result.stdout
                    )
                    tile.data = None
                    return tile

                if cmd["need_out"]:
                    os.close(fd_in)
                    name_in = name_out
                    fd_in = fd_out

            with open(name_in, "rb") as file_out:
                tile.data = file_out.read()
            os.close(fd_in)

        return tile


class TilesFileStore(TileStore):
    def __init__(self, tiles_file: str, layer: str, all_dimensions: List[Dict[str, str]]):
        super().__init__()
        assert isinstance(layer, str)

        self.tiles_file = open(tiles_file)
        self.layer = layer
        self.all_dimensions = all_dimensions

    def list(self) -> Iterator[Tile]:
        while True:
            line = self.tiles_file.readline()
            if not line:
                return
            line = line.split("#")[0].strip()
            if line != "":
                try:
                    tilecoord = parse_tilecoord(line)
                except ValueError as e:
                    logger.error(
                        "A tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n\n%s",
                        line,
                        repr(e),
                        exc_info=True,
                    )
                    continue

                for dimensions in self.all_dimensions:
                    metadata = {"layer": self.layer}
                    for k, v in dimensions.items():
                        metadata["dimension_" + k] = v
                    yield Tile(tilecoord, metadata=metadata)


def _await_message(_: Any) -> bool:
    try:
        # Just sleep, the SQSTileStore will try again after that...
        time.sleep(10)
        return False
    except KeyboardInterrupt:
        raise StopIteration


def get_queue_store(
    config: tilecloud_chain.configuration.Configuration, daemon: bool
) -> TimedTileStoreWrapper:
    if "redis" in config:
        # Create a Redis queue
        conf = config["redis"]
        tilestore_kwargs: Dict[str, Any] = dict(
            name=conf["queue"],
            stop_if_empty=not daemon,
            timeout=conf["timeout"],
            pending_timeout=conf["pending_timeout"],
            max_retries=conf["max_retries"],
            max_errors_age=conf["max_errors_age"],
            max_errors_nb=conf["max_errors_nb"],
            connection_kwargs=conf.get("connection_kwargs", {}),
            sentinel_kwargs=conf.get("sentinel_kwargs"),
        )
        if "socket_timeout" in conf:
            tilestore_kwargs["connection_kwargs"]["socket_timeout"] = conf["socket_timeout"]
        if "db" in conf:
            tilestore_kwargs["connection_kwargs"]["db"] = conf["db"]
        if "url" in conf:
            tilestore_kwargs["url"] = conf["url"]
        else:
            tilestore_kwargs["sentinels"] = conf["sentinels"]
            tilestore_kwargs["service_name"] = conf.get("service_name", "mymaster")
        return TimedTileStoreWrapper(RedisTileStore(**tilestore_kwargs), stats_name="redis")
    else:
        # Create a SQS queue
        return TimedTileStoreWrapper(
            SQSTileStore(_get_sqs_queue(config), on_empty=_await_message if daemon else maybe_stop),
            stats_name="SQS",
        )


def _get_sqs_queue(
    config: tilecloud_chain.configuration.Configuration,
) -> "botocore.client.SQS":
    if "sqs" not in config:
        sys.exit("The config hasn't any configured queue")
    sqs = boto3.resource("sqs", region_name=config["sqs"].get("region", "eu-west-1"))
    return sqs.get_queue_by_name(QueueName=config["sqs"]["queue"])
