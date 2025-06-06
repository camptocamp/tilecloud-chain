"""Calculate the cost of the generation."""

import asyncio
import logging
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Iterable, Iterator
from datetime import timedelta

from tilecloud import Tile, TileStore

import tilecloud_chain
from tilecloud_chain import Run, TileGeneration, add_common_options, configuration
from tilecloud_chain.format import duration_format
from tilecloud_chain.store import TileStoreWrapper

_LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Calculate the cost, main function."""
    asyncio.run(_async_main())


async def _async_main() -> None:
    """Calculate the cost, main function."""
    try:
        parser = ArgumentParser(description="Used to calculate the generation cost", prog=sys.argv[0])
        add_common_options(parser, tile_pyramid=False, dimensions=True, grid=True)
        parser.add_argument(
            "--cost-algo",
            "--calculate-cost-algorithm",
            default="area",
            dest="cost_algo",
            choices=("area", "count"),
            help="The algorithm use to calculate the cost default base on the 'area' "
            "of the generation geometry, can also be 'count', to be base on number of tiles to generate.",
        )

        options = parser.parse_args()
        gene = TileGeneration(
            options.config,
            options=options,
            layer_name=options.layer,
            base_config={"cost": {}},
            multi_task=False,
        )
        config = gene.get_config(options.config)

        all_size: float = 0
        tile_size: float = 0
        all_tiles = 0
        if options.layer:
            layer = config.config["layers"][options.layer]
            (all_size, all_time, all_price, all_tiles) = await _calculate_cost(gene, options.layer, options)
            tile_size = layer["cost"].get("tile_size", configuration.TILE_SIZE_DEFAULT) / (1024.0 * 1024)
        else:
            all_time = timedelta()
            all_price = 0
            for layer_name in gene.get_config(options.config).config["generation"]["default_layers"]:
                print()
                print(f"===== {layer_name} =====")
                layer = config.config["layers"][layer_name]
                gene.create_log_tiles_error(layer_name)
                (size, time, price, tiles) = await _calculate_cost(gene, layer_name, options)
                tile_size += layer["cost"].get("tile_size", configuration.TILE_SIZE_DEFAULT) / (1024.0 * 1024)
                all_time += time
                all_price += price
                all_size += size
                all_tiles += tiles

            print()
            print("===== GLOBAL =====")
            print(f"Total number of tiles: {all_tiles}")
            print(f"Total generation time: {duration_format(all_time)} [d h:mm:ss]")
            print(f"Total generation cost: {all_price:0.2f} [$]")
        print()
        s3_cost = (
            all_size
            * gene.get_main_config().config["cost"]["s3"].get("storage", configuration.S3_STORAGE_DEFAULT)
            / (1024.0 * 1024 * 1024)
        )
        print(f"S3 Storage: {s3_cost:0.2f} [$/month]")
        s3_get_cost = (
            gene.get_main_config().config["cost"]["s3"].get("get", configuration.S3_GET_DEFAULT)
            * config.config["cost"].get("request_per_layers", configuration.REQUEST_PER_LAYERS_DEFAULT)
            / 10000.0
            + gene.get_main_config().config["cost"]["s3"].get("download", configuration.S3_DOWNLOAD_DEFAULT)
            * config.config["cost"].get("request_per_layers", configuration.REQUEST_PER_LAYERS_DEFAULT)
            * tile_size
        )
        print(f"S3 get: {s3_get_cost:0.2f} [$/month]")
        #    if 'cloudfront' in gene.config['cost']:
        #        print('CloudFront: %0.2f [$/month]' % ()
        #            gene.config['cost']['cloudfront']['get'] *
        #            gene.config['cost'].get("request_per_layers", configuration.REQUESTS_PER_LAYERS_DEFAULT) / 10000.0 +
        #            gene.config['cost']['cloudfront'].get("download", configuration.CLOUDFRONT_DOWNLOAD_DEFAULT) *
        #            gene.config['cost'].get("request_per_layers", configuration.REQUESTS_PER_LAYERS_DEFAULT) * tile_size)
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        _LOGGER.exception("Exit with exception")
        sys.exit(1)


async def _calculate_cost(
    gene: TileGeneration,
    layer_name: str,
    options: Namespace,
) -> tuple[float, timedelta, float, int]:
    nb_metatiles = {}
    nb_tiles = {}
    config = gene.get_config(options.config)
    layer = config.config["layers"][layer_name]

    meta = layer["meta"]
    if options.cost_algo == "area":
        grid = tilecloud_chain.get_grid_config(config, layer_name, options.grid)
        tile_size = grid.get("tile_size", configuration.TILE_SIZE_DEFAULT)
        for zoom, resolution in enumerate(grid["resolutions"]):
            if "min_resolution_seed" in layer and resolution < layer["min_resolution_seed"]:
                continue

            print(f"Calculate zoom {zoom}.")

            px_buffer = (
                layer.get("px_buffer", configuration.LAYER_PIXEL_BUFFER_DEFAULT)
                + layer.get("meta_buffer", configuration.LAYER_META_BUFFER_DEFAULT)
                if meta
                else 0
            )
            m_buffer = px_buffer * resolution
            if meta:
                size = tile_size * layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT) * resolution
                meta_buffer = size * 0.7 + m_buffer
                meta_geom = gene.get_geoms(config, layer_name, options.grid)[zoom].buffer(meta_buffer, 1)
                nb_metatiles[zoom] = round(meta_geom.area / size**2)
            size = tile_size * resolution
            tile_buffer = size * 0.7 + m_buffer
            geom = gene.get_geoms(config, layer_name, options.grid)[zoom].buffer(tile_buffer, 1)
            nb_tiles[zoom] = round(geom.area / size**2)

    elif options.cost_algo == "count":
        gene.init_tilecoords(config, layer_name, options.grid)
        gene.add_geom_filter()

        if meta:

            async def count_metatile(tile: Tile) -> Tile:
                if tile:
                    if tile.tilecoord.z in nb_metatiles:
                        nb_metatiles[tile.tilecoord.z] += 1
                    else:
                        nb_metatiles[tile.tilecoord.z] = 1
                return tile

            gene.imap(count_metatile)

            class MetaTileSplitter(TileStore):
                """Convert the metatile flow to tile flow."""

                def get(self, tiles: Iterable[Tile | None]) -> Iterator[Tile]:
                    assert tiles is not None
                    for metatile in tiles:
                        assert metatile is not None
                        for tilecoord in metatile.tilecoord:
                            yield Tile(tilecoord, metadata=metatile.metadata)

                def put_one(self, tile: Tile) -> Tile:
                    raise NotImplementedError

                def get_one(self, tile: Tile) -> Tile | None:
                    raise NotImplementedError

                def delete_one(self, tile: Tile) -> Tile:
                    raise NotImplementedError

            await gene.add_metatile_splitter(TileStoreWrapper(MetaTileSplitter()))

            # Only keep tiles that intersect geometry
            gene.add_geom_filter()

        async def count_tile(tile: Tile) -> Tile:
            if tile:
                if tile.tilecoord.z in nb_tiles:
                    nb_tiles[tile.tilecoord.z] += 1
                else:
                    print(f"Calculate zoom {tile.tilecoord.z}.")
                    nb_tiles[tile.tilecoord.z] = 1
            return tile

        gene.imap(count_tile)

        run = Run(gene, gene.functions_metatiles)
        assert gene.tilestream
        async for tile in gene.tilestream:
            tile.metadata["layer"] = layer_name
            await run(tile)

    times = {}
    print()
    for z, nb_metatile in nb_metatiles.items():
        print(f"{nb_metatile} meta tiles in zoom {z}.")
        times[z] = layer["cost"]["metatile_generation_time"] * nb_metatile

    price: float = 0
    all_size: float = 0
    all_time: float = 0
    all_tiles = 0
    for z, nb_tile in nb_tiles.items():
        print()
        print(f"{nb_tile} tiles in zoom {z}.")
        all_tiles += nb_tile
        if meta:
            time = (
                times[z]
                + layer["cost"].get("tile_generation_time", configuration.TILE_GENERATION_TIME_DEFAULT)
                * nb_tile
            )
        else:
            time = (
                layer["cost"].get("tileonly_generation_time", configuration.TILE_ONLY_GENERATION_TIME_DEFAULT)
                * nb_tile
            )
        size = layer["cost"].get("tile_size", configuration.TILE_SIZE_DEFAULT) * nb_tile
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print(f"Time to generate: {duration_format(td)} [d h:mm:ss]")
        c = (
            gene.get_main_config().config["cost"]["s3"].get("put", configuration.S3_PUT_DEFAULT)
            * nb_tile
            / 1000.0
        )
        price += c
        print(f"S3 PUT: {c:0.2f} [$]")

        if "sqs" in gene.get_main_config().config:
            nb_sqs = nb_metatiles[z] * 3 if meta else nb_tile * 3
            c = (
                nb_sqs
                * gene.get_main_config().config["cost"]["sqs"].get("request", configuration.REQUEST_DEFAULT)
                / 1000000.0
            )
            price += c
            print(f"SQS usage: {c:0.2f} [$]")

    print()
    td = timedelta(milliseconds=all_time)
    print(f"Number of tiles: {all_tiles}")
    print(f"Generation time: {duration_format(td)} [d h:mm:ss]")
    print(f"Generation cost: {price:0.2f} [$]")

    return all_size, td, price, all_tiles
