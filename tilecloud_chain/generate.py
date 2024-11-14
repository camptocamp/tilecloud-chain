"""Generate the tiles, generate the queue, ..."""

import logging
import os
import random
import socket
import sys
import threading
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from datetime import datetime
from getpass import getuser
from typing import IO, cast

import boto3
import prometheus_client
import tilecloud.filter.error
from tilecloud import Tile, TileCoord, TileStore
from tilecloud.filter.logger import Logger
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.store.url import URLTileStore

import tilecloud_chain
from tilecloud_chain import (
    Count,
    CountSize,
    HashDropper,
    HashLogger,
    LocalProcessFilter,
    MultiAction,
    TileGeneration,
    TilesFileStore,
    add_common_options,
    configuration,
    get_queue_store,
    parse_tilecoord,
    quote,
)
from tilecloud_chain.database_logger import DatabaseLogger, DatabaseLoggerInit
from tilecloud_chain.format import default_int, duration_format, size_format
from tilecloud_chain.multitilestore import MultiTileStore
from tilecloud_chain.timedtilestore import TimedTileStoreWrapper

_LOGGER = logging.getLogger(__name__)


class LogTilesContext:
    """Logging tile context."""

    def __init__(self, gene: TileGeneration):
        self.gene = gene

    def __call__(self, tile: Tile) -> Tile:
        """Add logs tile context."""
        tilecloud_chain.LOGGING_CONTEXT.setdefault(os.getpid(), {})[threading.current_thread().native_id] = {  # type: ignore
            "host": tile.metadata.get("host"),
            "layer": tile.metadata.get("layer"),
            "meta_tilecoord": str(tile.tilecoord),
        }

        return tile


