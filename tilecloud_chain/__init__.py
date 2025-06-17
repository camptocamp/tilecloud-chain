"""TileCloud Chain."""

import asyncio
import contextvars
import datetime
import json
import logging
import logging.config
import math
import os
import pkgutil
import re
import shlex
import sqlite3
import sys
import tempfile
import time
from argparse import ArgumentParser, Namespace
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha1
from io import BytesIO
from itertools import product
from math import ceil, sqrt
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Literal, NamedTuple, TextIO, TypedDict, cast

import aiofiles
import boto3
import c2cwsgiutils.pyramid_logging
import c2cwsgiutils.setup_process
import jsonschema_validator
import psycopg2
import pyproj
import shapely.ops
from azure.identity import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from c2cwsgiutils import sentry
from PIL import Image
from prometheus_client import Counter, Summary
from ruamel.yaml import YAML
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import Polygon
from shapely.ops import unary_union
from shapely.wkb import loads as loads_wkb
from tilecloud import BoundingPyramid, Tile, TileCoord, TileGrid
from tilecloud.filter.error import LogErrors
from tilecloud.filter.logger import Logger
from tilecloud.grid.free import FreeTileGrid
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.store.mbtiles import MBTilesTileStore
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.store.redis import RedisTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.sqs import SQSTileStore, _maybe_stop

import tilecloud_chain.configuration
from tilecloud_chain import configuration
from tilecloud_chain.filter.error import MaximumConsecutiveErrors, TooManyError
from tilecloud_chain.multitilestore import MultiTileStore
from tilecloud_chain.store import (
    AsyncTileStore,
    CallWrapper,
    NoneTileStore,
    TileStoreWrapper,
)
from tilecloud_chain.store.azure_storage_blob import AzureStorageBlobTileStore
from tilecloud_chain.timedtilestore import TimedTileStoreWrapper

if TYPE_CHECKING:
    import botocore.client

_LOGGER = logging.getLogger(__name__)


_ERROR_COUNTER = Counter("tilecloud_chain_error_counter", "Number of errors", ["layer", "host"])
_GEOMS_GET_SUMMARY = Summary("tilecloud_chain_geoms_get", "Geoms filter get", ["layer", "host"])


_HOST_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("host")
_LAYER_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("layer")
_META_TILE_COORD_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar("meta_tilecoord")

_ALLOWED_COMMANDS = os.environ.get(
    "TILEGENERATION_ALLOWED_PROCESS_COMMANDS",
    "optipng,jpegoptim,pngquant",
).split(",")


def formatted_metadata(tile: Tile) -> str:
    """Get human readable string of the metadata."""
    metadata = dict(tile.metadata)
    if "tiles" in metadata:
        metadata["tiles"] = metadata["tiles"].keys()  # type: ignore[attr-defined]
    return " ".join([f"{k}={metadata[k]}" for k in sorted(metadata.keys())])


Tile.formated_metadata = property(formatted_metadata)  # type: ignore[method-assign,assignment]


def add_common_options(
    parser: ArgumentParser,
    tile_pyramid: bool = True,
    no_geom: bool = True,
    near: bool = True,
    time: bool = True,  # pylint: disable=redefined-outer-name
    dimensions: bool = False,
    cache: bool = True,
    default_config_file: bool = False,
    grid: bool = False,
) -> None:
    """Get the options used by some commands."""
    c2cwsgiutils.setup_process.fill_arguments(parser)
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=(
            os.environ.get("TILEGENERATION_CONFIGFILE", "tilegeneration/config.yaml")
            if default_config_file
            else None
        ),
        help="path to the configuration file",
        metavar="FILE",
    )
    parser.add_argument(
        "--host",
        help="the host name used in JSON logs and in the Prometheus stats",
        default="localhost",
    )
    parser.add_argument(
        "--ignore-error",
        action="store_true",
        help="continue if there is an error in the configuration",
    )
    parser.add_argument("-l", "--layer", metavar="NAME", help="the layer to generate")
    if tile_pyramid or grid:
        parser.add_argument(
            "-g",
            "--grid",
            help="the grid to use, if not specified, the default grid for the layer in the config file is used",
        )
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
            "-t",
            "--test",
            type=int,
            help="test with generating N tiles, and add log messages",
            metavar="N",
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
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="Display info message.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action="store_true",
        help="Display debug message, and stop on first error.",
    )


def get_tile_matrix_identifier(
    grid: tilecloud_chain.configuration.Grid,
    resolution: float | None = None,
    zoom: int | None = None,
) -> str:
    """Get an identifier for a tile matrix."""
    if grid is None or grid.get("matrix_identifier", configuration.MATRIX_IDENTIFIER_DEFAULT) == "zoom":
        return str(zoom)
    assert zoom is not None
    if resolution is None:
        resolution = grid["resolutions"][zoom]
    if int(resolution) == resolution:
        return str(int(resolution))
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
        functions: list[Callable[[Tile], Awaitable[Tile | None]]],
        out: IO[str] | None = None,
    ) -> None:
        self.gene = gene
        self.functions = functions
        self.out = out
        self.safe = gene.options is None or not gene.options.debug
        daemon = gene.options is not None and getattr(gene.options, "daemon", False)
        self.max_consecutive_errors = (
            MaximumConsecutiveErrors(
                gene.get_main_config()
                .config["generation"]
                .get(
                    "maxconsecutive_errors",
                    configuration.MAX_CONSECUTIVE_ERRORS_DEFAULT,
                ),
            )
            if not daemon and gene.maxconsecutive_errors
            else None
        )
        self.error = 0
        self.error_lock = asyncio.Lock()
        self.error_logger = LogErrors(
            _LOGGER,
            logging.ERROR,
            "Error in tile: %(tilecoord)s, %(formated_metadata)s, %(error)r",
        )

    async def __call__(self, tile: Tile | None) -> Tile | None:
        """Run the tile generation."""
        if tile is None:
            return None

        if "tiles" in tile.metadata:
            tile.metadata["tiles"][tile.tilecoord] = tile  # type: ignore[index]

        tilecoord = tile.tilecoord
        _LOGGER.debug("[%s] Metadata: %s", tilecoord, tile.formated_metadata)
        for func in self.functions:
            try:
                _LOGGER.debug("[%s] Run: %s", tilecoord, func)
                n = datetime.datetime.now(tz=datetime.timezone.utc)
                if self.safe:
                    try:
                        tile = await func(tile)
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        _LOGGER.exception("[%s] Fail to process function %s", tilecoord, func)
                        assert tile is not None
                        tile.error = e
                else:
                    tile = await func(tile)
                _LOGGER.debug(
                    "[%s] %s in %s",
                    tilecoord,
                    func.time_message if getattr(func, "time_message", None) is not None else func,  # type: ignore[attr-defined]
                    str(datetime.datetime.now(tz=datetime.timezone.utc) - n),
                )
                if tile is None:
                    _LOGGER.debug("[%s] Drop", tilecoord)
                    return None
                if tile.error:
                    if tile.content_type and (
                        tile.content_type in ["application/xml", "text/xml"]
                        or tile.content_type.startswith("application/vnd.ogc.se_xml;")
                        or tile.content_type.startswith("text/html;")
                    ):
                        assert isinstance(tile.error, str)
                        tile.error = f"WMS server error: {self._re_rm_xml_tag.sub('', tile.error)}"
                    if self.out:
                        print(
                            f"Error with tile {tile.tilecoord} {tile.formated_metadata}:\n{tile.error}",
                            file=self.out,
                        )
                    _LOGGER.warning(
                        "Error with tile %s %s:\n%s",
                        tile.tilecoord,
                        tile.formated_metadata,
                        tile.error,
                    )
                    _ERROR_COUNTER.labels(
                        tile.metadata.get("layer", "none"),
                        tile.metadata.get("host", "none"),
                    ).inc()

                    if "error_file" in self.gene.get_main_config().config["generation"]:
                        self.gene.log_tiles_error(tile=tile, message=repr(tile.error))

                    if self.max_consecutive_errors is not None:
                        self.max_consecutive_errors(tile)

                    if self.gene.queue_store is not None:
                        await self.gene.queue_store.delete_one(tile)
                    async with self.error_lock:
                        self.error += 1
                    return tile
            except Exception:
                _LOGGER.debug("Run error", exc_info=True)
                raise

        if self.max_consecutive_errors is not None:
            self.max_consecutive_errors(tile)

        return tile


