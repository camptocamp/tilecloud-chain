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
import pathlib
import pkgutil
import queue
import re
import sqlite3
import subprocess  # nosec
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
    Optional,
    TextIO,
    Tuple,
    TypedDict,
    Union,
    cast,
)

from PIL import Image
import boto3
import botocore.client
from c2cwsgiutils import sentry, stats
import c2cwsgiutils.setup_process
from jsonschema_gentypes import validate
import psycopg2
import pyramid.scripts.common
from ruamel.yaml import YAML
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon
from shapely.ops import unary_union
from shapely.wkb import loads as loads_wkb

from tilecloud import BoundingPyramid, Tile, TileCoord, TileGrid, TileStore, consume
import tilecloud.filter.error
from tilecloud.filter.error import LogErrors, MaximumConsecutiveErrors
from tilecloud.filter.logger import Logger
from tilecloud.grid.free import FreeTileGrid
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.store.azure_storage_blob import AzureStorageBlobTileStore
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
    """Get human redable string of the metadata."""
    metadata = dict(tile.metadata)
    if "tiles" in metadata:
        metadata["tiles"] = metadata["tiles"].keys()  # type: ignore
    return " ".join([f"{k}={metadata[k]}" for k in sorted(metadata.keys())])


setattr(Tile, "formated_metadata", property(formated_metadata))


def add_common_options(
    parser: ArgumentParser,
    tile_pyramid: bool = True,
    no_geom: bool = True,
    near: bool = True,
    time: bool = True,  # pylint: disable=redefined-outer-name
    dimensions: bool = False,
    cache: bool = True,
) -> None:
    """Get the options used by some commands."""
    c2cwsgiutils.setup_process.fill_arguments(parser)
    parser.add_argument(
        "-c",
        "--config",
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
    """Get an identifier for a tile matrix."""
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
    """
    Run the tile generation.

    Add some logs.
    Manage the max_consecutive_errors.
    """

    _re_rm_xml_tag = re.compile("(<[^>]*>|\n)")

    def __init__(
        self,
        gene: "TileGeneration",
        functions: List[Callable[[Tile], Tile]],
    ) -> None:
        self.gene = gene
        self.functions = functions
        self.safe = gene.options is None or not gene.options.debug
        daemon = gene.options is not None and getattr(gene.options, "daemon", False)
        self.max_consecutive_errors = (
            MaximumConsecutiveErrors(gene.get_main_config().config["generation"]["maxconsecutive_errors"])
            if not daemon and gene.maxconsecutive_errors
            else None
        )
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
                logger.debug("[%s] %s in %s", tilecoord, func.time_message if getattr(func, "time_message", None) is not None else func, str(datetime.now() - n))  # type: ignore
                if tile is None:
                    logger.debug("[%s] Drop", tilecoord)
                    return None
                if tile.error:
                    if tile.content_type and tile.content_type.startswith("application/vnd.ogc.se_xml"):
                        assert isinstance(tile.error, str)
                        tile.error = f"WMS server error: {self._re_rm_xml_tag.sub('', tile.error)}"
                    logger.warning("Error with tile %s:\n%s", tile.tilecoord, tile.error)
                    if stats.BACKENDS:
                        stats.increment_counter(["error", tile.metadata.get("layer", "None")])

                    if "error_file" in self.gene.get_main_config().config["generation"]:
                        self.gene.log_tiles_error(tile=tile, message=repr(tile.error))

                    if self.max_consecutive_errors is not None:
                        self.max_consecutive_errors(tile)

                    if self.gene.queue_store is not None:
                        self.gene.queue_store.delete_one(tile)
                    with self.error_lock:
                        self.error += 1
                    return tile
            except Exception:
                logger.debug("Run error", stack_info=True)
                raise

        if self.max_consecutive_errors is not None:
            self.max_consecutive_errors(tile)

        return tile


class Close:
    """Database closer."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def __call__(self) -> None:
        self.db.close()


class Legend(TypedDict, total=False):
    """Legend fields."""

    mime_type: str
    href: str
    max_resolution: float
    min_resolution: float
    width: int
    height: int


class DatedConfig:
    """Loaded config with timestamps to be able to invalidate it on configuration file change."""

    def __init__(self, config: tilecloud_chain.configuration.Configuration, mtime: float, file: str) -> None:
        self.config = config
        self.mtime = mtime
        self.file = file


class DatedGeoms:
    """Geoms with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, geoms: Dict[Union[str, int], BaseGeometry], mtime: float) -> None:
        self.geoms = geoms
        self.mtime = mtime