class Generate:
    """Generate the tiles, generate the queue, ..."""

    def __init__(
        self, options: Namespace, gene: TileGeneration, out: IO[str] | None, server: bool = False
    ) -> None:
        self._count_metatiles: Count | None = None
        self._count_metatiles_dropped: Count | None = None
        self._count_tiles: Count | None = None
        self._count_tiles_dropped: Count | None = None
        self._count_tiles_stored: CountSize | None = None
        self._queue_tilestore: TileStore | None = None
        self._cache_tilestore: TileStore | None = None
        self._options = options
        self._gene = gene
        self.out = out

        if getattr(self._options, "get_hash", None) is not None:
            self._options.role = "hash"
            self._options.test = 1

        if getattr(self._options, "tiles", None) is not None:
            self._options.role = "slave"

        self._generate_init()
        if self._options.role != "master" and not server:
            self._generate_tiles()

    def gene(self, layer_name: str | None = None) -> None:
        """Generate the tiles."""
        if self._count_tiles is not None:
            self._count_tiles.nb = 0
        if self._count_tiles_dropped is not None:
            self._count_tiles_dropped.nb = 0
        if self._count_tiles_stored is not None:
            self._count_tiles_stored.nb = 0
            self._count_tiles_stored.size = 0
        if self._count_metatiles is not None:
            self._count_metatiles.nb = 0
        if self._count_metatiles_dropped is not None:
            self._count_metatiles_dropped.nb = 0
        self._gene.error = 0

        if self._options.role != "slave" and not self._options.get_hash and not self._options.get_bbox:
            assert layer_name
            self._gene.create_log_tiles_error(layer_name)

        if self._options.role != "slave" or self._options.tiles:
            self._generate_queue(layer_name)

        self.generate_consume()
        self.generate_resume(layer_name)

    def _generate_init(self) -> None:
        if self._options.role != "server":
            self._count_metatiles_dropped = Count()
            self._count_tiles = Count()
            self._count_tiles_dropped = Count()

        if self._options.role in ("master", "slave") and not self._options.tiles:
            self._queue_tilestore = get_queue_store(self._gene.get_main_config(), self._options.daemon)

        if self._options.role in ("local", "master"):
            self._gene.add_geom_filter()

        if self._options.role in ("local", "master") and "logging" in self._gene.get_main_config().config:
            self._gene.imap(
                DatabaseLoggerInit(
                    self._gene.get_main_config().config["logging"],
                    self._options is not None and self._options.daemon,
                )
            )

        if self._options.local_process_number is not None:
            self.add_local_process_filter()

        # At this stage, the tilestream contains metatiles that intersect geometry
        self._gene.add_logger()

        if self._options.role == "master":
            assert self._queue_tilestore is not None
            # Put the metatiles into the SQS or Redis queue
            self._gene.put(self._queue_tilestore)
            self._count_tiles = self._gene.counter()

        if self._options.role in ("local", "slave"):
            self._cache_tilestore = self._gene.get_tilesstore(self._options.cache)
            assert self._cache_tilestore is not None

    def add_local_process_filter(self) -> None:
        """Add the local process filter to the gene."""
        self._gene.imap(
            LocalProcessFilter(
                self._gene.get_main_config()
                .config["generation"]
                .get("number_process", configuration.NUMBER_PROCESS_DEFAULT),
                self._options.local_process_number,
            )
        )

    def _generate_queue(self, layer_name: str | None) -> None:
        if self._options.tiles:
            self._gene.set_store(TilesFileStore(self._options.tiles))
            return

        assert layer_name is not None
        assert self._gene.config_file is not None
        config = self._gene.get_config(self._gene.config_file)
        layer = config.config["layers"][layer_name]

        if self._options.get_bbox:
            try:
                tilecoord = parse_tilecoord(self._options.get_bbox)
                bounds = default_int(self._gene.get_grid(config, layer["grid"]).extent(tilecoord))
                print(f"Tile bounds: [{','.join([str(b) for b in bounds])}]", file=self.out)
                sys.exit()
            except ValueError:
                _LOGGER.exception(
                    "Tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n",
                    self._options.get_bbox,
                )
                sys.exit(1)

        if self._options.role in ("local", "master"):
            # Generate a stream of metatiles
            self._gene.init_tilecoords(config, layer_name)

        elif self._options.role == "hash":
            layer = config.config["layers"][layer_name]
            try:
                z, x, y = (int(v) for v in self._options.get_hash.split("/"))
                if layer.get("meta"):
                    self._gene.set_tilecoords(
                        config,
                        [TileCoord(z, x, y, layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT))],
                        layer_name,
                    )
                else:
                    self._gene.set_tilecoords(config, [TileCoord(z, x, y)], layer_name)
            except ValueError:
                _LOGGER.exception("Tile '%s' is not in the format 'z/x/y'", self._options.get_hash)
                sys.exit(1)

    def _generate_tiles(self) -> None:
        if self._options.role in ("slave") and not self._options.tiles:
            assert self._queue_tilestore is not None
            # Get the metatiles from the SQS/Redis queue
            self._gene.set_store(self._queue_tilestore)
            self._gene.imap(lambda tile: tile if "layer" in tile.metadata else None)
            self._gene.imap(LogTilesContext(self._gene))

        if self._options.role != "server":
            self._count_metatiles = self._gene.counter()

        self._gene.get(MultiTileStore(TilestoreGetter(self)), "Get tile")

        if self._options.role in ("local", "slave") and "logging" in self._gene.get_main_config().config:
            self._gene.imap(
                DatabaseLogger(
                    self._gene.get_main_config().config["logging"],
                    self._options is not None and self._options.daemon,
                )
            )
            self._gene.init(
                (
                    self._queue_tilestore
                    if "error_file" in self._gene.get_main_config().config["generation"]
                    else None
                ),
                self._options.daemon,
            )
        else:
            self._gene.init(self._queue_tilestore, daemon=self._options.daemon)

        if self._options.role == "hash":
            self._gene.imap(HashLogger("empty_metatile_detection", self.out))
        elif not self._options.near:
            assert self._count_metatiles_dropped is not None
            self._gene.imap(MultiAction(HashDropperGetter(self, True, self._count_metatiles_dropped)))

        def add_elapsed_togenerate(metatile: Tile) -> Tile | None:
            if metatile is not None:
                metatile.elapsed_togenerate = metatile.tilecoord.n**2  # type: ignore
                return metatile
            return None

        self._gene.imap(add_elapsed_togenerate)

        # Split the metatile image into individual tiles
        self._gene.add_metatile_splitter()
        self._gene.imap(Logger(_LOGGER, logging.INFO, "%(tilecoord)s, %(formated_metadata)s"))

        if self._count_tiles is not None:
            self._gene.imap(self._count_tiles)

        self._gene.process(key="pre_hash_post_process")

        if self._options.role == "hash":
            self._gene.imap(HashLogger("empty_tile_detection", self.out))
        elif not self._options.near:
            assert self._count_tiles_dropped is not None
            self._gene.imap(MultiAction(HashDropperGetter(self, False, self._count_tiles_dropped)))

        if self._options.role != "server":
            self._gene.process()

        if self._options.role in ("local", "slave"):
            self._count_tiles_stored = self._gene.counter_size()

            if self._options.time:

                def log_size(tile: Tile) -> Tile:
                    assert tile.data is not None
                    sys.stdout.write(f"size: {len(tile.data)}\n")
                    return tile

                self._gene.imap(log_size)

            assert self._cache_tilestore is not None
            self._gene.put(self._cache_tilestore, "Store the tile")

        if self._options.role == "slave" and not self._options.tiles:

            def delete_from_store(tile: Tile) -> Tile:
                assert self._queue_tilestore is not None
                if hasattr(tile, "metatile"):
                    metatile: Tile = tile.metatile
                    metatile.elapsed_togenerate -= 1  # type: ignore
                    if metatile.elapsed_togenerate == 0:  # type: ignore
                        self._queue_tilestore.delete_one(metatile)
                else:
                    self._queue_tilestore.delete_one(tile)
                return tile

            self._gene.imap(delete_from_store)

        if self._options.role in ("local", "slave") and "logging" in self._gene.get_main_config().config:
            self._gene.imap(
                DatabaseLogger(
                    self._gene.get_main_config().config["logging"],
                    self._options is not None and self._options.daemon,
                )
            )
        self._gene.init(self._queue_tilestore, daemon=self._options.daemon)

    def generate_consume(self) -> None:
        """Consume the tiles and log the time if needed."""
        if self._options.time is not None:
            options = self._options

            class LogTime:
                """Log the generation time."""

                n = 0
                t1 = None

                def __call__(self, tile: Tile) -> Tile:
                    self.n += 1
                    assert options.time
                    if self.n == options.time:
                        self.t1 = datetime.now()
                    elif self.n == 2 * options.time:
                        t2 = datetime.now()
                        assert self.t1
                        duration = (t2 - self.t1) / options.time
                        time = (
                            duration.days * 24 * 3600 + duration.seconds
                        ) * 1000000 + duration.microseconds
                        sys.stdout.write(f"time: {time}\n")
                    return tile

            self._gene.imap(LogTime())

            self._gene.consume(self._options.time * 3)
        else:
            self._gene.consume()

    def generate_resume(self, layer_name: str | None) -> None:
        """Generate the resume message and close the tilestore connection."""
        config = self._gene.get_config(self._gene.config_file) if self._gene.config_file is not None else None
        if self._options.time is None:
            layer = None
            if layer_name is not None:
                assert config is not None
                layer = config.config["layers"][layer_name]
                all_dimensions = self._gene.get_all_dimensions(layer)
                formatted_dimensions = " - ".join(
                    [", ".join(["=".join(d) for d in dimensions.items()]) for dimensions in all_dimensions]
                )
                suffix = (
                    ""
                    if ((len(all_dimensions) == 1 and len(all_dimensions[0]) == 0) or layer["type"] != "wms")
                    else f" ({formatted_dimensions})"
                )
                message = [f"The tile generation of layer '{layer_name}{suffix}' is finish"]
            else:
                message = ["The tile generation is finish"]
            if self._options.role == "master":
                assert self._count_tiles
                message.append(f"Nb of generated jobs: {self._count_tiles.nb}")
            elif layer.get("meta") if layer is not None else self._options.role == "slave":
                assert self._count_metatiles is not None
                assert self._count_metatiles_dropped is not None
                message += [
                    f"Nb generated metatiles: {self._count_metatiles.nb}",
                    f"Nb metatiles dropped: {self._count_metatiles_dropped.nb}",
                ]

            if self._options.role != "master":
                assert self._count_tiles is not None
                assert self._count_tiles_dropped is not None
                message += [
                    f"Nb generated tiles: {self._count_tiles.nb}",
                    f"Nb tiles dropped: {self._count_tiles_dropped.nb}",
                ]
                if self._options.role in ("local", "slave"):
                    assert self._count_tiles_stored is not None
                    assert self._count_tiles is not None
                    message += [
                        f"Nb tiles stored: {self._count_tiles_stored.nb}",
                        f"Nb tiles in error: {self._gene.error}",
                        f"Total time: {duration_format(self._gene.duration)}",
                    ]
                    if self._count_tiles_stored.nb != 0:
                        message.append(f"Total size: {size_format(self._count_tiles_stored.size)}")
                    if self._count_tiles.nb != 0:
                        message.append(
                            "Time per tile: "
                            f"{(self._gene.duration / self._count_tiles.nb * 1000).seconds:0.0f} ms"
                        )
                    if self._count_tiles_stored.nb != 0:
                        message.append(
                            "Size per tile: "
                            f"{self._count_tiles_stored.size / self._count_tiles_stored.nb:0.0f} o"
                        )

            if not self._options.quiet and self._options.role in ("local", "slave", "master") and message:
                print("\n".join(message) + "\n", file=self.out)

        if self._cache_tilestore is not None and hasattr(self._cache_tilestore, "connection"):
            self._cache_tilestore.connection.close()

        if (
            self._options.role != "hash"
            and self._options.time is None
            and config is not None
            and "sns" in config.config
        ):
            if "region" in config.config["sns"]:
                sns_client = boto3.client("sns", region_name=config.config["sns"].get("region", "eu-west-1"))
            else:
                sns_client = boto3.client("sns")
            sns_message = [message[0]]
            sns_message += [
                f"Layer: {layer_name if layer_name is not None else '(All layers)'}",
                f"Role: {self._options.role}",
                f"Host: {socket.getfqdn()}",
                f"Command: {' '.join([quote(arg) for arg in sys.argv])}",
            ]
            sns_message += message[1:]
            sns_client.publish(
                TopicArn=config.config["sns"]["topic"],
                Message="\n".join(sns_message),
                Subject=f"Tile generation ({layer_name if layer_name is not None else 'All layers'} - "
                f"{self._options.role})",
            )


