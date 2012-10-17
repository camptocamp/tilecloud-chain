# -*- coding: utf-8 -*-

import os
import sys
import logging
from itertools import ifilter
from datetime import datetime
from getpass import getuser
from optparse import OptionParser

from tilecloud import TileCoord, consume
from tilecloud.store.url import URLTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, DropEmpty

logger = logging.getLogger(__name__)


def _gene(options, gene, layer):
    gene.set_layer(layer, options)

    if options.get_hash:
        options.role = 'hash'
        options.test = 1

    if options.role in ('master', 'slave'):
        # Create SQS queue
        sqs_tilestore = SQSTileStore(gene.get_sqs_queue())

    if options.role in ('local', 'slave'):
        cache = gene.caches[options.cache]
        # build layout
        layout = WMTSTileLayout(
            layer=layer,
            url=cache['folder'],
            style=gene.layer['wmts_style'],
            format='.' + gene.layer['extension'],
            dimensions=[(str(dimension['name']), str(dimension['default']))
                    for dimension in gene.layer['dimensions']],
            tile_matrix_set=gene.layer['grid'],
            request_encoding='REST',
        )
        # store
        if cache['type'] == 's3':
            # on s3
            cache_tilestore = S3TileStore(cache['bucket'], layout)
        elif cache['type'] == 'filesystem':
            # on filesystem
            cache_tilestore = FilesystemTileStore(layout)
        else:
            exit('unknown cache type: ' + cache['type'])

    meta = gene.layer['meta']
    if options.role in ('local', 'master'):
        # Generate a stream of metatiles
        gene.init_tilecoords(options)
        gene.add_geom_filter()

    elif options.role == 'slave':
        # Get the metatiles from the SQS queue
        gene.set_store(sqs_tilestore)

    elif options.role == 'hash':
        z, x, y = (int(v) for v in options.get_hash.split('/'))
        if meta:
            gene.set_tilecoords([TileCoord(z, x, y, gene.layer['meta_size'])])
        else:
            gene.set_tilecoords([TileCoord(z, x, y)])

    # At this stage, the tilestream contains metatiles that intersect geometry
    if options.test > 0:
        gene.imap(Logger(logger, logging.DEBUG, '%(tilecoord)s'))

    if options.role == 'master':
        # Put the metatiles into the SQS queue
        if gene.config['generation']['number_process'] == 1:
            gene.put(sqs_tilestore)
        else:
            from multiprocessing import Pool
            pool = Pool(gene.config['generation']['number_process'])
            pool.imap_unordered(sqs_tilestore.put_one, ifilter(None, gene.tilestream))

        gene.put(sqs_tilestore)

    elif options.role in ('local', 'slave', 'hash'):
        if gene.layer['type'] == 'wms':
            # Get the metatile image from the WMS server
            gene.get(URLTileStore(
                tilelayouts=(WMSTileLayout(
                    url=gene.layer['url'],
                    layers=gene.layer['layers'],
                    srs=gene.layer['grid_ref']['srs'],
                    format=gene.layer['mime_type'],
                    border=gene.layer['meta_buffer'] if meta else 0,
                    tilegrid=gene.get_grid()['obj']
                ),)
            ), True)
        elif gene.layer['type'] == 'mapnik':
            from tilecloud.store.mapnik_ import MapnikTileStore

            if gene.layer['output_format'] == 'grid':
                gene.get(MapnikTileStore(
                    tilegrid=gene.get_grid()['obj'],
                    mapfile=gene.layer['mapfile'],
                    image_buffer=gene.layer['meta_buffer'] if meta else 0,
                    data_buffer=gene.layer['data_buffer'],
                    output_format=gene.layer['output_format'],
                    resolution=gene.layer['resolution'],
                    layers_fields=gene.layer['layers_fields']
                ), False)
            else:
                gene.get(MapnikTileStore(
                    tilegrid=gene.get_grid()['obj'],
                    mapfile=gene.layer['mapfile'],
                    image_buffer=gene.layer['meta_buffer'] if meta else 0,
                    data_buffer=gene.layer['data_buffer'],
                    output_format=gene.layer['output_format'],
                ), False)

        if meta:
            if options.role == 'hash':
                gene.imap(HashLogger('empty_metatile_detection', logger))
            else:
                # Handle errors
                gene.add_error_filters(logger)

                # Discard tiles with certain content
                if meta and 'empty_metatile_detection' in gene.layer:
                    empty_tile = gene.layer['empty_metatile_detection']
                    gene.imap(HashDropper(empty_tile['size'], empty_tile['hash'], store=cache_tilestore))

            def add_elapsed_togenerate(metatile):
                if metatile is not None:
                    metatile.elapsed_togenerate = metatile.tilecoord.n ** 2
                    return True
                return False
            gene.ifilter(add_elapsed_togenerate)

            # Split the metatile image into individual tiles
            gene.get2(MetaTileSplitterTileStore(
                    gene.layer['mime_type'],
                    gene.layer['grid_ref']['tile_size'],
                    gene.layer['meta_buffer']), True)

            if options.role != 'hash':
                # Only keep tiles that intersect geometry
                gene.add_geom_filter()

        if options.role == 'hash':
            gene.imap(HashLogger('empty_tile_detection', logger))
        else:
            # Discard tiles with certain content
            if 'empty_tile_detection' in gene.layer:
                empty_tile = gene.layer['empty_tile_detection']
                gene.imap(HashDropper(empty_tile['size'], empty_tile['hash'], store=cache_tilestore))

    if options.role in ('local', 'slave'):
        if options.test > 0:
            gene.imap(Logger(logger, logging.DEBUG, '%(tilecoord)s'))

        gene.add_error_filters(logger)
        gene.ifilter(DropEmpty())

        if options.time:
            def log_size(tile):
                print len(tile.data)
            gene.imap(log_size)

        gene.put(cache_tilestore)

    gene.add_error_filters(logger)

    if options.role == 'slave':
        if meta:
            def decr_tile_in_metatile(tile):
                tile.metatile.elapsed_togenerate -= 1
                if tile.metatile.elapsed_togenerate == 0:
                    sqs_tilestore.delete_one(tile.metatile)
                return True
            gene.ifilter(decr_tile_in_metatile)
        else:
            gene.delete(sqs_tilestore)

    if options.time:
        consume(gene.tilestream, options.time)
        t1 = datetime.now()
        consume(gene.tilestream, options.time)
        t2 = datetime.now()
        consume(gene.tilestream, options.time)
        d = (t2 - t1) / options.time
        print (d.days * 24 * 3600 + d.seconds) * 1000000 + d.microseconds
    else:
        consume(gene.tilestream, options.test)


