# -*- coding: utf-8 -*-

import sys
import logging
from datetime import timedelta
from argparse import ArgumentParser

from tilecloud import Tile, TileStore, consume

from tilecloud_chain import TileGeneration, add_comon_options
from tilecloud_chain.format import duration_format


logger = logging.getLogger(__name__)


def main():
    parser = ArgumentParser(
        description='Used to calculate the generation cost',
        prog=sys.argv[0]
    )
    add_comon_options(parser, tile_pyramid=False, dimensions=True)
    parser.add_argument(
        '--cost-algo', '--calculate-cost-algorithm', default='area', dest='cost_algo',
        choices=('area', 'count'),
        help="The algorithm use to calculate the cost default base on the 'area' "
        "of the generation geometry, can also be 'count', to be base on number of tiles to generate."
    )

    options = parser.parse_args()
    gene = TileGeneration(
        options.config, options,
        layer_name=options.layer, base_config={'cost': {}}
    )

    all_size = 0
    tile_size = 0
    all_tiles = 0
    if options.layer:
        layer = gene.layers[options.layer]
        (all_size, all_time, all_price, all_tiles) = _calculate_cost(
            gene, layer, options
        )
        tile_size = layer['cost']['tile_size'] / (1024.0 * 1024)
    else:
        all_time = timedelta()
        all_price = 0
        for layer_name in gene.config['generation']['default_layers']:
            print("")
            print("===== {} =====".format(layer_name))
            layer = gene.layers[layer_name]
            gene.init_layer(layer, options)
            (size, time, price, tiles) = _calculate_cost(gene, layer, options)
            tile_size += layer['cost']['tile_size'] / (1024.0 * 1024)
            all_time += time
            all_price += price
            all_size += size
            all_tiles += tiles

        print("")
        print("===== GLOBAL =====")
        print("Total number of tiles: {}".format(all_tiles))
        print('Total generation time: {} [d h:mm:ss]'.format((duration_format(all_time))))
        print('Total generation cost: {0:0.2f} [$]'.format(all_price))
    print("")
    print('S3 Storage: {0:0.2f} [$/month]'.format(
        all_size * gene.config['cost']['s3']['storage'] / (1024.0 * 1024 * 1024)
    ))
    print('S3 get: {0:0.2f} [$/month]'.format((
        gene.config['cost']['s3']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
        gene.config['cost']['s3']['download'] * gene.config['cost']['request_per_layers'] * tile_size))
    )
#    if 'cloudfront' in gene.config['cost']:
#        print('CloudFront: %0.2f [$/month]' % ()
#            gene.config['cost']['cloudfront']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
#            gene.config['cost']['cloudfront']['download'] *
#            gene.config['cost']['request_per_layers'] * tile_size)
    sys.exit(0)


def _calculate_cost(gene, layer, options):
    nb_metatiles = {}
    nb_tiles = {}

    meta = layer['meta']
    if options.cost_algo == 'area':
        tile_size = layer['grid_ref']['tile_size']
        for zoom, resolution in enumerate(layer['grid_ref']['resolutions']):
            if 'min_resolution_seed' in layer and resolution < layer['min_resolution_seed']:
                continue

            print("Calculate zoom {}.".format(zoom))

            px_buffer = layer['px_buffer'] + \
                layer['meta_buffer'] if meta else 0
            m_buffer = px_buffer * resolution
            if meta:
                size = tile_size * layer['meta_size'] * resolution
                meta_buffer = size * 0.7 + m_buffer
                meta_geom = gene.geoms[zoom].buffer(meta_buffer, 1)
                nb_metatiles[zoom] = int(round(meta_geom.area / size ** 2))
            size = tile_size * resolution
            tile_buffer = size * 0.7 + m_buffer
            geom = gene.geoms[zoom].buffer(tile_buffer, 1)
            nb_tiles[zoom] = int(round(geom.area / size ** 2))

    elif options.cost_algo == 'count':
        gene.init_tilecoords(layer)
        gene.add_geom_filter(layer)

        if meta:
            def count_metatile(tile):
                if tile:
                    if tile.tilecoord.z in nb_metatiles:
                        nb_metatiles[tile.tilecoord.z] += 1
                    else:
                        nb_metatiles[tile.tilecoord.z] = 1
                return tile
            gene.imap(count_metatile)

            class MetaTileSplitter(TileStore):
                @staticmethod
                def get(tiles):
                    for metatile in tiles:
                        for tilecoord in metatile.tilecoord:
                            yield Tile(tilecoord)
            gene.tilestream = MetaTileSplitter().get(gene.tilestream)

            # Only keep tiles that intersect geometry
            gene.add_geom_filter(layer)

        def count_tile(tile):
            if tile:
                if tile.tilecoord.z in nb_tiles:
                    nb_tiles[tile.tilecoord.z] += 1
                else:
                    print("Calculate zoom {}.".format(tile.tilecoord.z))
                    nb_tiles[tile.tilecoord.z] = 1
            return tile
        gene.imap(count_tile)

        consume(gene.tilestream, None)

    times = {}
    print('')
    for z in nb_metatiles:
        print("{} meta tiles in zoom {}.".format(nb_metatiles[z], z))
        times[z] = layer['cost']['metatile_generation_time'] * nb_metatiles[z]

    price = 0
    all_size = 0
    all_time = 0
    all_tiles = 0
    for z in nb_tiles:
        print('')
        print("{} tiles in zoom {}.".format(nb_tiles[z], z))
        all_tiles += nb_tiles[z]
        if meta:
            time = times[z] + layer['cost']['tile_generation_time'] * nb_tiles[z]
        else:
            time = layer['cost']['tileonly_generation_time'] * nb_tiles[z]
        size = layer['cost']['tile_size'] * nb_tiles[z]
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print("Time to generate: {} [d h:mm:ss]".format((duration_format(td))))
        c = gene.config['cost']['s3']['put'] * nb_tiles[z] / 1000.0
        price += c
        print('S3 PUT: {0:0.2f} [$]'.format(c))

        if 'sqs' in gene.config:
            if meta:
                nb_sqs = nb_metatiles[z] * 3
            else:
                nb_sqs = nb_tiles[z] * 3
            c = nb_sqs * gene.config['cost']['sqs']['request'] / 1000000.0
            price += c
            print('SQS usage: {0:0.2f} [$]'.format(c))

    print("")
    td = timedelta(milliseconds=all_time)
    print("Number of tiles: {}".format(all_tiles))
    print('Generation time: {} [d h:mm:ss]'.format((duration_format(td))))
    print('Generation cost: {0:0.2f} [$]'.format(price))

    return all_size, td, price, all_tiles