class Close:
    """Database closer."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def __call__(self) -> None:
        """Close the database."""
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

    def __init__(
        self,
        config: tilecloud_chain.configuration.Configuration,
        mtime: float,
        file: Path,
    ) -> None:
        self.config = config
        self.mtime = mtime
        self.file = file


class DatedGeoms:
    """Geoms with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, geoms: dict[str | int, BaseGeometry], mtime: float) -> None:
        self.geoms = geoms
        self.mtime = mtime


class DatedTileGrid:
    """TilGrid with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, grid: TileGrid, mtime: float) -> None:
        self.grid = grid
        self.mtime = mtime


class DatedHosts:
    """Host with timestamps to be able to invalidate it on configuration change."""

    def __init__(self, hosts: dict[str, Path], mtime: float) -> None:
        self.hosts = hosts
        self.mtime = mtime


class MissingErrorFileError(Exception):
    """Missing error file exception."""


class LoggingInformation(TypedDict):
    """Logging information."""

    host: str | None
    layer: str | None
    meta_tilecoord: str


class JsonLogHandler(c2cwsgiutils.pyramid_logging.JsonLogHandler):
    """Log to stdout in JSON."""

    def __init__(self, stream: TextIO | None = None) -> None:
        super().__init__(stream)
        self.addFilter(TileFilter())


class TileFilter(logging.Filter):
    """A logging filter that adds request information to CEE logs."""

    def filter(self, record: Any) -> bool:
        """Add the request information to the log record."""
        record.tcc_host = _HOST_CONTEXT.get()
        record.tcc_layer = _LAYER_CONTEXT.get()
        record.tcc_meta_tilecoord = _META_TILE_COORD_CONTEXT.get()

        return True


def get_azure_container_client(container: str) -> ContainerClient:
    """Get the Azure blog storage client."""
    if os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        return BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"],
        ).get_container_client(container=container)
    if "AZURE_STORAGE_BLOB_CONTAINER_URL" in os.environ:
        container_client = ContainerClient.from_container_url(os.environ["AZURE_STORAGE_BLOB_CONTAINER_URL"])
        if os.environ.get("AZURE_STORAGE_BLOB_VALIDATE_CONTAINER_NAME", "true").lower() == "true":
            assert container == container_client.container_name, (
                f"Container name mismatch: {container} != {container_client.container_name}"
            )
        return container_client
    return BlobServiceClient(
        account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
        credential=DefaultAzureCredential(),  # type: ignore[arg-type]
    ).get_container_client(container=container)


def get_grid_name(
    config: DatedConfig,
    layer_name: str,
    grid_name: str | None,
) -> str:
    """Get the grid name."""
    layer = config.config["layers"][layer_name]
    if "grid" in layer:
        _LOGGER.warning(
            "The layer %s has a 'grid' key, it is deprecated, use 'grids' instead.",
            layer_name,
        )
    if grid_name is None and "grid" in layer:
        grid_name = layer["grid"]
    if grid_name is None:
        grid_names = get_grid_names(config, layer_name)
        if len(grid_names) == 1:
            return grid_names[0]

        grid_names_str = "'" + "', '".join(grid_names) + "'"
        message = (
            f"There is more the one grid for the layer '{layer_name}' specify one grid with the --grid option from {grid_names_str}."
            if grid_names
            else f"There is no grid for le layer '{layer_name}'!"
        )
        raise ValueError(message)
    return grid_name


def get_grid_config(
    config: DatedConfig,
    layer_name: str,
    grid_name: str | None,
) -> tilecloud_chain.configuration.Grid:
    """Get the grid configuration."""
    return config.config["grids"][get_grid_name(config, layer_name, grid_name)]


def get_grid_names(
    config: DatedConfig,
    layer_name: str,
    grid_name: str | None = None,
) -> list[str]:
    """Get the grid names for a layer."""
    if layer_name not in config.config.get("layers", {}):
        layers_str = "'" + "', '".join(config.config.get("layers", {}).keys()) + "'"
        message = (
            f"Layer '{layer_name}' not found in the configuration available layers: {layers_str}."
            " Please check the configuration file or the layer name."
        )
        raise ValueError(message)
    layer = config.config["layers"][layer_name]
    if "grid" in layer:
        _LOGGER.warning(
            "The layer %s has a 'grid' key, it is deprecated, use 'grids' instead.",
            layer_name,
        )

    grid_names = []
    if "grids" in layer:
        grid_names = layer["grids"]
    elif "grid" in layer:
        grid_names = [layer["grid"]]
    else:
        grid_names = list(config.config["grids"].keys())

    if grid_name is not None:
        if grid_name not in grid_names:
            grid_names_str = "'" + "', '".join(grid_names) + "'"
            message = f"The grid name '{grid_name}' is invalid, he should be in {grid_names_str}"
            raise ValueError(message)
        return [grid_name]
    return grid_names


def get_proj4_literal(srs: int) -> str:
    """Get the proj4 literal for a given SRS."""
    # Map known SRS values to their proj4 literals
    proj4_literals = {
        3857: (
            "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 "
            "+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over"
        ),
        21781: (
            "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 "
            "+x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 "
            "+units=m +no_defs"
        ),
        2056: (
            "+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 "
            "+x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 "
            "+units=m +no_defs"
        ),
    }

    # Return the proj4 literal for the given SRS, or a default format if not found
    return proj4_literals.get(srs, f"+init=EPSG:{srs}")


def transform_bbox(proj4_literals_src: str, proj4_literals_dst: str, bbox: list[float]) -> list[float]:
    """
    Transform a bounding box from source projection to destination projection.

    Args:
        proj4_literals_src: Source projection as proj4 literal string
        proj4_literals_dst: Destination projection as proj4 literal string
        bbox: Bounding box in source projection as [xmin, ymin, xmax, ymax]

    Returns
    -------
        Transformed bounding box as [xmin, ymin, xmax, ymax]
    """
    source_projection = pyproj.CRS.from_proj4(proj4_literals_src)
    dest_projection = pyproj.CRS.from_proj4(proj4_literals_dst)
    transformer = pyproj.Transformer.from_crs(source_projection, dest_projection)

    point_1 = transformer.transform(bbox[0], bbox[1])
    point_2 = transformer.transform(bbox[2], bbox[3])

    return [point_1[0], point_1[1], point_2[0], point_2[1]]


class TileGeneration:
    """Base class of all the tile generation."""

    tilestream: AsyncIterator[Tile] | None = None
    duration = datetime.timedelta()
    error = 0
    queue_store: AsyncTileStore | None = None
    daemon = False

    def __init__(
        self,
        config_file: Path | None = None,
        options: Namespace | None = None,
        layer_name: str | None = None,
        base_config: tilecloud_chain.configuration.Configuration | None = None,
        configure_logging: bool = True,
        multi_task: bool = True,
        maxconsecutive_errors: bool = True,
        out: IO[str] | None = None,
    ) -> None:
        self.geoms_cache: dict[Path, dict[str, dict[str, DatedGeoms]]] = {}
        self._close_actions: list[Close] = []
        self.error_lock = asyncio.Lock()
        self.error_files_: dict[str, TextIO] = {}
        self.functions_tiles: list[Callable[[Tile], Awaitable[Tile | None]]] = []
        self.functions_metatiles: list[Callable[[Tile], Awaitable[Tile | None]]] = []
        self.functions: list[Callable[[Tile], Awaitable[Tile | None]]] = self.functions_metatiles
        self.maxconsecutive_errors = maxconsecutive_errors
        self.out = out
        self.grid_cache: dict[Path, dict[str, DatedTileGrid]] = {}
        self.layer_legends: dict[str, list[Legend]] = {}
        self.config_file = config_file
        self.base_config = base_config
        self.multi_task = multi_task
        self.configs: dict[Path, DatedConfig] = {}
        self.hosts_cache: DatedHosts | None = None

        class Options(NamedTuple):
            verbose: bool
            debug: bool
            quiet: bool
            bbox: Any
            zoom: Any
            test: Any
            near: Any
            time: Any
            geom: bool
            ignore_error: bool

        self.options: Namespace = options or Options(  # type: ignore[assignment]
            verbose=False,
            debug=False,
            quiet=False,
            bbox=None,
            zoom=None,
            test=None,
            near=None,
            time=None,
            geom=True,
            ignore_error=False,
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

        if configure_logging and os.environ.get("CI", "false").lower() != "true":
            ###
            # logging configuration
            # https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
            ###
            logging.config.dictConfig(
                {
                    "version": 1,
                    "root": {
                        "level": os.environ["OTHER_LOG_LEVEL"],
                        "handlers": [os.environ["LOG_TYPE"]],
                    },
                    "loggers": {
                        # "level = INFO" logs SQL queries.
                        # "level = DEBUG" logs SQL queries and results.
                        # "level = WARN" logs neither.  (Recommended for production systems.)
                        "sqlalchemy.engine": {"level": os.environ["SQL_LOG_LEVEL"]},
                        "c2cwsgiutils": {"level": os.environ["C2CWSGIUTILS_LOG_LEVEL"]},
                        "tilecloud": {"level": os.environ["TILECLOUD_LOG_LEVEL"]},
                        "tilecloud_chain": {"level": os.environ["TILECLOUD_CHAIN_LOG_LEVEL"]},
                    },
                    "handlers": {
                        "console": {
                            "class": "logging.StreamHandler",
                            "formatter": "generic",
                            "stream": "ext://sys.stdout",
                        },
                        "json": {
                            "class": "tilecloud_chain.JsonLogHandler",
                            "formatter": "generic",
                            "stream": "ext://sys.stdout",
                        },
                    },
                    "formatters": {
                        "generic": {
                            "format": "%(asctime)s [%(process)d] [%(levelname)-5.5s] %(message)s",
                            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
                            "class": "logging.Formatter",
                        },
                    },
                },
            )
            sentry.includeme()

        assert "generation" in self.get_main_config().config, self.get_main_config().config

        error = False
        if self.options is not None and self.options.zoom is not None:
            error_message = (
                f"The zoom argument '{self.options.zoom}' has incorrect format, "
                "it can be a single value, a range (3-9), a list of values (2,5,7)."
            )
            if self.options.zoom.find("-") >= 0:
                splitted_zoom: list[str] = self.options.zoom.split("-")
                if len(splitted_zoom) != 2:
                    _LOGGER.error(error_message)
                    error = True
                try:
                    self.options.zoom = range(int(splitted_zoom[0]), int(splitted_zoom[1]) + 1)
                except ValueError:
                    _LOGGER.exception(error_message)
                    error = True
            elif self.options.zoom.find(",") >= 0:
                try:
                    self.options.zoom = [int(z) for z in self.options.zoom.split(",")]
                except ValueError:
                    _LOGGER.exception(error_message)
                    error = True
            else:
                try:
                    self.options.zoom = [int(self.options.zoom)]
                except ValueError:
                    _LOGGER.exception(error_message)
                    error = True

        if error:
            sys.exit(1)

        if layer_name and self.config_file:
            assert layer_name is not None
            self.create_log_tiles_error(layer_name)

    def get_host_config_file(self, host: str | None) -> Path | None:
        """Get the configuration file name for the given host."""
        if self.config_file:
            return self.config_file
        assert host
        if host not in self.get_hosts():
            _LOGGER.error("Missing host '%s' in global config", host)
            return None
        config_file = self.get_hosts().get(
            host,
            (
                Path(os.environ["TILEGENERATION_CONFIGFILE"])
                if "TILEGENERATION_CONFIGFILE" in os.environ
                else None
            ),
        )
        _LOGGER.debug("For the host %s, use config file: %s", host, config_file)
        return config_file

    def get_host_config(self, host: str | None) -> DatedConfig:
        """Get the configuration for the given host."""
        config_file = self.get_host_config_file(host)
        if not config_file:
            _LOGGER.error("No config file for host %s", host)
        return (
            self.get_config(config_file)
            if config_file
            else DatedConfig(cast("tilecloud_chain.configuration.Configuration", {}), 0, Path())
        )

    def get_tile_config(self, tile: Tile) -> DatedConfig:
        """Get the configuration for the given tile."""
        return self.get_config(Path(tile.metadata["config_file"]))

    def get_config(
        self,
        config_file: Path,
        ignore_error: bool = True,
        base_config: tilecloud_chain.configuration.Configuration | None = None,
    ) -> DatedConfig:
        """Get the validated configuration for the file name, with cache management."""
        if not config_file.exists():
            _LOGGER.error("Missing config file %s", config_file)
            if ignore_error:
                return DatedConfig(cast("tilecloud_chain.configuration.Configuration", {}), 0, Path())
            sys.exit(1)

        config: DatedConfig | None = self.configs.get(config_file)
        if config is not None and config.mtime == config_file.stat().st_mtime:
            return config

        config, success = self._get_config(config_file, ignore_error, base_config)
        if not success or config is None:
            if ignore_error:
                config = DatedConfig(cast("tilecloud_chain.configuration.Configuration", {}), 0, Path())
            else:
                sys.exit(1)
        self.configs[config_file] = config
        return config

    def get_main_config(self) -> DatedConfig:
        """Get the main configuration."""
        if os.environ.get("TILEGENERATION_MAIN_CONFIGFILE"):
            return self.get_config(Path(os.environ["TILEGENERATION_MAIN_CONFIGFILE"]), ignore_error=False)
        if self.config_file:
            return self.get_config(self.config_file, self.options.ignore_error, self.base_config)
        _LOGGER.error("No provided configuration file")
        return DatedConfig({}, 0, Path())

    def _fill_host(self, hosts: dict[str, Path], config=dict[str, Any]) -> None:  # type: ignore[no-untyped-def] # noqa: ANN001
        for key, value in config.items():
            if isinstance(value, dict):
                self._fill_host(hosts, value)
            elif isinstance(value, str):
                hosts[key] = Path(value)
            else:
                _LOGGER.error("Invalid value for host: %s", value)

    def get_hosts(self, silent: bool = False) -> dict[str, Path]:
        """Get the hosts from the hosts file."""
        file_path = Path(os.environ["TILEGENERATION_HOSTSFILE"])
        if not file_path.exists():
            if not silent:
                _LOGGER.error("Missing hosts file %s", file_path)
            return {}

        if self.hosts_cache is not None and self.hosts_cache.mtime == file_path.stat().st_mtime:
            return self.hosts_cache.hosts

        with file_path.open(encoding="utf-8") as hosts_file:
            ruamel = YAML(typ="safe")
            hosts: dict[str, Path] = {}
            hosts_raw = ruamel.load(hosts_file)
            if "sources" in hosts_raw:
                self._fill_host(hosts, hosts_raw["sources"])
            else:
                hosts = hosts_raw

        self.hosts_cache = DatedHosts(hosts, file_path.stat().st_mtime)
        return hosts

    def _get_config(
        self,
        config_file: Path,
        ignore_error: bool,
        base_config: tilecloud_chain.configuration.Configuration | None = None,
    ) -> tuple[DatedConfig, bool]:
        """Get the validated configuration for the file name."""
        with config_file.open(encoding="utf-8") as f:
            config: dict[str, Any] = {}
            config.update({} if base_config is None else base_config)
            ruamel = YAML()
            config.update(ruamel.load(f))

        dated_config = DatedConfig(
            cast("tilecloud_chain.configuration.Configuration", config),
            Path(config_file).stat().st_mtime,
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
        errors, _ = jsonschema_validator.validate(
            str(config.file),
            cast("dict[str, Any]", config.config),
            json.loads(schema_data),
        )

        if errors:
            _LOGGER.error("The config file is invalid:\n%s", "\n".join(errors))
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
                        _LOGGER.error(
                            "The resolution %s * resolution_scale %s is not an integer.",
                            resolution,
                            scale,
                        )
                        error = True
            else:
                grid["resolution_scale"] = self._resolution_scale(grid["resolutions"])

            srs = int(grid.get("srs", configuration.SRS_DEFAULT).split(":")[1])
            if "proj4_literal" not in grid:
                grid["proj4_literal"] = get_proj4_literal(srs)

        layers = config.config.get("layers", {})
        for lname, layer in sorted(layers.items()):
            if "srs" in layer and "proj4_literal" not in layer:
                srs = int(layer["srs"].split(":")[1])
                layer["proj4_literal"] = get_proj4_literal(srs)
            if "headers" not in layer and layer["type"] == "wms":
                layer["headers"] = {
                    "Cache-Control": "no-cache, no-store",
                    "Pragma": "no-cache",
                }
            if layer["type"] == "mapnik" and layer.get("output_format", "png") == "grid" and layer["meta"]:
                _LOGGER.error(
                    "The layer '%s' is of type Mapnik/Grid, that can't support matatiles.",
                    lname,
                )
                error = True

        if error and not (
            ignore_error or os.environ.get("TILEGENERATION_IGNORE_CONFIG_ERROR", "FALSE").lower() == "true"
        ):
            sys.exit(1)

        return not (error or errors)

    def init(self, queue_store: AsyncTileStore | None = None, daemon: bool = False) -> None:
        """Initialize the tile generation."""
        self.queue_store = queue_store
        self.daemon = daemon

    @staticmethod
    def _primefactors(x: int) -> list[int]:
        factorlist = []
        loop = 2
        while loop <= x:
            if x % loop == 0:
                x = round(x / loop)
                factorlist.append(loop)
            else:
                loop += 1
        return factorlist

    def _resolution_scale(self, resolutions: list[float] | list[int]) -> int:
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

    def get_all_dimensions(self, layer: tilecloud_chain.configuration.Layer) -> list[dict[str, str]]:
        """Get all the dimensions."""
        assert layer is not None

        options_dimensions = {}
        for opt_dim in self.options.dimensions:
            opt_dim = opt_dim.split("=")  # noqa: PLW2901
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
        grid_name: str | None,
        read_only: bool = False,
    ) -> AsyncTileStore | None:
        """Get the tile store."""
        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer %s not found in config %s", layer_name, config.file)
            return None
        layer = config.config["layers"][layer_name]
        grid = get_grid_config(config, layer_name, grid_name)
        layout = WMTSTileLayout(
            layer=layer_name,
            url=cache["folder"],
            style=layer["wmts_style"],
            format_pattern="." + layer["extension"],
            dimensions_name=[dimension["name"] for dimension in layer.get("dimensions", [])],
            tile_matrix_set=get_grid_name(config, layer_name, grid_name),
            tile_matrix=lambda z: get_tile_matrix_identifier(grid, zoom=z),
            request_encoding="REST",
        )
        # store
        if cache["type"] == "s3":
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            # on s3
            cache_tilestore: AsyncTileStore = TileStoreWrapper(
                S3TileStore(
                    cache_s3["bucket"],
                    layout,
                    s3_host=cache.get("host", "s3-eu-west-1.amazonaws.com"),
                    cache_control=cache.get("cache_control"),
                ),
            )
        elif cache["type"] == "azure":
            cache_azure = cast("tilecloud_chain.configuration.CacheAzureTyped", cache)
            # on Azure
            cache_tilestore = AzureStorageBlobTileStore(
                tilelayout=layout,
                cache_control=cache_azure.get("cache_control"),
                container_client=get_azure_container_client(cache_azure["container"]),
            )
        elif cache["type"] == "mbtiles":
            metadata = {}
            for dimension in layer["dimensions"]:
                metadata["dimension_" + dimension["name"]] = dimension["default"]
            # on mbtiles file
            filename = Path(
                layout.filename(TileCoord(0, 0, 0), metadata=metadata).replace("/0/0/0", "") + ".mbtiles",
            )
            filename.parent.mkdir(parents=True, exist_ok=True)
            cache_tilestore = TileStoreWrapper(
                MBTilesTileStore(
                    sqlite3.connect(filename),
                    content_type=layer["mime_type"],
                    tilecoord_in_topleft=True,
                ),
            )
        elif cache["type"] == "bsddb":
            metadata = {}
            for dimension in layer["dimensions"]:
                metadata["dimension_" + dimension["name"]] = dimension["default"]
            import bsddb3 as bsddb  # pylint: disable=import-outside-toplevel,import-error
            from tilecloud.store.bsddb import (  # pylint: disable=import-outside-toplevel
                BSDDBTileStore,
            )

            # on bsddb file
            filename = Path(
                layout.filename(TileCoord(0, 0, 0), metadata=metadata).replace("/0/0/0", "") + ".bsddb",
            )
            filename.parent.mkdir(parents=True, exist_ok=True)
            db = bsddb.hashopen(
                filename,
                # and os.path.exists(filename) to avoid error on non existing file
                "r" if read_only and filename.exists() else "c",
            )

            self._close_actions.append(Close(db))

            cache_tilestore = TileStoreWrapper(
                BSDDBTileStore(
                    db,
                    content_type=layer["mime_type"],
                ),
            )
        elif cache["type"] == "filesystem":
            # on filesystem
            cache_tilestore = TileStoreWrapper(
                FilesystemTileStore(
                    layout,
                    content_type=layer["mime_type"],
                ),
            )
        else:
            sys.exit("unknown cache type: " + cache["type"])

        return cache_tilestore

    def get_tilesstore(self, cache: str | None = None) -> TimedTileStoreWrapper:
        """Get the tile store."""
        gene = self

        def get_store(config_file: Path, layer_name: str, grid_name: str | None) -> AsyncTileStore | None:
            config = gene.get_config(config_file)
            cache_name = cache or config.config["generation"].get(
                "default_cache",
                configuration.DEFAULT_CACHE_DEFAULT,
            )
            cache_obj = config.config["caches"][cache_name]
            return self.get_store(config, cache_obj, layer_name, grid_name)

        return TimedTileStoreWrapper(
            MultiTileStore(get_store),
            store_name="store",
        )

    def add_geom_filter(self) -> None:
        """Add a geometry filter to the chain."""
        self.imap(IntersectGeometryFilter(gene=self), "Intersect with geom")

    def add_logger(self) -> None:
        """Add a logger to the chain."""
        if (
            not self.options.quiet
            and not self.options.verbose
            and not self.options.debug
            and os.environ.get("FRONTEND") != "noninteractive"
        ):

            async def log_tiles(tile: Tile) -> Tile:
                sys.stdout.write(f"{tile.tilecoord} {tile.formated_metadata}                         \r")
                sys.stdout.flush()
                return tile

            self.imap(log_tiles)
        elif not self.options.quiet and getattr(self.options, "role", None) != "server":
            self.imap(CallWrapper(Logger(_LOGGER, logging.INFO, "%(tilecoord)s, %(formated_metadata)s")))

    async def add_metatile_splitter(self, store: AsyncTileStore | None = None) -> None:
        """Add a metatile splitter to the chain."""
        assert self.functions != self.functions_tiles, "add_metatile_splitter should not be called twice"
        if store is None:
            gene = self

            def get_splitter(
                config_file: Path,
                layer_name: str,
                grid_name: str | None,
            ) -> AsyncTileStore | None:
                config = gene.get_config(config_file)
                if layer_name not in config.config.get("layers", {}):
                    _LOGGER.warning("Layer %s not found in config %s", layer_name, config_file)
                    return None
                layer = config.config["layers"][layer_name]
                if layer.get("meta"):
                    return TileStoreWrapper(
                        MetaTileSplitterTileStore(
                            layer["mime_type"],
                            get_grid_config(config, layer_name, grid_name).get(
                                "tile_size",
                                configuration.TILE_SIZE_DEFAULT,
                            ),
                            layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT),
                        ),
                    )
                return NoneTileStore()

            store = TimedTileStoreWrapper(MultiTileStore(get_splitter), store_name="splitter")

        run = Run(self, self.functions_tiles, out=self.out)

        async def meta_get(metatile: Tile) -> Tile:
            assert store is not None

            async def _async_metatile() -> AsyncIterator[Tile]:
                yield metatile

            substream = store.get(_async_metatile())
            if getattr(self.options, "role", "") == "hash":
                tile = await anext(substream)
                assert tile is not None
                await run(tile)
            else:
                tasks = []
                async for tile in substream:
                    assert tile is not None
                    tasks.append(run(tile))
                await asyncio.gather(*tasks)

                async with self.error_lock:
                    self.error += run.error
            return metatile

        self.imap(meta_get)
        self.functions = self.functions_tiles

    def create_log_tiles_error(self, layer: str) -> TextIO | None:
        """Create the error file for the given layer."""
        if "error_file" in self.get_main_config().config.get("generation", {}):
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            time_ = now.strftime("%d-%m-%Y %H:%M:%S")
            error_file = Path(  # pylint: disable=consider-using-with # noqa: SIM115
                self.get_main_config().config["generation"]["error_file"].format(layer=layer, datetime=now),
            ).open("a", encoding="utf-8")
            error_file.write(f"# [{time_}] Start the layer '{layer}' generation\n")
            self.error_files_[layer] = error_file
            return error_file
        return None

    def close(self) -> None:
        """Close the tile generation."""
        for file_ in self.error_files_.values():
            file_.close()

    def get_log_tiles_error_file(self, layer: str) -> TextIO | None:
        """Get the error file for the given layer."""
        return self.error_files_[layer] if layer in self.error_files_ else self.create_log_tiles_error(layer)

    def log_tiles_error(self, tile: Tile | None = None, message: str | None = None) -> None:
        """Log the error message for the given tile."""
        if tile is None:
            return
        config = self.get_tile_config(tile)
        if "error_file" in config.config["generation"]:
            assert tile is not None

            time_ = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%d-%m-%Y %H:%M:%S")
            if self.get_log_tiles_error_file(tile.metadata["layer"]) is None:
                message = "Missing error file"
                raise MissingErrorFileError(message)

            tilecoord = "" if tile.tilecoord is None else f"{tile.tilecoord} {tile.formated_metadata} "
            message = "" if message is None else f" {message}"

            io = self.get_log_tiles_error_file(tile.metadata["layer"])
            assert io is not None
            out_message = message.replace("\n", " ")
            io.write(f"{tilecoord}# [{time_}]{out_message}\n")

    def get_grid(self, config: DatedConfig, grid_name: str) -> TileGrid:
        """Get the grid for the given name."""
        dated_grid = self.grid_cache.get(config.file, {}).get(grid_name)
        if dated_grid is not None and config.mtime == dated_grid.mtime:
            return dated_grid.grid

        grid = config.config["grids"][grid_name]
        scale = grid["resolution_scale"]

        tilegrid = FreeTileGrid(
            resolutions=cast("list[int]", [r * scale for r in grid["resolutions"]]),
            scale=scale,
            max_extent=cast("tuple[int, int, int, int]", grid["bbox"]),
            tile_size=grid.get("tile_size", configuration.TILE_SIZE_DEFAULT),
        )

        self.grid_cache.setdefault(config.file, {})[grid_name] = DatedTileGrid(tilegrid, config.mtime)
        return tilegrid

    def get_geoms(
        self,
        config: DatedConfig,
        layer_name: str,
        grid_name: str,
        host: str | None = None,
    ) -> dict[str | int, BaseGeometry]:
        """Get the geometries for the given layer."""
        dated_geoms = self.geoms_cache.get(config.file, {}).get(layer_name, {}).get(grid_name)
        if dated_geoms is not None and config.mtime == dated_geoms.mtime:
            return dated_geoms.geoms

        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer %s not found in config %s", layer_name, config.file)
            return {}
        layer = config.config["layers"][layer_name]

        grid = get_grid_config(config, layer_name, grid_name)

        layer_bbox: list[int | float] | None = layer.get("bbox")
        # Repoject the layer bbox
        if (
            layer_bbox
            and "proj4_literal" in layer
            and "proj4_literal" in grid
            and layer["proj4_literal"] != grid["proj4_literal"]
        ):
            layer_bbox = transform_bbox(layer["proj4_literal"], grid["proj4_literal"], layer_bbox)

        if self.options.near is not None or (
            self.options.time is not None and layer_bbox is not None and self.options.zoom is not None
        ):
            if self.options.zoom is None or len(self.options.zoom) != 1:
                sys.exit("Option --near needs the option --zoom with one value.")
            if not (self.options.time is not None or self.options.test is not None):
                sys.exit("Option --near needs the option --time or --test.")
            position = (
                self.options.near
                if self.options.near is not None or layer_bbox is None
                else [
                    (layer_bbox[0] + layer_bbox[2]) / 2,
                    (layer_bbox[1] + layer_bbox[3]) / 2,
                ]
            )
            grid_bbox = grid["bbox"]
            diff = [position[0] - grid_bbox[0], position[1] - grid_bbox[1]]
            resolution = grid["resolutions"][self.options.zoom[0]]
            mt_to_m = (
                layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT)
                * grid.get("tile_size", configuration.TILE_SIZE_DEFAULT)
                * resolution
            )
            mt = [float(d) / mt_to_m for d in diff]

            nb_tile = self.options.time * 3 if self.options.time is not None else self.options.test
            nb_mt = nb_tile / (layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT) ** 2)
            nb_sqrt_mt = ceil(sqrt(nb_mt))

            mt_origin = [round(m - nb_sqrt_mt / 2) for m in mt]
            extent = [
                grid_bbox[0] + mt_origin[0] * mt_to_m,
                grid_bbox[1] + mt_origin[1] * mt_to_m,
                grid_bbox[0] + (mt_origin[0] + nb_sqrt_mt) * mt_to_m,
                grid_bbox[1] + (mt_origin[1] + nb_sqrt_mt) * mt_to_m,
            ]
        elif self.options.bbox is not None:
            if (
                "proj4_literal" in layer
                and "proj4_literal" in grid
                and (layer["proj4_literal"] != grid["proj4_literal"])
            ):
                extent = transform_bbox(layer["proj4_literal"], grid["proj4_literal"], self.options.bbox)
            else:
                extent = self.options.bbox
        elif layer_bbox is not None:
            extent = layer_bbox
        else:
            extent = grid["bbox"]

        geoms: dict[str | int, BaseGeometry] = {}
        if extent:
            geom = Polygon(
                (
                    (extent[0], extent[1]),
                    (extent[0], extent[3]),
                    (extent[2], extent[3]),
                    (extent[2], extent[1]),
                ),
            )
            for z, _ in enumerate(grid["resolutions"]):
                geoms[z] = geom

        if self.options.near is None and self.options.geom:
            for g in layer.get("geoms", []):
                with _GEOMS_GET_SUMMARY.labels(layer_name, host if host else self.options.host).time():
                    connection = psycopg2.connect(g["connection"])
                    cursor = connection.cursor()
                    sql = f"SELECT ST_AsBinary(geom) FROM (SELECT {g['sql']}) AS g"  # nosec # noqa: S608
                    _LOGGER.info("Execute SQL: %s.", sql)
                    cursor.execute(sql)
                    geom_list = [loads_wkb(bytes(r[0])) for r in cursor.fetchall()]
                    geom = unary_union(geom_list)

                    # Reproject the geometry if needed
                    if (
                        "proj4_literal" in layer
                        and "proj4_literal" in grid
                        and layer["proj4_literal"] != grid["proj4_literal"]
                    ):
                        # Create transformer from layer to grid projection
                        source_projection = pyproj.CRS.from_proj4(layer["proj4_literal"])
                        dest_projection = pyproj.CRS.from_proj4(grid["proj4_literal"])
                        transformer = pyproj.Transformer.from_crs(source_projection, dest_projection)
                        # Transform the geometry
                        geom = shapely.ops.transform(transformer.transform, geom)

                    if extent:
                        geom = geom.intersection(
                            Polygon(
                                (
                                    (extent[0], extent[1]),
                                    (extent[0], extent[3]),
                                    (extent[2], extent[3]),
                                    (extent[2], extent[1]),
                                ),
                            ),
                        )
                    for z, r in enumerate(grid["resolutions"]):
                        if ("min_resolution" not in g or g["min_resolution"] <= r) and (
                            "max_resolution" not in g or g["max_resolution"] >= r
                        ):
                            geoms[z] = geom
                    cursor.close()
                    connection.close()

        self.geoms_cache.setdefault(config.file, {}).setdefault(layer_name, {})[grid_name] = DatedGeoms(
            geoms,
            config.mtime,
        )
        return geoms

    def init_tilecoords(self, config: DatedConfig, layer_name: str, used_grid_name: str | None) -> None:
        """Initialize the tilestream for the given layer."""
        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer %s not found in config %s", layer_name, config.file)
            return
        layer = config.config["layers"][layer_name]
        grid_names = get_grid_names(config, layer_name, used_grid_name)
        _LOGGER.debug(
            "Initialize tilecoords for layer %s with grids %s (%s)",
            layer_name,
            ", ".join(grid_names),
            used_grid_name if used_grid_name else "-",
        )
        grid_tilecoords: dict[str, Iterable[TileCoord]] = {}
        for grid_name in grid_names:
            grid = get_grid_config(config, layer_name, grid_name)
            resolutions = grid["resolutions"]

            if self.options.time is not None and self.options.zoom is None:
                if "min_resolution_seed" in layer:
                    self.options.zoom = [resolutions.index(layer["min_resolution_seed"])]
                else:
                    self.options.zoom = [len(resolutions) - 1]

            if self.options.zoom is not None:
                zoom_max = len(resolutions) - 1
                for zoom in self.options.zoom:
                    if zoom > zoom_max:
                        _LOGGER.warning(
                            "zoom %i is greater than the maximum zoom %i of grid %s of layer %s, ignored.",
                            zoom,
                            zoom_max,
                            grid_name,
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
                            _LOGGER.warning(
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
            tilegrid = self.get_grid(config, get_grid_name(config, layer_name, grid_name))
            bounding_pyramid = BoundingPyramid(tilegrid=tilegrid)
            geoms = self.get_geoms(config, layer_name, grid_name)
            for zoom in self.options.zoom:
                if zoom in geoms:
                    extent = geoms[zoom].bounds

                    if len([e for e in extent if not math.isnan(e)]) == 0:
                        _LOGGER.warning("bounds empty for zoom %s", zoom)
                    else:
                        minx, miny, maxx, maxy = extent
                        px_buffer = layer.get("px_buffer", configuration.LAYER_PIXEL_BUFFER_DEFAULT)
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
                            ),
                        )
                        bounding_pyramid.add(
                            tilegrid.tilecoord(
                                zoom,
                                min(maxx, tilegrid.max_extent[2]),
                                min(maxy, tilegrid.max_extent[3]),
                            ),
                        )
            if layer["meta"]:
                grid_tilecoords[grid_name] = bounding_pyramid.metatilecoords(
                    layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT),
                )
            else:
                grid_tilecoords[grid_name] = bounding_pyramid
        self.set_tilecoords(config, grid_tilecoords, layer_name)

    @staticmethod
    async def _tilestream(
        grid_tilecoords: dict[str, Iterable[TileCoord]],
        default_metadata: dict[str, str],
        all_dimensions: list[dict[str, str]],
    ) -> AsyncIterator[Tile]:
        for grid_name, tilecoords in grid_tilecoords.items():
            for tilecoord in tilecoords:
                for dimensions in all_dimensions:
                    assert "grid" not in default_metadata, "grid should not be in default_metadata"
                    metadata = {
                        "grid": grid_name,
                    }
                    if default_metadata is not None:
                        metadata.update(default_metadata)
                    for k, v in dimensions.items():
                        metadata["dimension_" + k] = v
                    yield Tile(tilecoord, metadata=metadata)

    def set_tilecoords(
        self,
        config: DatedConfig,
        grid_tilecoords: dict[str, Iterable[TileCoord]],
        layer_name: str,
    ) -> None:
        """Set the tilestream for the given tilecoords."""
        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer %s not found in config %s", layer_name, config.file)
            return
        layer = config.config["layers"][layer_name]

        metadata = {"layer": layer_name, "config_file": str(config.file)}
        if hasattr(self.options, "job_id") and self.options.job_id:
            metadata["job_id"] = self.options.job_id
        if self.options.host is not None:
            metadata["host"] = self.options.host
        self.tilestream = self._tilestream(grid_tilecoords, metadata, self.get_all_dimensions(layer))

    def set_store(self, store: AsyncTileStore) -> None:
        """Set the store for the tilestream."""
        self.tilestream = store.list()

    def counter(self) -> "Count":
        """Count the number of generated tile."""
        count = Count()
        self.imap(count)
        return count

    def counter_size(self) -> "CountSize":
        """Count the number of generated tile and measure the total generated size."""
        count = CountSize()
        self.imap(count)
        return count

    def process(self, name: str | None = None, key: str = "post_process") -> None:
        """Add a process to the tilestream."""
        gene = self

        def get_process(config_file: Path, layer_name: str) -> Process | None:
            config = gene.get_config(config_file)
            if layer_name not in config.config.get("layers", {}):
                _LOGGER.warning("Layer %s not found in config %s", layer_name, config_file)
                return None
            layer = config.config["layers"][layer_name]
            name_ = name
            if name_ is None:
                name_ = layer.get(key)  # type: ignore[assignment]
            if name_ is not None:
                return Process(config.config["process"][name_], self.options)
            return None

        self.imap(MultiAction(get_process))

    def get(self, store: AsyncTileStore, time_message: str | None = None) -> None:
        """Get the tiles from the store."""
        assert store is not None
        self.imap(store.get_one, time_message)

    def put(self, store: AsyncTileStore, time_message: str | None = None) -> None:
        """Put the tiles in the store."""
        assert store is not None

        async def put_internal(tile: Tile) -> Tile:
            await store.put_one(tile)
            return tile

        self.imap(put_internal, time_message)

    def delete(self, store: AsyncTileStore, time_message: str | None = None) -> None:
        """Delete the tiles from the store."""
        assert store is not None

        async def delete_internal(tile: Tile) -> Tile:
            await store.delete_one(tile)
            return tile

        self.imap(delete_internal, time_message)

    def imap(
        self,
        func: Callable[[Tile], Awaitable[Tile | None]],
        time_message: str | None = None,
    ) -> None:
        """Add a function to the tilestream."""
        assert func is not None

        class Func:
            """Function with an additional field used to names it in timing messages."""

            def __init__(
                self,
                func: Callable[[Tile], Awaitable[Tile | None]],
                time_message: str | None,
            ) -> None:
                self.func = func
                self.time_message = time_message

            async def __call__(self, tile: Tile) -> Tile | None:
                return await self.func(tile)

            def __str__(self) -> str:
                return f"Func: {self.func}"

            def __repr__(self) -> str:
                return f"Func: {self.func!r}"

        self.functions.append(Func(func, time_message))

    async def consume(self, test: int | None = None) -> None:
        """Consume the tilestream."""
        assert self.tilestream is not None

        test = self.options.test if test is None else test

        start = datetime.datetime.now(tz=datetime.timezone.utc)

        run = Run(self, self.functions_metatiles, out=self.out)

        if test is None:
            nb_tasks = int(os.environ.get("TILECLOUD_CHAIN_NB_TASKS", "1")) if self.multi_task else 1

            async def target() -> None:
                _LOGGER.debug("Start run")
                end = False
                while not end:
                    try:
                        assert self.tilestream is not None
                        tile = await anext(self.tilestream)

                        host_token = _HOST_CONTEXT.set(tile.metadata.get("host"))
                        layer_token = _LAYER_CONTEXT.set(tile.metadata.get("layer"))
                        meta_tilecoord_token = _META_TILE_COORD_CONTEXT.set(str(tile.tilecoord))

                        try:
                            await run(tile)
                        except TooManyError:
                            _LOGGER.exception("Too many errors")
                            end = True
                        finally:
                            _HOST_CONTEXT.reset(host_token)
                            _LAYER_CONTEXT.reset(layer_token)
                            _META_TILE_COORD_CONTEXT.reset(meta_tilecoord_token)
                    except StopAsyncIteration:
                        if not self.daemon:
                            end = True
                _LOGGER.debug("End run")

            tasks = [asyncio.create_task(target(), name=f"Run {i}") for i in range(nb_tasks)]
            await asyncio.gather(*tasks)

        else:
            for _ in range(test):
                await run(await anext(self.tilestream))

        self.error += run.error
        self.duration = datetime.datetime.now(tz=datetime.timezone.utc) - start
        for ca in self._close_actions:
            ca()


class Count:
    """Count the number of generated tile."""

    def __init__(self) -> None:
        self.nb = 0
        self.lock = asyncio.Lock()

    async def __call__(self, tile: Tile | None = None) -> Tile | None:
        """Count the number of generated tile."""
        async with self.lock:
            self.nb += 1
        return tile

    def __str__(self) -> str:
        return f"Count: {self.nb}"

    def __repr__(self) -> str:
        return f"Count: {self.nb}"


class CountSize:
    """Count the number of generated tile and measure the total generated size."""

    def __init__(self) -> None:
        self.nb = 0
        self.size = 0
        self.lock = asyncio.Lock()

    async def __call__(self, tile: Tile | None = None) -> Tile | None:
        """Count the number of generated tile and measure the total generated size."""
        if tile and tile.data:
            async with self.lock:
                self.nb += 1
                self.size += len(tile.data)
        return tile

    def __str__(self) -> str:
        return f"CountSize: {self.nb} {self.size}"

    def __repr__(self) -> str:
        return f"CountSize: {self.nb} {self.size}"


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
        store: AsyncTileStore | None = None,
        queue_store: AsyncTileStore | None = None,
        count: Count | None = None,
    ) -> None:
        self.size = size
        self.sha1code = sha1code
        self.store = store
        self.queue_store = queue_store
        self.count = count

    async def __call__(self, tile: Tile) -> Tile | None:
        """Drop the tile if the size and hash are the same as the specified ones."""
        assert tile.data
        if len(tile.data) != self.size or sha1(tile.data).hexdigest() != self.sha1code:  # noqa: S324
            return tile
        if self.store is not None:
            if tile.tilecoord.n != 1:
                for tilecoord in tile.tilecoord:
                    await self.store.delete_one(Tile(tilecoord, metadata=tile.metadata))
            else:
                await self.store.delete_one(tile)
        _LOGGER.info("The tile %s %s is dropped", tile.tilecoord, tile.formated_metadata)
        if hasattr(tile, "metatile"):
            metatile: Tile = tile.metatile
            metatile.elapsed_togenerate -= 1  # type: ignore[attr-defined]
            if metatile.elapsed_togenerate == 0 and self.queue_store is not None:  # type: ignore[attr-defined]
                await self.queue_store.delete_one(metatile)
        elif self.queue_store is not None:
            await self.queue_store.delete_one(tile)

        if self.count:
            await self.count()

        return None


@dataclass
class _DatedAction:
    """Dated action."""

    mtime: float
    action: Callable[[Tile], Awaitable[Tile | None]]


class MultiAction:
    """
    Used to perform an action based on the tile's layer name.

    E.g a HashDropper or Process
    """

    def __init__(
        self,
        get_action: Callable[[Path, str], Callable[[Tile], Awaitable[Tile | None]] | None],
    ) -> None:
        self.get_action = get_action
        self.actions: dict[tuple[Path, str], _DatedAction] = {}

    def _get_action(self, config_file: Path, layer: str) -> Callable[[Tile], Awaitable[Tile | None]] | None:
        """Get the action based on the tile's layer name."""
        if not config_file.exists():
            _LOGGER.warning("Config file %s does not exist", config_file)
            return None
        mtime = config_file.stat().st_mtime
        action = self.actions.get((config_file, layer))
        if action is not None and action.mtime != mtime:
            action = None
        if action is None:
            action_item = self.get_action(config_file, layer)
            if action_item is not None:
                action = _DatedAction(mtime, action_item)
                self.actions[(config_file, layer)] = action
        return action.action if action is not None else None

    async def __call__(self, tile: Tile) -> Tile | None:
        """Run the action."""
        layer = tile.metadata["layer"]
        config_file = Path(tile.metadata["config_file"])
        action = self._get_action(config_file, layer)
        if action:
            _LOGGER.debug("[%s] Run action %s.", tile.tilecoord, action)
            return await action(tile)
        return tile

    def __str__(self) -> str:
        """Return a string representation of the object."""
        actions = {str(action.action) for action in self.actions.values()}
        keys = {f"{config_file}:{layer}" for config_file, layer in self.actions}
        return f"{self.__class__.__name__}({', '.join(actions)} - {', '.join(keys)})"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        actions = {repr(action.action) for action in self.actions.values()}
        keys = {f"{config_file}:{layer}" for config_file, layer in self.actions}
        return f"{self.__class__.__name__}({', '.join(actions)} - {', '.join(keys)})"