class TilestoreGetter:
    """Used to get the correct tilestore based on the layername config file any layer type."""

    def __init__(self, gene: Generate):
        self.gene = gene

    def __call__(self, config_file: str, layer_name: str) -> TileStore | None:
        """Get the tilestore based on the layername config file any layer type."""
        config = self.gene._gene.get_config(config_file)
        layer = config.config["layers"][layer_name]
        if layer["type"] == "wms":
            params = layer.get("params", {}).copy()
            if "STYLES" not in params:
                params["STYLES"] = ",".join(layer["wmts_style"] for _ in layer["layers"].split(","))
            if layer.get("generate_salt", False):
                params["SALT"] = str(random.randint(0, 999999))  # nosec # noqa: S311

            # Get the metatile image from the WMS server
            return TimedTileStoreWrapper(
                URLTileStore(
                    tilelayouts=(
                        WMSTileLayout(
                            url=layer["url"],
                            layers=layer["layers"],
                            srs=config.config["grids"][layer["grid"]].get("srs", configuration.SRS_DEFAULT),
                            format_pattern=layer["mime_type"],
                            border=(
                                layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT)
                                if layer["meta"]
                                else 0
                            ),
                            tilegrid=self.gene._gene.get_grid(config, layer["grid"]),
                            params=params,
                        ),
                    ),
                    headers=layer["headers"],
                ),
                "wms",
            )
        elif layer["type"] == "mapnik":
            try:
                from tilecloud.store.mapnik_ import MapnikTileStore  # pylint: disable=import-outside-toplevel

                from tilecloud_chain.mapnik_ import (  # pylint: disable=import-outside-toplevel
                    MapnikDropActionTileStore,
                )
            except ImportError:
                if os.environ.get("CI", "FALSE") == "FALSE":  # pragma nocover
                    _LOGGER.error("Mapnik is not available", exc_info=True)
                return None

            grid = config.config["grids"][layer["grid"]]
            if cast(str, layer.get("output_format", "png")) == "grid":
                assert self.gene._count_tiles
                assert self.gene._count_tiles_dropped
                return TimedTileStoreWrapper(
                    MapnikDropActionTileStore(
                        tilegrid=self.gene._gene.get_grid(config, layer["grid"]),
                        mapfile=layer["mapfile"],
                        image_buffer=(
                            layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT)
                            if layer.get("meta")
                            else 0
                        ),
                        data_buffer=layer.get("data_buffer", 128),
                        output_format=layer.get("output_format", "png"),
                        resolution=layer.get("resolution", 4),
                        layers_fields=layer.get("layers_fields", {}),
                        drop_empty_utfgrid=layer.get("drop_empty_utfgrid", False),
                        store=self.gene._cache_tilestore,
                        queue_store=self.gene._queue_tilestore,
                        count=[self.gene._count_tiles, self.gene._count_tiles_dropped],
                        proj4_literal=grid["proj4_literal"],
                    ),
                    "mapnik-drop",
                )
            else:
                return TimedTileStoreWrapper(
                    MapnikTileStore(
                        tilegrid=self.gene._gene.get_grid(config, layer["grid"]),
                        mapfile=layer["mapfile"],
                        image_buffer=(
                            layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT)
                            if layer.get("meta")
                            else 0
                        ),
                        data_buffer=layer.get("data_buffer", 128),
                        output_format=cast(str, layer.get("output_format", "png")),
                        proj4_literal=grid["proj4_literal"],
                    ),
                    "mapnik",
                )
        return None


