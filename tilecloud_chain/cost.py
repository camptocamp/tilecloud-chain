from argparse import ArgumentParser, Namespace
from datetime import timedelta
import logging
import sys
from typing import Iterable, Iterator, Tuple

from tilecloud import Tile, TileStore
from tilecloud_chain import Run, TileGeneration, add_comon_options
from tilecloud_chain.format import duration_format

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        parser = ArgumentParser(description="Used to calculate the generation cost", prog=sys.argv[0])
        add_comon_options(parser, tile_pyramid=False, dimensions=True)
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
            multi_thread=False,
        )
        config = gene.get_config(options.config)

        all_size: float = 0
        tile_size: float = 0
        all_tiles = 0
        if options.layer:
            layer = config.config["layers"][options.layer]
            (all_size, all_time, all_price, all_tiles) = _calculate_cost(gene, options.layer, options)
            tile_size = layer["cost"]["tile_size"] / (1024.0 * 1024)
        else:
            all_time = timedelta()
            all_price = 0
            for layer_name in gene.get_config(options.config).config["generation"]["default_layers"]:
                print()
                print(f"===== {layer_name} =====")
                layer = config.config["layers"][layer_name]
                gene.create_log_tiles_error(layer_name)
                (size, time, price, tiles) = _calculate_cost(gene, layer_name, options)
                tile_size += layer["cost"]["tile_size"] / (1024.0 * 1024)
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
        print(
            "S3 Storage: {:0.2f} [$/month]".format(
                all_size * gene.get_main_config().config["cost"]["s3"]["storage"] / (1024.0 * 1024 * 1024)
            )
        )
        print(
            "S3 get: {:0.2f} [$/month]".format(
                gene.get_main_config().config["cost"]["s3"]["get"]
                * config.config["cost"]["request_per_layers"]
                / 10000.0
                + gene.get_main_config().config["cost"]["s3"]["download"]
                * config.config["cost"]["request_per_layers"]
                * tile_size
            )
        )
        #    if 'cloudfront' in gene.config['cost']:
        #        print('CloudFront: %0.2f [$/month]' % ()
        #            gene.config['cost']['cloudfront']['get'] *
        #            gene.config['cost']['request_per_layers'] / 10000.0 +
        #            gene.config['cost']['cloudfront']['download'] *
        #            gene.config['cost']['request_per_layers'] * tile_size)
    except SystemExit:
        raise
    except:  # pylint: disable=bare-except
        logger.exception("Exit with exception")
        sys.exit(1)


def _calculate_cost(
    gene: TileGeneration, layer_name: str, options: Namespace
) -> Tuple[float, timedelta, float, int]:
    nb_metatiles = {}
    nb_tiles = {}
    config = gene.get_config(options.config)
    layer = config.config["layers"][layer_name]

    meta = layer["meta"]
    if options.cost_algo == "area":
        tile_size = config.config["grids"][layer["grid"]]["tile_size"]
        for zoom, resolution in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
            if "min_resolution_seed" in layer and resolution < layer["min_resolution_seed"]:
                continue

            print(f"Calculate zoom {zoom}.")

            px_buffer = layer["px_buffer"] + layer["meta_buffer"] if meta else 0
            m_buffer = px_buffer * resolution
            if meta:
                size = tile_size * layer["meta_size"] * resolution
                meta_buffer = size * 0.7 + m_buffer
                meta_geom = gene.get_geoms(config, layer_name)[zoom].buffer(meta_buffer, 1)
                nb_metatiles[zoom] = int(round(meta_geom.area / size ** 2))
            size = tile_size * resolution
            tile_buffer = size * 0.7 + m_buffer
            geom = gene.get_geoms(config, layer_name)[zoom].buffer(tile_buffer, 1)
            nb_tiles[zoom] = int(round(geom.area / size ** 2))

    elif options.cost_algo == "count":
        gene.init_tilecoords(config, layer_name)
        gene.add_geom_filter()

        if meta:

            def count_metatile(tile: Tile) -> Tile:
                if tile:
                    if tile.tilecoord.z in nb_metatiles:
                        nb_metatiles[tile.tilecoord.z] += 1
                    else:
                        nb_metatiles[tile.tilecoord.z] = 1
                return tile

            gene.imap(count_metatile)

            class MetaTileSplitter(TileStore):
                @staticmethod
                def get(tiles: Iterable[Tile]) -> Iterator[Tile]:
                    for metatile in tiles:
                        for tilecoord in metatile.tilecoord:
                            yield Tile(tilecoord)

            gene.add_metatile_splitter(MetaTileSplitter())

            # Only keep tiles that intersect geometry
            gene.add_geom_filter()

        def count_tile(tile: Tile) -> Tile:
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
        for tile in gene.tilestream:
            tile.metadata["layer"] = layer_name
            run(tile)

    times = {}
    print()
    for z in nb_metatiles:
        print(f"{nb_metatiles[z]} meta tiles in zoom {z}.")
        times[z] = layer["cost"]["metatile_generation_time"] * nb_metatiles[z]

    price: float = 0
    all_size: float = 0
    all_time: float = 0
    all_tiles = 0
    for z in nb_tiles:
        print()
        print(f"{nb_tiles[z]} tiles in zoom {z}.")
        all_tiles += nb_tiles[z]
        if meta:
            time = times[z] + layer["cost"]["tile_generation_time"] * nb_tiles[z]
        else:
            time = layer["cost"]["tileonly_generation_time"] * nb_tiles[z]
        size = layer["cost"]["tile_size"] * nb_tiles[z]
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print(f"Time to generate: {duration_format(td)} [d h:mm:ss]")
        c = gene.get_main_config().config["cost"]["s3"]["put"] * nb_tiles[z] / 1000.0
        price += c
        print(f"S3 PUT: {c:0.2f} [$]")

        if "sqs" in gene.get_main_config().config:
            if meta:
                nb_sqs = nb_metatiles[z] * 3
            else:
                nb_sqs = nb_tiles[z] * 3
            c = nb_sqs * gene.get_main_config().config["cost"]["sqs"]["request"] / 1000000.0
            price += c
            print(f"SQS usage: {c:0.2f} [$]")

    print()
    td = timedelta(milliseconds=all_time)
    print(f"Number of tiles: {all_tiles}")
    print(f"Generation time: {duration_format(td)} [d h:mm:ss]")
    print(f"Generation cost: {price:0.2f} [$]")

    return all_size, td, price, all_tiles