class HashLogger:
    """Log the tile size and hash."""

    def __init__(self, block: str, out: IO[str] | None) -> None:
        self.block = block
        self.out = out

    async def __call__(self, tile: Tile) -> Tile:
        """Log the tile size and hash."""
        ref = None
        try:
            assert tile.data
            image = Image.open(BytesIO(tile.data))
        except OSError as ex:
            assert tile.data
            _LOGGER.error("%s: %s", str(ex), tile.data)  # noqa: TRY400
            raise
        for px in image.getdata():  # type: ignore[attr-defined]
            if ref is None:
                ref = px
            elif px != ref:
                print("Error: image is not uniform.", file=self.out)
                _LOGGER.debug("Error: image is not uniform.")
                sys.exit(1)

        assert tile.data
        print(
            f"""Tile: {tile.tilecoord} {tile.formated_metadata}
    {self.block}:
        size: {len(tile.data)}
        hash: {sha1(tile.data).hexdigest()}""",  # noqa: S324
            file=self.out,
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
        """Filter the tilecoord."""
        nb = round(tilecoord.z + tilecoord.x / tilecoord.n + tilecoord.y / tilecoord.n)
        return nb % self.nb_process == self.process_nb

    async def __call__(self, tile: Tile) -> Tile | None:
        """Filter the tile."""
        return tile if self.filter(tile.tilecoord) else None


class IntersectGeometryFilter:
    """Drop the tiles (coordinates) it she didn't intersect the configured geom."""

    def __init__(
        self,
        gene: TileGeneration,
    ) -> None:
        self.gene = gene

    def filter_tilecoord(
        self,
        config: DatedConfig,
        tilecoord: TileCoord,
        layer_name: str,
        grid_name: str,
        host: str | None = None,
    ) -> bool:
        """Filter the tilecoord."""
        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer %s not found in config %s", layer_name, config.file)
            return True
        layer = config.config["layers"][layer_name]
        grid = config.config["grids"][grid_name]
        tile_grid = self.gene.get_grid(config, grid_name)
        px_buffer = (
            layer.get("px_buffer", configuration.LAYER_PIXEL_BUFFER_DEFAULT)
            + layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT)
            if layer["meta"]
            else 0
        )
        geoms = self.gene.get_geoms(config, layer_name, grid_name, host=host)
        return self.bbox_polygon(  # type: ignore[no-any-return]
            tile_grid.extent(tilecoord, grid["resolutions"][tilecoord.z] * px_buffer),
        ).intersects(geoms[tilecoord.z])

    async def __call__(self, tile: Tile) -> Tile | None:
        """Filter the tile on a geometry."""
        return (
            tile
            if self.filter_tilecoord(
                self.gene.get_tile_config(tile),
                tile.tilecoord,
                tile.metadata["layer"],
                tile.metadata["grid"],
            )
            else None
        )

    @staticmethod
    def bbox_polygon(bbox: tuple[float, float, float, float]) -> Polygon:
        """Create a polygon from a bbox."""
        return Polygon(
            (
                (bbox[0], bbox[1]),
                (bbox[0], bbox[3]),
                (bbox[2], bbox[3]),
                (bbox[2], bbox[1]),
            ),
        )


