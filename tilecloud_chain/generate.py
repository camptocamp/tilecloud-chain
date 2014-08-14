# -*- coding: utf-8 -*-

import os
import re
import sys
import logging
import socket
import random
from datetime import datetime
from getpass import getuser
from argparse import ArgumentParser

import boto
from boto import sns
from tilecloud import TileCoord
from tilecloud.store.url import URLTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, DropEmpty, TilesFileStore, \
    add_comon_options, parse_tilecoord, quote, Count
from tilecloud_chain.format import size_format, duration_format

logger = logging.getLogger(__name__)


class Generate:
    _re_rm_xml_tag = re.compile('(<[^>]*>|\n)')

    def gene(self, options, gene, layer):
        count_metatiles = None
        count_metatiles_dropped = Count()
        count_tiles = None
        count_tiles_dropped = Count()

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

        cache_tilestore = None
        if options.role in ('local', 'slave'):
            cache_tilestore = gene.get_tilesstore(options.cache)

        meta = gene.layer['meta']
        if options.tiles:
            gene.set_store(TilesFileStore(options.tiles))

        elif options.role in ('local', 'master'):
            # Generate a stream of metatiles
            gene.init_tilecoords()
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
        gene.add_logger()

        count_metatiles = gene.counter()

        if options.role == 'master':  # pragma: no cover
            # Put the metatiles into the SQS queue
            gene.put(sqs_tilestore)

        elif options.role in ('local', 'slave', 'hash'):
            if gene.layer['type'] == 'wms':
                params = gene.layer['params'].copy()
                if 'STYLES' not in params:
                    params['STYLES'] = ','.join(gene.layer['wmts_style'] for l in gene.layer['layers'])
                if gene.layer['generate_salt']:
                    params['SALT'] = str(random.randint(0, sys.maxint))
                for dim in gene.layer['dimensions']:
                    params[dim['name']] = dim['value']
                for dim in gene.options.dimensions:
                    dim = dim.split('=')
                    if len(dim) != 2:  # pragma: no cover
                        exit(
                            'the DIMENTIONS option should be like this '
                            'DATE=2013 VERSION=13.'
                        )
                    params[dim[0]] = dim[1]

                # Get the metatile image from the WMS server
                gene.get(URLTileStore(
                    tilelayouts=(WMSTileLayout(
                        url=gene.layer['url'],
                        layers=','.join(gene.layer['layers']),
                        srs=gene.layer['grid_ref']['srs'],
                        format=gene.layer['mime_type'],
                        border=gene.layer['meta_buffer'] if meta else 0,
                        tilegrid=gene.get_grid()['obj'],
                        params=params,
                    ),),
                    headers=gene.layer['headers'],
                ), "Get tile from WMS")
            elif gene.layer['type'] == 'mapnik':
                from tilecloud.store.mapnik_ import MapnikTileStore
                from tilecloud_chain.mapnik_ import MapnikDropActionTileStore

                grid = gene.get_grid()
                if gene.layer['output_format'] == 'grid':
                    gene.get(MapnikDropActionTileStore(
                        tilegrid=grid['obj'],
                        mapfile=gene.layer['mapfile'],
                        image_buffer=gene.layer['meta_buffer'] if meta else 0,
                        data_buffer=gene.layer['data_buffer'],
                        output_format=gene.layer['output_format'],
                        resolution=gene.layer['resolution'],
                        layers_fields=gene.layer['layers_fields'],
                        drop_empty_utfgrid=gene.layer['drop_empty_utfgrid'],
                        store=cache_tilestore,
                        queue_store=sqs_tilestore,
                        count=count_tiles_dropped,
                        proj4_literal=grid['proj4_literal'],
                    ), "Create Mapnik grid tile")
                else:
                    gene.get(MapnikTileStore(
                        tilegrid=grid['obj'],
                        mapfile=gene.layer['mapfile'],
                        image_buffer=gene.layer['meta_buffer'] if meta else 0,
                        data_buffer=gene.layer['data_buffer'],
                        output_format=gene.layer['output_format'],
                        proj4_literal=grid['proj4_literal'],
                    ), "Create Mapnik tile")

            def wrong_content_type_to_error(tile):
                if tile is not None and tile.content_type is not None \
                        and tile.content_type.find("image/") != 0:
                    if tile.content_type.find("application/vnd.ogc.se_xml") == 0:
                        tile.error = "WMS server error: %s" % (
                            self._re_rm_xml_tag.sub('', tile.data)
                        )
                    else:  # pragma: no cover
                        tile.error = "%s is not an image format, error: %s" % (
                            tile.content_type,
                            tile.data
                        )
                return tile
            gene.imap(wrong_content_type_to_error)

            # Handle errors
            gene.add_error_filters()

            if meta:
                if options.role == 'hash':
                    gene.imap(HashLogger('empty_metatile_detection'))
                elif not options.near:
                    # Discard tiles with certain content
                    if 'empty_metatile_detection' in gene.layer:
                        empty_tile = gene.layer['empty_metatile_detection']

                        gene.imap(HashDropper(
                            empty_tile['size'], empty_tile['hash'], store=cache_tilestore,
                            queue_store=sqs_tilestore,
                            count=count_metatiles_dropped,
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

                # Handle errors
                gene.add_error_filters()

            self.count_tiles = gene.counter()

            if 'pre_hash_post_process' in gene.layer:
                gene.process(gene.layer['pre_hash_post_process'])

            if options.role == 'hash':
                gene.imap(HashLogger('empty_tile_detection'))
            elif not options.near:
                # Discard tiles with certain content
                if 'empty_tile_detection' in gene.layer:
                    empty_tile = gene.layer['empty_tile_detection']

                    gene.imap(HashDropper(
                        empty_tile['size'], empty_tile['hash'], store=cache_tilestore,
                        queue_store=sqs_tilestore,
                        count=count_tiles_dropped,
                    ))

            gene.process()

        if options.role in ('local', 'slave'):
            gene.add_error_filters()
            gene.ifilter(DropEmpty(gene))
            count_tiles = gene.counter(size=True)

            if options.time:
                def log_size(tile):
                    sys.stdout.write('size: %i\n' % len(tile.data))
                    return tile
                gene.imap(log_size)

            gene.put(cache_tilestore, "Store the tile")
        else:
            count_tiles = gene.counter(size=True)

        gene.add_error_filters()
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

        if options.time is not None:
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

            gene.consume(options.time * 3)
        else:
            gene.consume()

            if not options.quiet and options.role in ('local', 'slave'):
                nb_tiles = count_tiles.nb + count_tiles_dropped.nb
                print """The tile generation of layer '%s' is finish
%sNb generated tiles: %i
Nb tiles dropped: %i
Nb tiles stored: %i
Nb error: %i
Total time: %s
Total size: %s
Time per tiles: %i ms
Size per tile: %i o
""" % \
                    (
                        gene.layer['name'],
                        """Nb generated metatiles: %i
Nb metatiles dropped: %i
""" %
                        (
                            count_metatiles.nb, count_metatiles_dropped.nb
                        ) if meta else '',
                        nb_tiles,
                        count_tiles_dropped.nb,
                        count_tiles.nb,
                        gene.error,
                        duration_format(gene.duration),
                        size_format(count_tiles.size),
                        (gene.duration / nb_tiles * 1000).seconds if nb_tiles != 0 else 0,
                        count_tiles.size / count_tiles.nb if count_tiles.nb != 0 else -1
                    )

        if cache_tilestore is not None and hasattr(cache_tilestore, 'connection'):
            cache_tilestore.connection.close()

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
Command: %(cmd)s

%(meta)sNb generated tiles: %(nb_tiles)i
Nb tiles dropped: %(nb_tiles_dropped)i
Total time: %(duration)s [s]
Time per tiles: %(tile_duration)i [ms]""" %
                {
                    'role': options.role,
                    'layer': gene.layer['name'],
                    'host': socket.getfqdn(),
                    'cmd': ' '.join([quote(arg) for arg in sys.argv]),
                    'meta': """Nb generated metatiles: %(nb_metatiles)i
Nb metatiles dropped: %(nb_metatiles_dropped)i
""" %
                    {
                        'nb_metatiles': count_metatiles.nb,
                        'nb_metatiles_dropped': count_metatiles_dropped.nb,
                    } if meta else '',
                    'nb_tiles': nb_tiles if meta else count_metatiles.nb,
                    'nb_tiles_dropped': count_tiles_dropped.nb if meta else count_metatiles_dropped.nb,
                    'duration': duration_format(gene.duration),
                    'tile_duration': (gene.duration / nb_tiles * 1000).seconds if nb_tiles != 0 else 0,
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
    parser = ArgumentParser(description='Used to generate the tiles', prog='./buildout/bin/generate_tiles')
    add_comon_options(parser, dimensions=True)
    parser.add_argument(
        '--get-hash', metavar="TILE",
        help='get the empty tiles hash, use the specified TILE z/x/y'
    )
    parser.add_argument(
        '--get-bbox', metavar="TILE",
        help='get the bbox of a tile, use the specified TILE z/x/y, or z/x/y:+n/+n for metatiles'
    )
    parser.add_argument(
        '--role', default='local', choices=('local', 'master', 'slave'),
        help='local/master/slave, master to file the queue and '
        'slave to generate the tiles'
    )
    parser.add_argument(
        '--daemonize', default=False, action="store_true",
        help='run as a daemon'
    )
    parser.add_argument(
        '--tiles', metavar="FILE",
        help='Generate the tiles from a tiles file, use the format z/x/y, or z/x/y:+n/+n for metatiles'
    )
    parser.add_argument(
        '--generated-tiles-file', metavar="FILE",
        help='Store the tiles in a file (unrecommended)'
    )

    options = parser.parse_args()

    if options.daemonize:
        daemonize()  # pragma: no cover

    gene = TileGeneration(options.config, options)

    if options.get_hash is None and options.get_bbox is None and \
            'authorised_user' in gene.config['generation'] and \
            gene.config['generation']['authorised_user'] != getuser():
        exit('not authorised, authorised user is: %s.' % gene.config['generation']['authorised_user'])

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if options.tiles is not None and options.role not in ['local', 'master']:  # pragma: no cover
        exit("The --tiles option work only with role local or master")

    try:
        if (options.layer):
            generate = Generate()
            generate.gene(options, gene, options.layer)
        elif options.get_bbox:  # pragma: no cover
            exit("With --get-bbox option we needs to specify a layer")
        elif options.get_hash:  # pragma: no cover
            exit("With --get-hash option we needs to specify a layer")
        elif options.tiles:  # pragma: no cover
            exit("With --tiles option we needs to specify a layer")
        else:
            for layer in gene.config['generation']['default_layers']:
                generate = Generate()
                generate.gene(options, gene, layer)
    finally:
        if gene.error_file is not None:
            gene.error_file.close()