class DatedTileGrid:
    """TilGrid with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, grid: TileGrid, mtime: float) -> None:
        self.grid = grid
        self.mtime = mtime


class DatedHosts:
    """Host with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, hosts: Dict[str, str], mtime: float) -> None:
        self.hosts = hosts
        self.mtime = mtime


class TileGeneration:
    """Base class of all the tile generation."""

    tilestream: Optional[Iterator[Tile]] = None
    duration: timedelta = timedelta()
    error = 0
    queue_store: Optional[TileStore] = None
    daemon = False

    def __init__(
        self,
        config_file: Optional[str] = None,
        options: Optional[Namespace] = None,
        layer_name: Optional[str] = None,
        base_config: Optional[tilecloud_chain.configuration.Configuration] = None,
        configure_logging: bool = True,
        multi_thread: bool = True,
        maxconsecutive_errors: bool = True,
    ):
        self.geoms_cache: Dict[str, Dict[str, DatedGeoms]] = {}
        self._close_actions: List["Close"] = []
        self.error_lock = threading.Lock()
        self.error_files_: Dict[str, TextIO] = {}
        self.functions_tiles: List[Callable[[Tile], Tile]] = []
        self.functions_metatiles: List[Callable[[Tile], Tile]] = []
        self.functions = self.functions_metatiles
        self.metatilesplitter_thread_pool: Optional[ThreadPoolExecutor] = None
        self.multi_thread = multi_thread
        self.maxconsecutive_errors = maxconsecutive_errors
        self.grid_cache: Dict[str, Dict[str, DatedTileGrid]] = {}
        self.layer_legends: Dict[str, List[Legend]] = {}
        self.config_file = config_file
        self.base_config = base_config
        self.configs: Dict[str, DatedConfig] = {}
        self.hosts_cache: Optional[DatedHosts] = None

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
            if os.environ.get("CI", "false").lower() != "true":
                loader = pyramid.scripts.common.get_config_loader(self.options.config_uri)
                loader.setup_logging(
                    pyramid.scripts.common.parse_vars(self.options.config_vars)
                    if self.options.config_vars
                    else None
                )
                sentry.init()

        assert "generation" in self.get_main_config().config, self.get_main_config().config

        error = False
        if self.options is not None and self.options.zoom is not None:
            error_message = (
                f"The zoom argument '{self.options.zoom}' has incorrect format, "
                "it can be a single value, a range (3-9), a list of values (2,5,7)."
            )
            if self.options.zoom.find("-") >= 0:
                splitted_zoom: List[str] = self.options.zoom.split("-")
                if len(splitted_zoom) != 2:
                    logger.error(error_message)
                    error = True
                try:
                    self.options.zoom = range(int(splitted_zoom[0]), int(splitted_zoom[1]) + 1)
                except ValueError:
                    logger.exception(error_message)
                    error = True
            elif self.options.zoom.find(",") >= 0:
                try:
                    self.options.zoom = [int(z) for z in self.options.zoom.split(",")]
                except ValueError:
                    logger.exception(error_message)
                    error = True
            else:
                try:
                    self.options.zoom = [int(self.options.zoom)]
                except ValueError:
                    logger.exception(error_message)
                    error = True

        if error:
            sys.exit(1)

        if layer_name and self.config_file:
            assert layer_name is not None
            self.create_log_tiles_error(layer_name)

    def get_host_config_file(self, host: Optional[str]) -> Optional[str]:
        """Get the configuration file name for the given host."""
        if self.config_file:
            return self.config_file
        assert host
        if host not in self.get_hosts():
            logger.error("Missing host '%s' in global config", host)
            return None
        return self.get_hosts().get(host, os.environ.get("TILEGENERATION_CONFIGFILE"))

    def get_host_config(self, host: Optional[str]) -> DatedConfig:
        """Get the configuration for the given host."""
        config_file = self.get_host_config_file(host)
        return (
            self.get_config(config_file)
            if config_file
            else DatedConfig(cast(tilecloud_chain.configuration.Configuration, {}), 0, "")
        )

    def get_tile_config(self, tile: Tile) -> DatedConfig:
        return self.get_config(tile.metadata["config_file"])

    def get_config(
        self,
        config_file: str,
        ignore_error: bool = True,
        base_config: Optional[tilecloud_chain.configuration.Configuration] = None,
    ) -> DatedConfig:
        """Get the validated configuration for the file name, with cache management."""
        assert config_file
        config_path = pathlib.Path(config_file)
        if not config_path.exists():
            logger.error("Missing config file %s", config_file)
            if ignore_error:
                return DatedConfig(cast(tilecloud_chain.configuration.Configuration, {}), 0, "")
            else:
                sys.exit(1)

        config: Optional[DatedConfig] = self.configs.get(config_file)
        if config is not None and config.mtime == config_path.stat().st_mtime:
            return config

        config, success = self._get_config(config_file, ignore_error, base_config)
        if not success or config is None:
            if ignore_error:
                config = DatedConfig(cast(tilecloud_chain.configuration.Configuration, {}), 0, "")
            else:
                sys.exit(1)
        self.configs[config_file] = config
        return config

    def get_main_config(self) -> DatedConfig:
        if "TILEGENERATION_MAIN_CONFIGFILE" in os.environ and os.environ["TILEGENERATION_MAIN_CONFIGFILE"]:
            return self.get_config(os.environ["TILEGENERATION_MAIN_CONFIGFILE"], False)
        elif self.config_file:
            return self.get_config(self.config_file, self.options.ignore_error, self.base_config)
        else:
            logger.error("No provided configuration file")
            return DatedConfig({}, 0, "")

    def get_hosts(self) -> Dict[str, str]:
        file_path = pathlib.Path(os.environ["TILEGENERATION_HOSTSFILE"])
        if not file_path.exists():
            logger.error("Missing hosts file %s", file_path)
            return {}

        if self.hosts_cache is not None and self.hosts_cache.mtime == file_path.stat().st_mtime:
            return self.hosts_cache.hosts

        with file_path.open(encoding="utf-8") as hosts_file:
            ruamel = YAML(typ="safe")
            hosts = {}
            hosts_raw = ruamel.load(hosts_file)
            if "sources" in hosts_raw:
                for key, value in hosts_raw["sources"].items():
                    if isinstance(value, str):
                        hosts[key] = value
                    else:
                        hosts.update(value)
            else:
                hosts = hosts_raw

        self.hosts_cache = DatedHosts(hosts, file_path.stat().st_mtime)
        return hosts

    def _get_config(
        self,
        config_file: str,
        ignore_error: bool,
        base_config: Optional[tilecloud_chain.configuration.Configuration] = None,
    ) -> Tuple[DatedConfig, bool]:
        """Get the validated configuration for the file name."""
        with open(config_file, encoding="utf-8") as f:
            config: Dict[str, Any] = {}
            config.update({} if base_config is None else base_config)
            ruamel = YAML()
            config.update(ruamel.load(f))

        dated_config = DatedConfig(
            cast(tilecloud_chain.configuration.Configuration, config),
            pathlib.Path(config_file).stat().st_mtime,
            config_file,
        )
        success = self.validate_config(dated_config, ignore_error)
        return dated_config, success

    def validate_config(self, config: DatedConfig, ignore_error: bool) -> bool:
        """Validate the configuration."""
        # Generate base structure
        if "defaults" in config.config:
            del config.config["defaults"]
        if "generation" not in config.config:
            config.config["generation"] = {}
        if "cost" in config.config:
            if "s3" not in config.config["cost"]:
                config.config["cost"]["s3"] = {}
            if "cloudfront" not in config.config["cost"]:
                config.config["cost"]["cloudfront"] = {}
            if "sqs" not in config.config["cost"]:
                config.config["cost"]["sqs"] = {}

        schema_data = pkgutil.get_data("tilecloud_chain", "schema.json")
        assert schema_data
        errors, _ = validate.validate(
            config.file, cast(Dict[str, Any], config.config), json.loads(schema_data), default=True
        )

        if errors:
            logger.error("The config file is invalid:\n%s", "\n".join(errors))
            if not (
                ignore_error
                or os.environ.get("TILEGENERATION_IGNORE_CONFIG_ERROR", "FALSE").lower() == "true"
            ):
                sys.exit(1)

        error = False
        grids = config.config.get("grids", {})
        for grid in grids.values():
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
                    grid["proj4_literal"] = f"+init={grid['srs']}"

        layers = config.config.get("layers", {})
        for lname, layer in sorted(layers.items()):
            if "headers" not in layer and layer["type"] == "wms":
                layer["headers"] = {
                    "Cache-Control": "no-cache, no-store",
                    "Pragma": "no-cache",
                }
            if layer["type"] == "mapnik" and layer.get("output_format", "png") == "grid" and layer["meta"]:
                logger.error("The layer '%s' is of type Mapnik/Grid, that can't support matatiles.", lname)
                error = True

        if error:
            if not (
                ignore_error
                or os.environ.get("TILEGENERATION_IGNORE_CONFIG_ERROR", "FALSE").lower() == "true"
            ):
                sys.exit(1)

        return not (error or errors)

    def init(self, queue_store: Optional[TileStore] = None, daemon: bool = False) -> None:
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
            result *= fact**nb
        return result

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
        self,
        config: DatedConfig,
        cache: tilecloud_chain.configuration.Cache,
        layer_name: str,
        read_only: bool = False,
    ) -> TileStore:
        layer = config.config["layers"][layer_name]
        grid = config.config["grids"][layer["grid"]]
        layout = WMTSTileLayout(
            layer=layer_name,
            url=cache["folder"],
            style=layer["wmts_style"],
            format="." + layer["extension"],
            dimensions_name=[dimension["name"] for dimension in layer.get("dimensions", [])],
            tile_matrix_set=layer["grid"],
            tile_matrix=lambda z: get_tile_matrix_identifier(grid, zoom=z),
            request_encoding="REST",
        )
        # store
        if cache["type"] == "s3":
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
            # on s3
            cache_tilestore: TileStore = S3TileStore(
                cache_s3["bucket"],
                layout,
                s3_host=cache.get("host", "s3-eu-west-1.amazonaws.com"),
                cache_control=cache.get("cache_control"),
            )
        elif cache["type"] == "azure":
            cache_azure = cast(tilecloud_chain.configuration.CacheAzureTyped, cache)
            # on Azure
            cache_tilestore = AzureStorageBlobTileStore(
                container=cache_azure["container"],
                tilelayout=layout,
                cache_control=cache_azure.get("cache_control"),
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

    @staticmethod
    def get_grid_name(
        config: DatedConfig, layer: tilecloud_chain.configuration.Layer, name: Optional[Any] = None
    ) -> tilecloud_chain.configuration.Grid:
        if name is None:
            name = layer["grid"]

        return config.config["grids"][name]

    def get_tilesstore(self, cache: Optional[str] = None) -> TimedTileStoreWrapper:
        gene = self

        def get_store(config_file: str, layer_name: str) -> TileStore:
            config = gene.get_config(config_file)
            cache_name = cache or config.config["generation"]["default_cache"]
            cache_obj = config.config["caches"][cache_name]
            return self.get_store(config, cache_obj, layer_name)

        cache_tilestore = TimedTileStoreWrapper(
            MultiTileStore(get_store),
            stats_name="store",
        )
        return cache_tilestore

    def add_geom_filter(self) -> None:
        self.imap(IntersectGeometryFilter(gene=self), "Intersect with geom")

    def add_logger(self) -> None:
        if (
            not self.options.quiet
            and not self.options.verbose
            and not self.options.debug
            and os.environ.get("FRONTEND") != "noninteractive"
        ):

            def log_tiles(tile: Tile) -> Tile:
                sys.stdout.write(f"{tile.tilecoord} {tile.formated_metadata}                         \r")
                sys.stdout.flush()
                return tile

            self.imap(log_tiles)
        elif not self.options.quiet and getattr(self.options, "role", None) != "server":
            self.imap(Logger(logger, logging.INFO, "%(tilecoord)s, %(formated_metadata)s"))

    def add_metatile_splitter(self, store: Optional[TileStore] = None) -> None:
        assert self.functions != self.functions_tiles, "add_metatile_splitter should not be called twice"
        if store is None:
            gene = self

            def get_splitter(config_file: str, layer_name: str) -> Optional[MetaTileSplitterTileStore]:
                config = gene.get_config(config_file)
                layer = config.config["layers"][layer_name]
                if layer.get("meta"):
                    return MetaTileSplitterTileStore(
                        layer["mime_type"],
                        config.config["grids"][layer["grid"]]["tile_size"],
                        layer["meta_buffer"],
                    )
                return None

            store = TimedTileStoreWrapper(MultiTileStore(get_splitter), stats_name="splitter")

        run = Run(self, self.functions_tiles)
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
        if "error_file" in self.get_main_config().config.get("generation", {}):
            now = datetime.now()
            time_ = now.strftime("%d-%m-%Y %H:%M:%S")
            error_file = open(  # pylint: disable=consider-using-with
                self.get_main_config().config["generation"]["error_file"].format(layer=layer, datetime=now),
                "a",
                encoding="utf-8",
            )
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
        if tile is None:
            return
        config = self.get_tile_config(tile)
        if "error_file" in config.config["generation"]:
            assert tile is not None

            time_ = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            if self.get_log_tiles_error_file(tile.metadata["layer"]) is None:
                raise Exception("Missing error file")

            tilecoord = "" if tile.tilecoord is None else f"{tile.tilecoord} {tile.formated_metadata} "
            message = "" if message is None else f" {message}"

            io = self.get_log_tiles_error_file(tile.metadata["layer"])
            assert io is not None
            out_message = message.replace("\n", " ")
            io.write(f"{tilecoord}# [{time_}]{out_message}\n")

    def get_grid(self, config: DatedConfig, grid_name: str) -> TileGrid:
        dated_grid = self.grid_cache.get(config.file, {}).get(grid_name)
        if dated_grid is not None and config.mtime == dated_grid.mtime:
            return dated_grid.grid

        grid = config.config["grids"][grid_name]
        scale = grid["resolution_scale"]

        tilegrid = FreeTileGrid(
            resolutions=cast(List[int], [r * scale for r in grid["resolutions"]]),
            scale=scale,
            max_extent=cast(Tuple[int, int, int, int], grid["bbox"]),
            tile_size=grid["tile_size"],
        )

        self.grid_cache.setdefault(config.file, {})[grid_name] = DatedTileGrid(tilegrid, config.mtime)
        return tilegrid

    def get_geoms(self, config: DatedConfig, layer_name: str) -> Dict[Union[str, int], BaseGeometry]:
        dated_geoms = self.geoms_cache.get(config.file, {}).get(layer_name)
        if dated_geoms is not None and config.mtime == dated_geoms.mtime:
            return dated_geoms.geoms

        layer = config.config["layers"][layer_name]

        if self.options.near is not None or (
            self.options.time is not None and "bbox" in layer and self.options.zoom is not None
        ):
            if self.options.zoom is None or len(self.options.zoom) != 1:
                sys.exit("Option --near needs the option --zoom with one value.")
            if not (self.options.time is not None or self.options.test is not None):
                sys.exit("Option --near needs the option --time or --test.")
            position = (
                self.options.near
                if self.options.near is not None
                else [(layer["bbox"][0] + layer["bbox"][2]) / 2, (layer["bbox"][1] + layer["bbox"][3]) / 2]
            )
            bbox = config.config["grids"][layer["grid"]]["bbox"]
            diff = [position[0] - bbox[0], position[1] - bbox[1]]
            resolution = config.config["grids"][layer["grid"]]["resolutions"][self.options.zoom[0]]
            mt_to_m = layer["meta_size"] * config.config["grids"][layer["grid"]]["tile_size"] * resolution
            mt = [float(d) / mt_to_m for d in diff]

            nb_tile = self.options.time * 3 if self.options.time is not None else self.options.test
            nb_mt = nb_tile / (layer["meta_size"] ** 2)
            nb_sqrt_mt = ceil(sqrt(nb_mt))

            mt_origin = [round(m - nb_sqrt_mt / 2) for m in mt]
            extent = [
                bbox[0] + mt_origin[0] * mt_to_m,
                bbox[1] + mt_origin[1] * mt_to_m,
                bbox[0] + (mt_origin[0] + nb_sqrt_mt) * mt_to_m,
                bbox[1] + (mt_origin[1] + nb_sqrt_mt) * mt_to_m,
            ]
        elif self.options.bbox is not None:
            extent = self.options.bbox
        elif "bbox" in layer:
            extent = layer["bbox"]
        else:
            extent = config.config["grids"][layer["grid"]]["bbox"]

        geoms: Dict[Union[str, int], BaseGeometry] = {}
        if extent:
            geom = Polygon(
                (
                    (extent[0], extent[1]),
                    (extent[0], extent[3]),
                    (extent[2], extent[3]),
                    (extent[2], extent[1]),
                )
            )
            for z, r in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                geoms[z] = geom

        if self.options.near is None and self.options.geom:
            for g in layer.get("geoms", []):
                with stats.timer_context(["geoms_get", layer_name]):
                    connection = psycopg2.connect(g["connection"])
                    cursor = connection.cursor()
                    sql = f"SELECT ST_AsBinary(geom) FROM (SELECT {g['sql']}) AS g"  # nosec
                    logger.info("Execute SQL: %s.", sql)
                    cursor.execute(sql)
                    geom_list = [loads_wkb(bytes(r[0])) for r in cursor.fetchall()]
                    geom = unary_union(geom_list)
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
                    for z, r in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                        if ("min_resolution" not in g or g["min_resolution"] <= r) and (
                            "max_resolution" not in g or g["max_resolution"] >= r
                        ):
                            geoms[z] = geom
                    cursor.close()
                    connection.close()

        self.geoms_cache.setdefault(config.file, {})[layer_name] = DatedGeoms(geoms, config.mtime)
        return geoms

    def init_tilecoords(self, config: DatedConfig, layer_name: str) -> None:
        layer = config.config["layers"][layer_name]
        resolutions = config.config["grids"][layer["grid"]]["resolutions"]

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
        tilegrid = self.get_grid(config, layer["grid"])
        bounding_pyramid = BoundingPyramid(tilegrid=tilegrid)
        geoms = self.get_geoms(config, layer_name)
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
            self.set_tilecoords(config, bounding_pyramid.metatilecoords(layer["meta_size"]), layer_name)
        else:
            self.set_tilecoords(config, bounding_pyramid, layer_name)

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

    def set_tilecoords(self, config: DatedConfig, tilecoords: Iterable[TileCoord], layer_name: str) -> None:
        assert tilecoords is not None
        layer = config.config["layers"][layer_name]

        self.tilestream = self._tilestream(
            tilecoords,
            {"layer": layer_name, "config_file": config.file},
            self.get_all_dimensions(layer),
        )

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
        gene = self

        def get_process(config_file: str, layer_name: str) -> Optional[Process]:
            config = gene.get_config(config_file)
            layer = config.config["layers"][layer_name]
            name_ = name
            if name_ is None:
                name_ = layer.get(key)  # type: ignore
            if name_ is not None:
                return Process(config.config["process"][name_], self.options)
            return None

        self.imap(MultiAction(get_process))

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
            """Function with an additional field used to names it in timing messages."""

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
                should_exit_error = False

                def target() -> None:
                    logger.debug("Start run")
                    nonlocal should_exit_error
                    while not end or not buffer.empty():
                        try:
                            run(buffer.get(timeout=1))
                        except tilecloud.filter.error.TooManyErrors:
                            logger.exception("Too many errors")
                            should_exit_error = True
                        except queue.Empty:
                            pass
                    logger.debug("End run")

                threads = [threading.Thread(target=target, name=f"Run {i}") for i in range(nb_thread)]
                for thread in threads:
                    thread.start()

                for tile in self.tilestream:
                    while True:
                        try:
                            buffer.put(tile, timeout=1)
                            break
                        except queue.Full:
                            if should_exit_error:
                                sys.exit(1)

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
    """Count the number of generated tile."""

    def __init__(self) -> None:
        self.nb = 0
        self.lock = threading.Lock()

    def __call__(self, tile: Optional[Tile] = None) -> Optional[Tile]:
        with self.lock:
            self.nb += 1
        return tile


class CountSize:
    """Count the number of generated tile and measure the total generated size."""

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
        if len(tile.data) != self.size or sha1(tile.data).hexdigest() != self.sha1code:  # nosec
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

    def __init__(
        self,
        get_action: Callable[[str, str], Optional[Callable[[Tile], Optional[Tile]]]],
    ) -> None:
        self.get_action = get_action
        self.actions: Dict[Tuple[str, str], Optional[Callable[[Tile], Optional[Tile]]]] = {}

    def __call__(self, tile: Tile) -> Optional[Tile]:
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        action = self.actions.get((config_file, layer))
        if action is None:
            action = self.get_action(config_file, layer)
            self.actions[(config_file, layer)] = action
        if action:
            logger.debug("[%s] Run action %s.", tile.tilecoord, action)
            return action(tile)
        return tile


class HashLogger:
    """Log the tile size and hash."""

    def __init__(self, block: str) -> None:
        self.block = block

    def __call__(self, tile: Tile) -> Tile:
        ref = None
        try:
            assert tile.data
            image = Image.open(BytesIO(tile.data))
        except OSError as ex:
            assert tile.data
            logger.exception("%s: %s", str(ex), tile.data)
            raise
        for px in image.getdata():
            if ref is None:
                ref = px
            elif px != ref:
                logger.error("Error: image is not uniform.")
                sys.exit(1)

        assert tile.data
        print(
            f"""Tile: {tile.tilecoord} {tile.formated_metadata}
    {self.block}:
        size: {len(tile.data)}
        hash: {sha1(tile.data).hexdigest()}"""  # nosec
        )
        return tile


class LocalProcessFilter:
    """
    Drop the tiles (coordinate) that shouldn't be generated in this process.

    Process 1: process tiles 0 of 3
    Process 2: process tiles 1 of 3
    Process 3: process tiles 2 of 3
    """

    def __init__(self, nb_process: int, process_nb: int) -> None:
        self.nb_process = nb_process
        self.process_nb = int(process_nb)

    def filter(self, tilecoord: TileCoord) -> bool:
        nb = round(tilecoord.z + tilecoord.x / tilecoord.n + tilecoord.y / tilecoord.n)
        return nb % self.nb_process == self.process_nb

    def __call__(self, tile: Tile) -> Optional[Tile]:
        return tile if self.filter(tile.tilecoord) else None


class IntersectGeometryFilter:
    """Drop the tiles (coordinates) it she didn't intersect the configured geom."""

    def __init__(
        self,
        gene: TileGeneration,
    ) -> None:
        self.gene = gene

    def filter_tilecoord(self, config: DatedConfig, tilecoord: TileCoord, layer_name: str) -> bool:
        layer = config.config["layers"][layer_name]
        grid_name = layer["grid"]
        grid = config.config["grids"][grid_name]
        tile_grid = self.gene.get_grid(config, grid_name)
        px_buffer = layer["px_buffer"] + layer["meta_buffer"] if layer["meta"] else 0
        geoms = self.gene.get_geoms(config, layer_name)
        return self.bbox_polygon(  # type: ignore
            tile_grid.extent(tilecoord, grid["resolutions"][tilecoord.z] * px_buffer)
        ).intersects(geoms[tilecoord.z])

    def __call__(self, tile: Tile) -> Optional[Tile]:
        return (
            tile
            if self.filter_tilecoord(self.gene.get_tile_config(tile), tile.tilecoord, tile.metadata["layer"])
            else None
        )

    @staticmethod
    def bbox_polygon(bbox: Tuple[float, float, float, float]) -> Polygon:
        return Polygon(((bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1])))


