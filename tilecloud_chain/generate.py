# -*- coding: utf-8 -*-

import os
import sys
import logging
import socket
from datetime import datetime
from getpass import getuser
from optparse import OptionParser

import boto
from boto import sns
from tilecloud import TileCoord, consume
from tilecloud.store.url import URLTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, DropEmpty, TilesFileStore, \
    add_comon_options, parse_tilecoord, quote

logger = logging.getLogger(__name__)


def _gene(options, gene, layer):
    if options.role == 'slave' or options.get_hash or options.get_bbox:
        gene.layer = gene.layers[layer]
    else:
        gene.set_layer(layer, options)

    if options.get_bbox:
        try:
            tilecoord = parse_tilecoord(options.get_bbox)
            print \
                "Tile bounds: [%i,%i,%i,%i]" % \
                gene.layer['grid_ref']['obj'].extent(tilecoord)
            exit()
        except ValueError as e:  # pragma: no cover
            exit(
                "Tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n\n%r" %
                (options.get_bbox, e)
            )

    if options.get_hash:
        options.role = 'hash'
        options.test = 1

    sqs_tilestore = None
    if options.role in ('master', 'slave'):
        # Create SQS queue
        sqs_tilestore = SQSTileStore(gene.get_sqs_queue())  # pragma: no cover

    if options.role in ('local', 'slave'):
        cache = gene.caches[options.cache]
        cache_tilestore = gene.get_store(cache, gene.layer)
        if cache_tilestore is None:
            exit('unknown cache type: ' + cache['type'])  # pragma: no cover

    meta = gene.layer['meta']
    if options.tiles_file:
        gene.set_store(TilesFileStore(options.tiles_file))

    elif options.role in ('local', 'master'):
        # Generate a stream of metatiles
        gene.init_tilecoords(options)
        gene.add_geom_filter()

    elif options.role == 'slave':
        # Get the metatiles from the SQS queue
        gene.set_store(sqs_tilestore)  # pragma: no cover

    elif options.role == 'hash':
        try:
            z, x, y = (int(v) for v in options.get_hash.split('/'))
            if meta:
                gene.set_tilecoords([TileCoord(z, x, y, gene.layer['meta_size'])])
            else:
                gene.set_tilecoords([TileCoord(z, x, y)])
        except ValueError as e:  # pragma: no cover
            exit(
                "Tile '%s' is not in the format 'z/x/y'\n%r" %
                (options.get_hash, e)
            )

    # At this stage, the tilestream contains metatiles that intersect geometry
    def logTile(tile):
        variables = dict()
        variables.update(tile.__dict__)
        variables.update(tile.tilecoord.__dict__)
        sys.stdout.write("%(tilecoord)s          \r" % variables)
        sys.stdout.flush()
        return tile
    gene.imap(logTile)

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
            ), "Get tile from WMS")
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
                    layers_fields=gene.layer['layers_fields'],
                    drop_empty_utfgrid=gene.layer['drop_empty_utfgrid'],
                ), "Create Mapnik grid tile")
            else:
                gene.get(MapnikTileStore(
                    tilegrid=gene.get_grid()['obj'],
                    mapfile=gene.layer['mapfile'],
                    image_buffer=gene.layer['meta_buffer'] if meta else 0,
                    data_buffer=gene.layer['data_buffer'],
                    output_format=gene.layer['output_format'],
                ), "Create Mapnik tile")

        if meta:
            if options.role == 'hash':
                gene.imap(HashLogger('empty_metatile_detection'))
            elif not options.near:
                # Handle errors
                gene.add_error_filters(logger)

                # Discard tiles with certain content
                if 'empty_metatile_detection' in gene.layer:
                    empty_tile = gene.layer['empty_metatile_detection']
                    gene.imap(HashDropper(
                        empty_tile['size'], empty_tile['hash'], store=cache_tilestore,
                        queue_store=sqs_tilestore
                    ))

            def add_elapsed_togenerate(metatile):
                if metatile is not None:
                    metatile.elapsed_togenerate = metatile.tilecoord.n ** 2
                    return True
                return False  # pragma: no cover
            gene.ifilter(add_elapsed_togenerate)

            # Split the metatile image into individual tiles
            gene.add_metatile_splitter()
            gene.imap(Logger(logger, logging.INFO, '%(tilecoord)s'))

        if options.role == 'hash':
            gene.imap(HashLogger('empty_tile_detection'))
        elif not options.near:
            # Discard tiles with certain content
            if 'empty_tile_detection' in gene.layer:
                empty_tile = gene.layer['empty_tile_detection']
                gene.imap(HashDropper(
                    empty_tile['size'], empty_tile['hash'], store=cache_tilestore,
                    queue_store=sqs_tilestore
                ))

    if options.role in ('local', 'slave'):
        gene.add_error_filters(logger)
        gene.ifilter(DropEmpty())

        if options.time:
            def log_size(tile):
                sys.stdout.write('size: %i\n' % len(tile.data))
                return tile
            gene.imap(log_size)

        gene.put(cache_tilestore, "Store the tile")

    gene.add_error_filters(logger)
    if options.generated_tiles_file:  # pragma: no cover
        generated_tiles_file = open(options.generated_tiles_file, 'a')

        def do(tile):
            generated_tiles_file.write('%s\n' % (tile.tilecoord, ))
            return tile
        gene.imap(do)

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

    if options.role != 'hash' and options.time is None and 'sns' in gene.config:  # pragma: no cover
        if 'region' in gene.config['sns']:
            connection = sns.connect_to_region(gene.config['sns']['region'])
        else:
            connection = boto.connect_sns()
        connection.publish(
            gene.config['sns']['topic'],
            """The tile generation is finish
Layer: %(layer)s
Role: %(role)s
Host: %(host)s
Command: %(cmd)s""" %
            {
                'role': options.role,
                'layer': gene.layer['name'],
                'host': socket.getfqdn(),
                'cmd': ' '.join([quote(arg) for arg in sys.argv])
            },
            "Tile generation (%(layer)s - %(role)s)" % {
                'role': options.role,
                'layer': gene.layer['name']
            }
        )


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
    parser.add_option(
        '--daemonize', default=False, action="store_true",
        help='run as a deamon'
    )
    parser.add_option(
        '-r', '--role', default='local',
        help='local/master/slave, master to file the queue and '
        'slave to generate the tiles'
    )
    parser.add_option(
        '-H', '--get-hash', metavar="TILE",
        help='get the empty tiles hash, use the specified TILE z/x/y'
    )
    parser.add_option(
        '--get-bbox', metavar="TILE",
        help='get the bbox of a tile, use the specified TILE z/x/y, or z/x/y:+n/+n for metatiles'
    )
    parser.add_option(
        '--tiles-file', metavar="FILE",
        help='Generate the tiles from a tiles file, use the format z/x/y, or z/x/y:+n/+n for metatiles'
    )
    parser.add_option(
        '--generated-tiles-file', metavar="FILE",
        help='Store the tiles in a file (unrecommended)'
    )

    (options, args) = parser.parse_args()

    if options.daemonize:
        daemonize()  # pragma: no cover

    gene = TileGeneration(options.config, options)

    if not options.get_hash and not options.get_bbox and \
            'authorised_user' in gene.config['generation'] and \
            gene.config['generation']['authorised_user'] != getuser():
        exit('not authorised, authorised user is: %s.' % gene.config['generation']['authorised_user'])

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if options.tiles_file and options.role not in ['local', 'master']:  # pragma: no cover
        exit("The --tiles-file option worky only with role local or master")

    try:
        if (options.layer):
            _gene(options, gene, options.layer)
        elif options.get_bbox:  # pragma: no cover
            exit("With --get-bbox option we needs to specify a layer")
        elif options.get_hash:  # pragma: no cover
            exit("With --get-hash option we needs to specify a layer")
        elif options.tiles_file:  # pragma: no cover
            exit("With --tiles-file option we needs to specify a layer")
        else:
            for layer in gene.config['generation']['default_layers']:
                _gene(options, gene, layer)
    finally:
        if gene.error_file is not None:
            gene.error_file.close()
