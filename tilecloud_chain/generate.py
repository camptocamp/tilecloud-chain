# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime
from getpass import getuser
from optparse import OptionParser

from tilecloud import TileCoord, consume
from tilecloud.store.url import URLTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, DropEmpty, add_comon_options

logger = logging.getLogger(__name__)


def _gene(options, gene, layer):
    gene.set_layer(layer, options)

    if options.get_hash:
        options.role = 'hash'
        options.test = 1

    sqs_tilestore = None
    if options.role in ('master', 'slave'):
        # Create SQS queue
        sqs_tilestore = SQSTileStore(gene.get_sqs_queue())  # pragma: no cover

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
            cache_tilestore = S3TileStore(cache['bucket'], layout)  # pragma: no cover
        elif cache['type'] == 'filesystem':
            # on filesystem
            cache_tilestore = FilesystemTileStore(layout)
        else:
            exit('unknown cache type: ' + cache['type'])  # pragma: no cover

    meta = gene.layer['meta']
    if options.role in ('local', 'master'):
        # Generate a stream of metatiles
        gene.init_tilecoords(options)
        gene.add_geom_filter()

    elif options.role == 'slave':
        # Get the metatiles from the SQS queue
        gene.set_store(sqs_tilestore)  # pragma: no cover

    elif options.role == 'hash':
        z, x, y = (int(v) for v in options.get_hash.split('/'))
        if meta:
            gene.set_tilecoords([TileCoord(z, x, y, gene.layer['meta_size'])])
        else:
            gene.set_tilecoords([TileCoord(z, x, y)])

    # At this stage, the tilestream contains metatiles that intersect geometry
    if options.test > 0 or options.verbose:
        gene.imap(Logger(logger, logging.INFO, '%(tilecoord)s'))

    if options.role == 'master':  # pragma: no cover
        # Put the metatiles into the SQS queue
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
            ))
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
                ))
            else:
                gene.get(MapnikTileStore(
                    tilegrid=gene.get_grid()['obj'],
                    mapfile=gene.layer['mapfile'],
                    image_buffer=gene.layer['meta_buffer'] if meta else 0,
                    data_buffer=gene.layer['data_buffer'],
                    output_format=gene.layer['output_format'],
                ))

        if meta:
            if options.role == 'hash':
                gene.imap(HashLogger('empty_metatile_detection'))
            elif not options.near:
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
                return False  # pragma: no cover
            gene.ifilter(add_elapsed_togenerate)

            # Split the metatile image into individual tiles
            gene.add_metatile_splitter()

            if options.role != 'hash':
                # Only keep tiles that intersect geometry
                gene.add_geom_filter(sqs_tilestore)

        if options.role == 'hash':
            gene.imap(HashLogger('empty_tile_detection'))
        elif not options.near:
            # Discard tiles with certain content
            if 'empty_tile_detection' in gene.layer:
                empty_tile = gene.layer['empty_tile_detection']
                gene.imap(HashDropper(empty_tile['size'], empty_tile['hash'], store=cache_tilestore))

    if options.role in ('local', 'slave'):
        if options.test > 0 or options.verbose:
            gene.imap(Logger(logger, logging.DEBUG, '%(tilecoord)s'))

        gene.add_error_filters(logger)
        gene.ifilter(DropEmpty())

        if options.time:
            def log_size(tile):
                sys.stdout.write('size: %i\n' % len(tile.data))
                return tile
            gene.imap(log_size)

        gene.put(cache_tilestore)

    gene.add_error_filters(logger)

    if options.role == 'slave':  # pragma: no cover
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
        class log_time:
            n = 0
            t1 = None

            def __call__(self, tile):
                self.n += 1
                if self.n == options.time:
                    self.t1 = datetime.now()
                elif self.n == 2 * options.time:
                    t2 = datetime.now()
                    d = (t2 - self.t1) / options.time
                    sys.stdout.write('time: %i\n' % ((d.days * 24 * 3600 + d.seconds) * 1000000 + d.microseconds))
                return tile
        gene.imap(log_time())

        consume(gene.tilestream, options.time * 3)
    else:
        consume(gene.tilestream, options.test)


def daemonize():  # pragma: no cover
    try:
        pid = os.fork()
        if pid > 0:
            print "Daemonize with pid %i." % pid
            sys.stderr.write(str(pid))
            # exit parent
            sys.exit(0)
    except OSError, e:
        exit("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))


def main():

    parser = OptionParser('Used to generate the tiles')
    add_comon_options(parser)
    parser.add_option('-d', '--daemonize', default=False, action="store_true",
            help='run as a deamon')
    parser.add_option('-r', '--role', default='local',
            help='local/master/slave, master to file the queue and '
            'slave to generate the tiles')
    parser.add_option('-H', '--get-hash', metavar="TILE",
            help='get the empty tiles hash, use the specified TILE z/x/y')

    (options, args) = parser.parse_args()

    if options.daemonize:
        daemonize()  # pragma: no cover

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