class DropEmpty:
    """Create a filter for dropping all tiles with errors."""

    def __init__(self, gene: TileGeneration) -> None:
        self.gene = gene

    async def __call__(self, tile: Tile) -> Tile | None:
        """Filter the enpty tile."""
        config = self.gene.get_tile_config(tile)
        if not tile or not tile.data:
            _LOGGER.error(
                "The tile: %s%s is empty",
                tile.tilecoord if tile else "not defined",
                " " + tile.formated_metadata if tile else "",
            )
            if "error_file" in config.config["generation"] and tile:
                self.gene.log_tiles_error(tile=tile, message="The tile is empty")
            return None
        return tile


def quote(arg: str) -> str:
    """Add some quote and escape to pass the argument to an externa command."""
    if " " in arg or "'" in arg or '"' in arg:
        if "'" in arg:
            if '"' in arg:
                formatted_arg = arg.replace("'", "\\'")
                return f"'{formatted_arg}'"
            return f'"{arg}"'
        return f"'{arg}'"
    if arg == "":
        return "''"
    return arg


def parse_tilecoord(string_representation: str) -> TileCoord:
    """Parce the tile coordinates (z/x/y => TileCoord object)."""
    parts = string_representation.split(":")
    coords = [int(v) for v in parts[0].split("/")]
    if len(coords) != 3:
        message = "Wrong number of coordinates"
        raise ValueError(message)
    z, x, y = coords
    if len(parts) == 1:
        tilecoord = TileCoord(z, x, y)
    elif len(parts) == 2:
        meta = parts[1].split("/")
        if len(meta) != 2:
            message = "No one '/' in meta coordinates"
            raise ValueError(message)
        tilecoord = TileCoord(z, x, y, int(meta[0]))
    else:
        message = "More than on ':' in the tilecoord"
        raise ValueError(message)
    return tilecoord