def detach() -> None:
    """Detach to the parent process."""
    try:
        pid = os.fork()
        if pid > 0:
            print(f"Detached with pid {pid}.")
            sys.stderr.write(str(pid))
            # exit parent
            sys.exit(0)
    except OSError as e:
        _LOGGER.exception("fork #1 failed: %d (%s)", e.errno, e.strerror)
        sys.exit(1)


def main(args: list[str] | None = None, out: IO[str] | None = None) -> None:
    """Run the tiles generation."""
    try:
        parser = ArgumentParser(
            description="Used to generate the tiles", prog=args[0] if args else sys.argv[0]
        )
        add_common_options(parser, dimensions=True)
        parser.add_argument(
            "--get-hash", metavar="TILE", help="get the empty tiles hash, use the specified TILE z/x/y"
        )
        parser.add_argument(
            "--get-bbox",
            metavar="TILE",
            help="get the bbox of a tile, use the specified TILE z/x/y, or z/x/y:+n/+n for metatiles",
        )
        parser.add_argument(
            "--role",
            default="local",
            choices=("local", "master", "slave"),
            help="local/master/slave, master to file the queue and slave to generate the tiles",
        )
        parser.add_argument(
            "--local-process-number", default=None, help="The number of process that we run in parallel"
        )
        parser.add_argument(
            "--detach", default=False, action="store_true", help="run detached from the terminal"
        )
        parser.add_argument(
            "--daemon", default=False, action="store_true", help="run continuously as a daemon"
        )
        parser.add_argument(
            "--tiles",
            metavar="FILE",
            help="Generate the tiles from a tiles file, use the format z/x/y, or z/x/y:+n/+n for metatiles",
        )
        parser.add_argument(
            "--job-id",
            help="The job id in case of Postgres queue",
            type=int,
        )

        options = parser.parse_args(args[1:] if args else sys.argv[1:])

        if options.detach:
            detach()

        if options.daemon and "C2C_PROMETHEUS_PORT" in os.environ:
            prometheus_client.start_http_server(int(os.environ["C2C_PROMETHEUS_PORT"]))

        gene = TileGeneration(
            config_file=options.config or os.environ.get("TILEGENERATION_CONFIGFILE"),
            options=options,
            multi_thread=options.get_hash is None,
        )

        if (
            options.get_hash is None
            and options.get_bbox is None
            and options.config is not None
            and "authorised_user" in gene.get_main_config().config.get("generation", {})
            and gene.get_main_config().config["generation"]["authorised_user"] != getuser()
            and os.environ.get("TILECLOUD_CHAIN_SLAVE", "false").lower() != "true"
        ):
            _LOGGER.error(
                "not authorized, authorized user is: %s.",
                gene.get_main_config().config["generation"]["authorised_user"],
            )
            sys.exit(1)

        if options.config:
            config = gene.get_config(options.config)

            if options.cache is None and options.config:
                options.cache = config.config["generation"].get(
                    "default_cache", configuration.DEFAULT_CACHE_DEFAULT
                )

        if options.tiles is not None and options.role not in ["local", "master"]:
            _LOGGER.error("The --tiles option work only with role local or master")
            sys.exit(1)

        try:
            generate = Generate(options, gene, out)
            if options.role == "slave":
                generate.gene()
            elif options.layer:
                generate.gene(options.layer)
            elif options.get_bbox:
                _LOGGER.error("With --get-bbox option you need to specify a layer")
                sys.exit(1)
            elif options.get_hash:
                _LOGGER.error("With --get-hash option you need to specify a layer")
                sys.exit(1)
            else:
                if options.config:
                    for layer in config.config["generation"].get(
                        "default_layers", config.config["layers"].keys()
                    ):
                        generate.gene(layer)
        except tilecloud.filter.error.TooManyErrors:
            _LOGGER.exception("Too many errors")
            sys.exit(1)
        finally:
            gene.close()
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except # noqa: E722
        _LOGGER.exception("Exit with exception")
        if os.environ.get("TESTS", "false").lower() == "true":
            raise
        sys.exit(1)

    if gene.error != 0:
        sys.exit(1)


class HashDropperGetter:
    """Drop th tiles based on the hash and the size."""

    def __init__(self, gene: Generate, meta: bool, count: Count):
        self.gene = gene
        self.meta = meta
        self.count = count

    def __call__(self, config_file: str, layer_name: str) -> Callable[[Tile], Tile | None]:
        """Call."""
        layer = self.gene._gene.get_config(config_file).config["layers"][layer_name]
        conf_name = "empty_metatile_detection" if self.meta else "empty_tile_detection"
        if conf_name in layer:
            empty_tile = layer["empty_metatile_detection"] if self.meta else layer["empty_tile_detection"]
            return HashDropper(
                empty_tile["size"],
                empty_tile["hash"],
                store=self.gene._gene.get_tilesstore(self.gene._options.cache),
                queue_store=self.gene._gene.queue_store,
                count=self.count,
            )
        return lambda tile: tile


if __name__ == "__main__":
    main()
