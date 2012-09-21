# -*- coding: utf-8 -*-

import logging
from optparse import OptionParser

from tilecloud import BoundingPyramid, Tile, consume
from tilecloud.store.url import URLTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.store.mapnik_utils import MapnikTileStore
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain.tilegeneration import TileGeneration, HashDropper

logger = logging.getLogger(__name__)


def _gene(options, gene, layer):
    gene.layer = gene.layers[layer]

    geometry = gene.get_geom()
    if geometry:
        extent = geometry.bounds
    else:
        extent = gene.layer['grid_ref']['bbox']

    bounding_pyramid = BoundingPyramid(tilegrid=gene.layer['grid_ref']['obj'])
    bounding_pyramid.fill(None, extent)

    if options.role in ('master', 'slave'):
        # Create SQS queue
        sqs_tilestore = SQSTileStore(gene.get_sqs_queue())

    if options.role in ('local', 'master'):
        # Generate a stream of metatiles
        gene.set_metatilecoords(
            bounding_pyramid.metatilecoords(
                gene.layer['meta_size']
                if gene.layer.get('meta', False) else 1))
        gene.add_geom_filter()

    elif options.role == 'slave':
        # Get the metatiles from the SQS queue
        gene.set_store(sqs_tilestore)

    # At this stage, the tilestream contains metatiles that intersect geometry
    if options.test > 0:
        gene.imap(Logger(logger, logging.DEBUG, '%(tilecoord)s'))

    if options.role == 'master':
        # Put the metatiles into the SQS queue
        gene.put(sqs_tilestore)

    elif options.role in ('local', 'slave'):
        if gene.layer['type'] == 'wms':
            # Get the metatile image from the WMS server
            gene.get(URLTileStore(
                tilelayouts=(WMSTileLayout(
                    url=gene.layer['url'],
                    layers=gene.layer['layers'],
                    srid=gene.layer['grid_ref']['srs'],
                    image_format=gene.layer['extension'],
                    buffer=(
                        gene.layer['meta_buffer']
                        if gene.layer.get('meta', False) else 0),
                    grid=gene.get_grid()['obj']
                ),)
            ))
        elif gene.layer['type'] == 'mapnik':
            if (
                    gene.layer.get('output_format', 'png') == 'grid' and
                    gene.layer.get('meta', False)):
                exit("Mapnik/Grid layers don't support metatiles.")

            gene.get(MapnikTileStore(
                tilegrid=gene.get_grid()['obj'],
                mapfile=gene.layer['mapfile'],
                image_buffer=(
                    gene.layer['meta_buffer']
                    if gene.layer.get('meta', False) else 0),
                data_buffer=gene.layer.get('data_buffer', 128),
                output_format=gene.layer.get('output_format', 'png'),
                layers_fields=gene.layer.get('layers_fields', {})
            ))

        if options.role == 'slave':
            # Mark the metatile as done
            # FIXME this is erronenous, the metatile is only really
            # done when all its tiles are done
            gene.delete(sqs_tilestore)

        # Handle errors
        gene.add_error_filters(logger)

        # Discard tiles with certain content
        if 'empty_metatile_detection' in gene.layer \
                and 'size' in gene.layer['empty_metatile_detection'] \
                and 'hash' in gene.layer['empty_metatile_detection']:
            empty_tile = gene.layer['empty_metatile_detection']
            gene.imap(HashDropper(empty_tile['size'], empty_tile['hash']))

        # Split the metatile image into individual tiles
        if gene.layer.get('meta', False):
            gene.get(MetaTileSplitterTileStore(
                    gene.layer['mime_type'],
                    gene.layer['grid_ref']['tile_size'],
                    gene.layer['meta_buffer']))

        # Only keep tiles that intersect geometry
        gene.add_geom_filter()

        # Discard tiles with certain content
        if 'empty_tile_detection' in gene.layer \
                and 'size' in gene.layer['empty_tile_detection'] \
                and 'hash' in gene.layer['empty_tile_detection']:
            empty_tile = gene.layer['empty_tile_detection']
            gene.imap(HashDropper(empty_tile['size'], empty_tile['hash']))

        if options.role == 'slave':
            # read metatile on error
            def tile_error(tile):
                if tile and tile.error:
                    sqs_tilestore.put_one(Tile(tile.tilecoord.metatilecoord(
                            gene.layer['metatile_size'])))
            gene.imap(tile_error)

        gene.add_error_filters(logger)

        cache = gene.caches[options.cache]
        # build layout
        layout = WMTSTileLayout(
            layer=layer,
            url=cache['folder'],
            style=gene.layer['wmts']['style'],
            format='.' + gene.layer['extension'],
            dimensions=[(str(dimension['name']), str(dimension['default']))
                    for dimension in gene.layer['dimensions']],
            tile_matrix_set=gene.layer['grid'],
            request_encoding='REST',
        )
        # store
        if cache['type'] == 's3':
            # on s3
            gene.put(S3TileStore(gene.metadata['s3_bucket'], layout))
        elif cache['type'] == 'filesystem':
            # on filesystem
            gene.put(FilesystemTileStore(layout))
        else:
            exit('unknown cache type: ' + cache['type'])

    if options.role == 'slave':
        gene.imap(tile_error)

    gene.add_error_filters(logger)

    consume(gene.tilestream, options.test)


def main():

    parser = OptionParser('Used to generate the tiles')
    parser.add_option('-c', '--config', default='tilegeneration/config.yaml',
            help='path to configuration file')
    parser.add_option('-b', '--bbox',
            help='restrict to specified bounding box')
    parser.add_option('-l', '--layer',
            help='the layer to generate')
    parser.add_option('-t', '--test', type='int', default=None,
            help='test with generating TEST tiles, and add log messages')
    parser.add_option('-r', '--role', default='local',
            help='local/master/slave, master to file the queue and '
            'slave to generate the tiles')
    parser.add_option('--cache', '--destination-cache',
            default=None, dest='cache',
            help='The cache name to use')
    (options, args) = parser.parse_args()
    logging.basicConfig(
        format='%(asctime)s:%(levelname)s:%(module)s:%(message)s',
        level=logging.INFO if options.test < 0 else logging.DEBUG)

    gene = TileGeneration(options.config)

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if (options.layer):
        _gene(options, gene, options.layer)
    else:
        for layer in gene.config['generation']['default_layers']:
            _gene(options, gene, layer)