class Process:
    """Process a tile throw an external command."""

    def __init__(self, config: tilecloud_chain.configuration.ProcessCommand, options: Namespace) -> None:
        self.config = config
        self.options: list[Literal["verbose", "debug", "quiet", "default"]] = []
        if options.verbose:
            self.options.append("verbose")
        if options.debug:
            self.options.append("debug")
        if options.quiet:
            self.options.append("quiet")
        if not self.options:
            self.options.append("default")

    async def __call__(self, tile: Tile) -> Tile | None:
        """Process the tile."""
        if tile and tile.data:
            fd_in, name_in = tempfile.mkstemp()
            async with aiofiles.open(name_in, "wb") as file_in:
                await file_in.write(tile.data)

            for cmd in self.config:
                args = [cmd["arg"][option] for option in self.options if option in cmd["arg"]]

                if cmd.get("need_out", configuration.NEED_OUT_DEFAULT):
                    fd_out, name_out = tempfile.mkstemp()
                    Path(name_out).unlink()
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
                commands = command.split(";")
                for command in commands:
                    command_split = shlex.split(command)
                    if command_split[0] not in _ALLOWED_COMMANDS:
                        _LOGGER.error("Command '%s' not allowed", command_split[0])
                        tile.error = f"Command '{command}' not allowed"
                        tile.data = None
                        return tile
                    _LOGGER.debug("[%s] process: %s", tile.tilecoord, command)
                    result = await asyncio.create_subprocess_exec(  # pylint: disable=subprocess-run-check
                        *command_split,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await result.communicate()
                    if result.returncode != 0:
                        tile.error = (
                            f"Command '{command}' on tile {tile.tilecoord} "
                            f"return error code {result.returncode}:\n{stderr.decode()}\n{stdout.decode()}"
                        )
                        tile.data = None
                        return tile

                if cmd.get("need_out", configuration.NEED_OUT_DEFAULT):
                    os.close(fd_in)
                    Path(name_in).unlink()
                    name_in = name_out
                    fd_in = fd_out

            async with aiofiles.open(name_in, "rb") as file_out:
                tile.data = await file_out.read()
            os.close(fd_in)
            Path(name_in).unlink()

        return tile

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(self.options)} - {self.config})"

    def __repr__(self) -> str:
        return self.__str__()


