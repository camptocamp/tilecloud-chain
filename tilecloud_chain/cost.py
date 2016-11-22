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
    add_comon_options(parser, tile_pyramid=False)
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
    if (options.layer):
        (all_size, all_time, all_price, all_tiles) = _calculate_cost(gene, options)
        tile_size = gene.layer['cost']['tile_size'] / (1024.0 * 1024)
    else:
        all_time = timedelta()
        all_price = 0
        for layer in gene.config['generation']['default_layers']:
            print("")
            print("===== {0!s} =====".format(layer))
            gene.set_layer(layer, options)
            (size, time, price, tiles) = _calculate_cost(gene, options)
            tile_size += gene.layer['cost']['tile_size'] / (1024.0 * 1024)
            all_time += time
            all_price += price
            all_size += size
            all_tiles += tiles

        print("")
        print("===== GLOBAL =====")
        print("Total number of tiles: {0:d}".format(all_tiles))
        print('Total generation time: {0!s} [d h:mm:ss]'.format((duration_format(all_time))))
        print('Total generation cost: {0:0.2f} [$]'.format(all_price))
    print("")
    print('S3 Storage: {0:0.2f} [$/month]'.format((all_size * gene.config['cost']['s3']['storage'] / (1024.0 * 1024 * 1024))))
    print('S3 get: {0:0.2f} [$/month]'.format((
        gene.config['cost']['s3']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
        gene.config['cost']['s3']['download'] * gene.config['cost']['request_per_layers'] * tile_size))
    )
#    if 'cloudfront' in gene.config['cost']:
#        print('CloudFront: %0.2f [$/month]' % ()
#            gene.config['cost']['cloudfront']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
#            gene.config['cost']['cloudfront']['download'] * gene.config['cost']['request_per_layers'] * tile_size)
    if 'ec2' in gene.config:
        print('ESB storage: {0:0.2f} [$/month]'.format((
            gene.config['cost']['esb']['storage'] * gene.config['cost']['esb_size']))
        )
    sys.exit(0)


def _calculate_cost(gene, options):
    nb_metatiles = {}
    nb_tiles = {}

    meta = gene.layer['meta']
    if options.cost_algo == 'area':
        tile_size = gene.layer['grid_ref']['tile_size']
        for zoom, resolution in enumerate(gene.layer['grid_ref']['resolutions']):
            if 'min_resolution_seed' in gene.layer and resolution < gene.layer['min_resolution_seed']:
                continue

            print("Calculate zoom {0:d}.".format(zoom))

            px_buffer = gene.layer['px_buffer'] + \
                gene.layer['meta_buffer'] if meta else 0
            m_buffer = px_buffer * resolution
            if meta:
                size = tile_size * gene.layer['meta_size'] * resolution
                meta_buffer = size * 0.7 + m_buffer
                meta_geom = gene.geoms[zoom].buffer(meta_buffer, 1)
                nb_metatiles[zoom] = int(round(meta_geom.area / size ** 2))
            size = tile_size * resolution
            tile_buffer = size * 0.7 + m_buffer
            geom = gene.geoms[zoom].buffer(tile_buffer, 1)
            nb_tiles[zoom] = int(round(geom.area / size ** 2))

    elif options.cost_algo == 'count':
        gene.init_tilecoords()
        gene.add_geom_filter()

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
                def get(self, tiles):
                    for metatile in tiles:
                        for tilecoord in metatile.tilecoord:
                            yield Tile(tilecoord)
            gene.tilestream = MetaTileSplitter().get(gene.tilestream)

            # Only keep tiles that intersect geometry
            gene.add_geom_filter()

        def count_tile(tile):
            if tile:
                if tile.tilecoord.z in nb_tiles:
                    nb_tiles[tile.tilecoord.z] += 1
                else:
                    print("Calculate zoom {0:d}.".format(tile.tilecoord.z))
                    nb_tiles[tile.tilecoord.z] = 1
            return tile
        gene.imap(count_tile)

        consume(gene.tilestream, None)

    times = {}
    print('')
    for z in nb_metatiles:
        print("{0:d} meta tiles in zoom {1:d}.".format(nb_metatiles[z], z))
        times[z] = gene.layer['cost']['metatile_generation_time'] * nb_metatiles[z]

    price = 0
    all_size = 0
    all_time = 0
    all_tiles = 0
    for z in nb_tiles:
        print('')
        print("{0:d} tiles in zoom {1:d}.".format(nb_tiles[z], z))
        all_tiles += nb_tiles[z]
        if meta:
            time = times[z] + gene.layer['cost']['tile_generation_time'] * nb_tiles[z]
        else:
            time = gene.layer['cost']['tileonly_generation_time'] * nb_tiles[z]
        size = gene.layer['cost']['tile_size'] * nb_tiles[z]
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print("Time to generate: {0!s} [d h:mm:ss]".format((duration_format(td))))
        c = gene.config['cost']['s3']['put'] * nb_tiles[z] / 1000.0
        price += c
        print('S3 PUT: {0:0.2f} [$]'.format(c))

        if 'ec2' in gene.config:
            c = time * gene.config['cost']['ec2']['usage'] / (1000.0 * 3600)
            price += c
            print('EC2 usage: {0:0.2f} [$]'.format(c))

            c = gene.config['cost']['esb']['io'] * time / (1000.0 * 2600 * 24 * 30)
            price += c
            print('ESB usage: {0:0.2f} [$]'.format(c))

        if 'sqs' in gene.layer:
            if meta:
                nb_sqs = nb_metatiles[z] * 3
            else:
                nb_sqs = nb_tiles[z] * 3
            c = nb_sqs * gene.config['cost']['sqs']['request'] / 1000000.0
            price += c
            print('SQS usage: {0:0.2f} [$]'.format(c))

    print("")
    td = timedelta(milliseconds=all_time)
    print("Number of tiles: {0:d}".format(all_tiles))
    print('Generation time: {0!s} [d h:mm:ss]'.format((duration_format(td))))
    print('Generation cost: {0:0.2f} [$]'.format(price))

    return (all_size, td, price, all_tiles)