class DropEmpty:
    """Create a filter for dropping all tiles with errors."""

    def __init__(self, gene: TileGeneration) -> None:
        self.gene = gene

    def __call__(self, tile: Tile) -> Optional[Tile]:
        config = self.gene.get_tile_config(tile)
        if not tile or not tile.data:
            logger.error(
                "The tile: %s%s is empty",
                tile.tilecoord if tile else "not defined",
                " " + tile.formated_metadata if tile else "",
            )
            if "error_file" in config.config["generation"] and tile:
                self.gene.log_tiles_error(tile=tile, message="The tile is empty")
            return None
        else:
            return tile


def quote(arg: str) -> str:
    """Add some quote and escape to pass the argument to an externa command."""
    if " " in arg or "'" in arg or '"' in arg:
        if "'" in arg:
            if '"' in arg:
                formated_arg = arg.replace("'", "\\'")
                return f"'{formated_arg}'"
            return f'"{arg}"'
        else:
            return f"'{arg}'"
    elif arg == "":
        return "''"
    else:
        return arg


def parse_tilecoord(string_representation: str) -> TileCoord:
    """Parce the tile coordinates (z/x/y => TileCoord object)."""
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
    """Process a tile throw an external command."""

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
                    command, shell=True, capture_output=True  # nosec
                )
                if result.returncode != 0:
                    tile.error = (
                        f"Command '{command}' on tile {tile.tilecoord} "
                        f"return error code {result.returncode}:\n{result.stderr!s}\n{result.stdout!s}"
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
    """Load tiles to be generate from a file."""

    def __init__(self, tiles_file: str):
        super().__init__()

        self.tiles_file = open(tiles_file, encoding="utf-8")  # pylint: disable=consider-using-with

    def list(self) -> Iterator[Tile]:
        while True:
            line = self.tiles_file.readline()
            if not line:
                return
            line = line.split("#")[0].strip()
            if line != "":
                splitted_line = line.split(" ")
                try:
                    tilecoord = parse_tilecoord(splitted_line[0])
                except ValueError as e:
                    logger.exception(
                        "A tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n\n%s",
                        line,
                        repr(e),
                    )
                    continue

                yield Tile(
                    tilecoord,
                    metadata=dict([cast(Tuple[str, str], e.split("=")) for e in splitted_line[1:]]),
                )


def _await_message(_: Any) -> bool:
    try:
        # Just sleep, the SQSTileStore will try again after that...
        time.sleep(10)
        return False
    except KeyboardInterrupt:
        raise StopIteration  # pylint: disable=raise-missing-from


def get_queue_store(config: DatedConfig, daemon: bool) -> TimedTileStoreWrapper:
    """Get the quue tile store (Redir or SQS)."""
    if "redis" in config.config:
        # Create a Redis queue
        conf = config.config["redis"]
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
    config: DatedConfig,
) -> "botocore.client.SQS":
    if "sqs" not in config.config:
        sys.exit("The config hasn't any configured queue")
    sqs = boto3.resource("sqs", region_name=config.config["sqs"].get("region", "eu-west-1"))
    return sqs.get_queue_by_name(QueueName=config.config["sqs"]["queue"])