class TilesFileStore(AsyncTileStore):
    """Load tiles to be generate from a file."""

    def __init__(self, tiles_file: Path) -> None:
        super().__init__()
        self.tiles_file_path = tiles_file

    async def list(self) -> AsyncIterator[Tile]:
        """List the tiles."""
        with self.tiles_file_path.open(encoding="utf-8") as tiles_file:
            while True:
                line = tiles_file.readline()
                if not line:
                    return
                line = line.split("#")[0].strip()
                if line != "":
                    splitted_line = line.split(" ")
                    try:
                        tilecoord = parse_tilecoord(splitted_line[0])
                    except ValueError as e:
                        _LOGGER.exception(
                            "A tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n\n%s",
                            line,
                            repr(e),  # noqa: TRY401
                        )
                        continue

                    yield Tile(
                        tilecoord,
                        metadata=dict([cast("tuple[str, str]", e.split("=")) for e in splitted_line[1:]]),
                    )

    async def get_one(self, tile: Tile) -> Tile | None:
        """Get the tile."""
        raise NotImplementedError

    async def put_one(self, tile: Tile) -> Tile:
        """Put the tile."""
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """Delete the tile."""
        raise NotImplementedError


def _await_message(_: Any) -> bool:
    try:
        # Just sleep, the SQSTileStore will try again after that...
        time.sleep(10)
    except KeyboardInterrupt as e:
        raise StopAsyncIteration from e  # pylint: disable=raise-missing-from
    else:
        return False


