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
from six import PY3

import boto
from boto import sns
from tilecloud import TileCoord
from tilecloud.store.url import URLTileStore
from tilecloud.store.sqs import SQSTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, DropEmpty, TilesFileStore, \
    add_comon_options, parse_tilecoord, quote, Count
from tilecloud_chain.format import size_format, duration_format, default_int

logger = logging.getLogger(__name__)


class Generate:
    _re_rm_xml_tag = re.compile('(<[^>]*>|\n)')

    def gene(self, options, gene, layer):
        if options.role == 'slave' or options.get_hash or options.get_bbox:
            gene.layer = gene.layers[layer]
        else:
            gene.set_layer(layer, options)

        if options.role in ('local', 'slave', 'hash'):
            all_dimensions = gene.get_all_dimensions()

            if len(all_dimensions) == 0:  # pragma: no cover
                self._gene(options, gene, layer)
            else:
                for dimensions in all_dimensions:
                    self._gene(options, gene, layer, dimensions)
        else:  # pragma: no cover
            self._gene(options, gene, layer)

    def _gene(self, options, gene, layer, dimensions=None):
        if dimensions is None:  # pragma: no cover
            dimensions = {}
        count_metatiles = None
        count_metatiles_dropped = Count()
        count_tiles = None
        count_tiles_dropped = Count()
        count_tiles_stored = None

        if options.get_bbox:
            try:
                tilecoord = parse_tilecoord(options.get_bbox)
                print("Tile bounds: [{},{},{},{}]".format(
                    *default_int(gene.layer['grid_ref']['obj'].extent(tilecoord))
                ))
                exit()
            except ValueError as e:  # pragma: no cover
                print(
                    "Tile '{}' is not in the format 'z/x/y' or z/x/y:+n/+n\n{1!r}".format(options.get_bbox, e)
                )
                exit(1)

        if options.get_hash:
            options.role = 'hash'
            options.test = 1

        sqs_tilestore = None
        if options.role in ('master', 'slave'):
            # Create SQS queue
            sqs_tilestore = SQSTileStore(gene.get_sqs_queue())  # pragma: no cover

        cache_tilestore = None
        if options.role in ('local', 'slave'):
            cache_tilestore = gene.get_tilesstore(options.cache, dimensions)

        meta = gene.layer['meta']
        if options.tiles:
            gene.set_store(TilesFileStore(options.tiles))

        elif options.role in ('local', 'master'):
            # Generate a stream of metatiles
            gene.init_tilecoords()
            gene.add_geom_filter()

        if options.local_process_number is not None:  # pragma: no cover
            gene.add_local_process_filter()

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
                    "Tile '{}' is not in the format 'z/x/y'\n{1!r}".format(options.get_hash, e)
                )

        # At this stage, the tilestream contains metatiles that intersect geometry
        gene.add_logger()

        count_metatiles = gene.counter()

        if options.role == 'master':  # pragma: no cover
            # Put the metatiles into the SQS queue
            gene.put(sqs_tilestore)
            count_tiles = gene.counter()

        elif options.role in ('local', 'slave', 'hash'):
            if gene.layer['type'] == 'wms':
                params = gene.layer['params'].copy()
                if 'STYLES' not in params:
                    params['STYLES'] = ','.join(gene.layer['wmts_style'] for l in gene.layer['layers'].split(','))
                if gene.layer['generate_salt']:
                    params['SALT'] = str(random.randint(0, 999999))
                params.update(dimensions)

                # Get the metatile image from the WMS server
                gene.get(URLTileStore(
                    tilelayouts=(WMSTileLayout(
                        url=gene.layer['url'],
                        layers=gene.layer['layers'],
                        srs=gene.layer['grid_ref']['srs'],
                        format=gene.layer['mime_type'],
                        border=gene.layer['meta_buffer'] if meta else 0,
                        tilegrid=gene.get_grid()['obj'],
                        params=params,
                    ),),
                    headers=gene.layer['headers'],
                ), "Get tile from WMS")
            elif gene.layer['type'] == 'mapnik':  # pragma: no cover
                from tilecloud.store.mapnik_ import MapnikTileStore
                from tilecloud_chain.mapnik_ import MapnikDropActionTileStore

                grid = gene.get_grid()
                if gene.layer['output_format'] == 'grid':
                    count_tiles = gene.counter()
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
                        tile.error = "WMS server error: {}".format((
                            self._re_rm_xml_tag.sub(
                                '', tile.data.decode('utf-8') if PY3 else tile.data
                            )
                        ))
                    else:  # pragma: no cover
                        tile.error = "{} is not an image format, error: {}".format(
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

            if gene.layer['type'] != 'mapnik' or gene.layer['output_format'] != 'grid':
                count_tiles = gene.counter()

            if 'pre_hash_post_process' in gene.layer:  # pragma: no cover
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
        else:  # pragma: no cover
            count_tiles = gene.counter()

        if options.role in ('local', 'slave'):
            gene.add_error_filters()
            gene.ifilter(DropEmpty(gene))
            count_tiles_stored = gene.counter(size=True)

            if options.time:
                def log_size(tile):
                    sys.stdout.write('size: {}\n'.format(len(tile.data)))
                    return tile
                gene.imap(log_size)

            gene.put(cache_tilestore, "Store the tile")

        gene.add_error_filters()
        if options.generated_tiles_file:  # pragma: no cover
            generated_tiles_file = open(options.generated_tiles_file, 'a')

            def do(tile):
                generated_tiles_file.write('{}\n'.format(tile.tilecoord))
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

        message = []
        if options.time is not None:
            class LogTime:
                n = 0
                t1 = None

                def __call__(self, tile):
                    self.n += 1
                    if self.n == options.time:
                        self.t1 = datetime.now()
                    elif self.n == 2 * options.time:
                        t2 = datetime.now()
                        d = (t2 - self.t1) / options.time
                        sys.stdout.write('time: {}\n'.format(
                            ((d.days * 24 * 3600 + d.seconds) * 1000000 + d.microseconds)
                        ))
                    return tile
            gene.imap(LogTime())

            gene.consume(options.time * 3)
        else:
            gene.consume()

            message = [
                "The tile generation of layer '{}{}' is finish".format(
                    gene.layer['name'],
                    "" if len(dimensions) == 0 or gene.layer['type'] != 'wms'
                    else " ({})".format(", ".join(["=".join(d) for d in dimensions.items()]))
                ),
            ]
            if options.role == "master":  # pragma: no cover
                message.append("Nb of generated jobs: {}".format(count_tiles.nb))
            else:
                if meta:
                    message += [
                        "Nb generated metatiles: {}".format(count_metatiles.nb),
                        "Nb metatiles dropped: {}".format(count_metatiles_dropped.nb),
                    ]
                message += [
                    "Nb generated tiles: {}".format(count_tiles.nb),
                    "Nb tiles dropped: {}".format(count_tiles_dropped.nb),
                ]
                if options.role in ('local', 'slave'):
                    message += [
                        "Nb tiles stored: {}".format(count_tiles_stored.nb),
                        "Nb tiles in error: {}".format(gene.error),
                        "Total time: {}".format(duration_format(gene.duration)),
                    ]
                    if count_tiles_stored.nb != 0:
                        message.append("Total size: {}".format(size_format(count_tiles_stored.size)))
                    if count_tiles.nb != 0:
                        message.append("Time per tile: {:0.0f} ms".format(
                            (gene.duration / count_tiles.nb * 1000).seconds)
                        )
                    if count_tiles_stored.nb != 0:
                        message.append("Size per tile: {:0.0f} o".format(
                            count_tiles_stored.size / count_tiles_stored.nb)
                        )

            if not options.quiet and options.role in ('local', 'slave'):
                print("\n".join(message) + "\n")

        if cache_tilestore is not None and hasattr(cache_tilestore, 'connection'):
            cache_tilestore.connection.close()

        if options.role != 'hash' and options.time is None and 'sns' in gene.config:  # pragma: no cover
            if 'region' in gene.config['sns']:
                connection = sns.connect_to_region(gene.config['sns']['region'])
            else:
                connection = boto.connect_sns()
            sns_message = [message[0]]
            sns_message += [
                "Layer: {}".format(gene.layer['name']),
                "Role: {}".format(options.role),
                "Host: {}".format(socket.getfqdn()),
                "Command: {}".format(' '.join([quote(arg) for arg in sys.argv])),
            ]
            sns_message += message[1:]
            connection.publish(
                gene.config['sns']['topic'],
                "\n".join(sns_message),
                "Tile generation ({layer!s} - {role!s})".format(**{
                    'role': options.role,
                    'layer': gene.layer['name']
                })
            )


def daemonize():  # pragma: no cover
    try:
        pid = os.fork()
        if pid > 0:
            print("Daemonize with pid {}.".format(pid))
            sys.stderr.write(str(pid))
            # exit parent
            sys.exit(0)
    except OSError as e:
        exit("fork #1 failed: {} ({})\n".format(e.errno, e.strerror))


def main():
    parser = ArgumentParser(description='Used to generate the tiles', prog=sys.argv[0])
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
        "--local-process-number", default=None,
        help="The number of process that we run in parallel"
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
        exit('not authorised, authorised user is: {}.'.format(gene.config['generation']['authorised_user']))

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
            for layer in gene.config['generation'].get('default_layers', gene.layers.keys()):
                generate = Generate()
                generate.gene(options, gene, layer)
    finally:
        if gene.error_file is not None:
            gene.error_file.close()