def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        exit("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))

    return os.getpid()


def main():

    parser = OptionParser('Used to generate the tiles')
    parser.add_option('-c', '--config', default='tilegeneration/config.yaml',
            help='path to configuration file', metavar="FILE")
    parser.add_option('-d', '--daemonize', default=False, action="store_true",
            help='run as a deamon')
    parser.add_option('-b', '--bbox',
            help='restrict to specified bounding box')
    parser.add_option('-z', '--zoom-level', type='int', dest='zoom',
            help='restrict to specified zoom level', metavar="ZOOM")
    parser.add_option('-l', '--layer', metavar="NAME",
            help='the layer to generate')
    parser.add_option('-t', '--test', type='int', default=None,
            help='test with generating N tiles, and add log messages', metavar="N")
    parser.add_option('-r', '--role', default='local',
            help='local/master/slave, master to file the queue and '
            'slave to generate the tiles')
    parser.add_option('--cache', '--destination-cache',
            default=None, dest='cache', metavar="NAME",
            help='The cache name to use')
    parser.add_option('-H', '--get-hash', metavar="TILE",
            help='get the empty tiles hash, use the specified TILE z/x/y')
    parser.add_option('--time', '--measure-generation-time',
            default=None, dest='time', metavar="N",
            help='Measure the generation time by creating N tiles to warm-up, '
            'N tile to do the measure and N tiles to slow-down')
    (options, args) = parser.parse_args()
    logging.basicConfig(
        format='%(asctime)s:%(levelname)s:%(module)s:%(message)s',
        level=logging.INFO if options.test < 0 else logging.DEBUG)

    if options.daemonize:
        print "Daemonize with pid %i." % daemonize()

    gene = TileGeneration(options.config, options)

    if not options.get_hash and \
            'authorised_user' in gene.config['generation'] and \
            gene.config['generation']['authorised_user'] != getuser():
        exit('not authorised, authorised user is: %s.' % gene.config['generation']['authorised_user'])

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if (options.layer):
        _gene(options, gene, options.layer)
    else:
        for layer in gene.config['generation']['default_layers']:
            _gene(options, gene, layer)