async def get_queue_store(config: DatedConfig, daemon: bool) -> TimedTileStoreWrapper:
    """Get the quue tile store."""
    queue_store = config.config.get("queue_store", configuration.QUEUE_STORE_DEFAULT)

    if queue_store == "postgresql":
        # Create a postgreSQL queue
        from tilecloud_chain.store.postgresql import (  # pylint: disable=import-outside-toplevel
            get_postgresql_queue_store,
        )

        return TimedTileStoreWrapper(
            await get_postgresql_queue_store(config),
            store_name="postgresql",
        )
    if queue_store == "redis":
        # Create a Redis queue
        conf = config.config["redis"]
        tilestore_kwargs: dict[str, Any] = {
            "name": os.environ.get(
                "TILECLOUD_CHAIN_REDIS_QUEUE",
                conf.get("queue", configuration.REDIS_QUEUE_DEFAULT),
            ),
            "stop_if_empty": not daemon,
            "timeout": os.environ.get(
                "TILECLOUD_CHAIN_REDIS_TIMEOUT",
                conf.get("timeout", configuration.TIMEOUT_DEFAULT),
            ),
            "pending_timeout": conf.get("pending_timeout", configuration.PENDING_TIMEOUT_DEFAULT),
            "max_retries": conf.get("max_retries", configuration.MAX_RETRIES_DEFAULT),
            "max_errors_age": conf.get("max_errors_age", configuration.MAX_ERRORS_AGE_DEFAULT),
            "max_errors_nb": conf.get("max_errors_nb", configuration.MAX_ERRORS_NUMBER_DEFAULT),
            "connection_kwargs": conf.get("connection_kwargs", {}),
            "sentinel_kwargs": conf.get("sentinel_kwargs"),
        }
        socket_timeout = os.environ.get("TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT", conf.get("socket_timeout"))
        if socket_timeout is not None:
            tilestore_kwargs["connection_kwargs"]["socket_timeout"] = socket_timeout
        db = os.environ.get("TILECLOUD_CHAIN_REDIS_DB", conf.get("db"))
        if db is not None:
            tilestore_kwargs["connection_kwargs"]["db"] = db
        url = os.environ.get("TILECLOUD_CHAIN_REDIS_URL", conf.get("url"))
        if url is not None:
            tilestore_kwargs["url"] = url
        else:
            sentinels: list[tuple[str, str | int]] = []
            if "TILECLOUD_CHAIN_REDIS_SENTINELs" in os.environ:
                sentinels_string = os.environ["TILECLOUD_CHAIN_REDIS_SENTINELS"]
                sentinels_tmp = [s.split(":") for s in sentinels_string.split(",")]
                sentinels = [  # pylint: disable=unnecessary-comprehension
                    (host, port) for host, port in sentinels_tmp
                ]
            elif "sentinels" in conf:
                sentinels = conf["sentinels"]

            tilestore_kwargs["sentinels"] = [(host, int(port)) for host, port in sentinels]
            tilestore_kwargs["service_name"] = os.environ.get(
                "TILECLOUD_CHAIN_REDIS_SERVICE_NAME",
                conf.get("service_name", configuration.SERVICE_NAME_DEFAULT),
            )
        if "pending_count" in conf:
            tilestore_kwargs["pending_count"] = conf["pending_count"]
        if "pending_max_count" in conf:
            tilestore_kwargs["pending_max_count"] = conf["pending_max_count"]
        return TimedTileStoreWrapper(TileStoreWrapper(RedisTileStore(**tilestore_kwargs)), store_name="redis")
    if queue_store == "sqs":
        # Create a SQS queue
        return TimedTileStoreWrapper(
            TileStoreWrapper(
                SQSTileStore(
                    _get_sqs_queue(config),
                    on_empty=_await_message if daemon else _maybe_stop,
                ),
            ),
            store_name="SQS",
        )
    raise NotImplementedError(f"Unknown queue store: {queue_store}")


def _get_sqs_queue(config: DatedConfig) -> "botocore.client.SQS":
    if "sqs" not in config.config:
        sys.exit("The config hasn't any configured queue")
    sqs = boto3.resource("sqs", region_name=config.config["sqs"].get("region", "eu-west-1"))
    return sqs.get_queue_by_name(QueueName=config.config["sqs"]["queue"])
