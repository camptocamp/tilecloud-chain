"""Copy the tiles from a cache to an other."""

import asyncio
import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING, cast

from tilecloud_chain import Count, DropEmpty, HashDropper, TileGeneration, add_common_options
from tilecloud_chain.format import duration_format, size_format

if TYPE_CHECKING:
    import tilecloud_chain.configuration


_logger = logging.getLogger(__name__)


class Copy:
    """Copy the tiles from a cache to an other."""

    count = None

    async def copy(
        self,
        options: Namespace,
        gene: TileGeneration,
        layer_name: str,
        source: str,
        destination: str,
        task_name: str,
    ) -> None:
        """Copy the tiles from a cache to an other."""
        assert gene.config_file
        config = gene.get_config(gene.config_file)
        layer = config.config["layers"][layer_name]
        # disable metatiles
        cast("tilecloud_chain.configuration.LayerWms", layer)["meta"] = False
        count_tiles_dropped = Count()

        gene.create_log_tiles_error(layer_name)
        source_tilestore = gene.get_tilesstore(source)
        dest_tilestore = gene.get_tilesstore(destination)
        gene.init_tilecoords(config, layer_name, options.grid)
        gene.add_geom_filter()
        gene.add_logger()
        gene.get(source_tilestore, "Get the tiles")
        gene.imap(DropEmpty(gene))
        # Discard tiles with certain content
        if "empty_tile_detection" in layer:
            empty_tile = layer["empty_tile_detection"]

            gene.imap(
                HashDropper(
                    empty_tile["size"],
                    empty_tile["hash"],
                    store=dest_tilestore,
                    count=count_tiles_dropped,
                ),
            )

        if options.process:
            gene.process(options.process)

        gene.imap(DropEmpty(gene))
        self.count = gene.counter_size()
        gene.put(dest_tilestore, "Store the tiles")
        await gene.consume()
        if not options.quiet:
            print(
                f"""The tile {task_name} of layer '{layer_name}' is finish
Nb {task_name} tiles: {self.count.nb}
Nb errored tiles: {gene.error}
Nb dropped tiles: {count_tiles_dropped.nb}
Total time: {duration_format(gene.duration)}
Total size: {size_format(self.count.size)}
Time per tile: {(gene.duration / self.count.nb * 1000).seconds if self.count.nb != 0 else 0} ms
Size per tile: {self.count.size / self.count.nb if self.count.nb != 0 else -1} o
""",
            )


def main() -> None:
    """Copy the tiles from a cache to an other."""
    asyncio.run(_async_main())


async def _async_main() -> None:
    """Copy the tiles from a cache to an other."""
    try:
        parser = ArgumentParser(
            description="Used to copy the tiles from a cache to an other",
            prog=sys.argv[0],
        )
        add_common_options(parser, near=False, time=False, dimensions=True, cache=False, grid=True)
        parser.add_argument("--process", dest="process", metavar="NAME", help="The process name to do")
        parser.add_argument("source", metavar="SOURCE", help="The source cache")
        parser.add_argument("dest", metavar="DEST", help="The destination cache")

        options = parser.parse_args()

        gene = TileGeneration(options.config, options)
        assert gene.config_file
        config = gene.get_config(gene.config_file)

        if options.layer:
            copy = Copy()
            await copy.copy(options, gene, options.layer, options.source, options.dest, "copy")
        else:
            layers = (
                config.config["generation"]["default_layers"]
                if "default_layers" in config.config["generation"]
                else config.config["layers"].keys()
            )
            for layer in layers:
                copy = Copy()
                await copy.copy(options, gene, layer, options.source, options.dest, "copy")
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        _logger.exception("Exit with exception")
        if os.environ.get("TESTS", "false").lower() == "true":
            raise
        sys.exit(1)


def process() -> None:
    """Copy the tiles from a cache to an other."""
    asyncio.run(_async_process())


async def _async_process() -> None:
    """Copy the tiles from a cache to an other."""
    try:
        parser = ArgumentParser(
            description="Used to copy the tiles from a cache to an other",
            prog=sys.argv[0],
        )
        add_common_options(parser, near=False, time=False, dimensions=True)
        parser.add_argument("process", metavar="PROCESS", help="The process name to do")

        options = parser.parse_args()

        gene = TileGeneration(options.config, options, multi_task=False)

        copy = Copy()
        if options.layer:
            await copy.copy(options, gene, options.layer, options.cache, options.cache, "process")
        else:
            assert gene.config_file
            config = gene.get_config(gene.config_file)
            layers_name = (
                config.config["generation"]["default_layers"]
                if "default_layers" in config.config.get("generation", {})
                else config.config["layers"].keys()
            )
            for layer in layers_name:
                await copy.copy(options, gene, layer, options.cache, options.cache, "process")
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        _logger.exception("Exit with exception")
        sys.exit(1)
