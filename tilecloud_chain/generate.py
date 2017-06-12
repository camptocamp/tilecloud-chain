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
from tilecloud.store.sqs import SQSTileStore, maybe_stop
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, TilesFileStore, \
    add_comon_options, parse_tilecoord, quote, Count, MultiTileStore, MultiAction
from tilecloud_chain.format import size_format, duration_format, default_int
from tilecloud_chain.database_logger import DatabaseLoggerInit, DatabaseLogger

logger = logging.getLogger(__name__)


class Generate:
    _re_rm_xml_tag = re.compile('(<[^>]*>|\n)')

    def gene(self, options, gene, layer=None):
        if options.role == 'slave':
            pass
        elif options.get_hash or options.get_bbox:
            gene.layer = gene.layers[layer]
        else:
            gene.set_layer(layer, options)

        if options.role in ('local', 'master', 'hash'):
            all_dimensions = gene.get_all_dimensions()

            if len(all_dimensions) == 0:  # pragma: no cover
                self._gene(options, gene)
            else:
                for dimensions in all_dimensions:
                    self._gene(options, gene, dimensions)
        else:  # pragma: no cover
            self._gene(options, gene)

    def _gene(self, options, gene, dimensions=None):
        if dimensions is None:  # pragma: no cover
            dimensions = {}
        self.dimensions = dimensions
        self.count_metatiles = None
        self.count_metatiles_dropped = Count()
        self.count_tiles = Count()
        self.count_tiles_dropped = Count()
        self.count_tiles_stored = None
        self.sqs_tilestore = None
        self.cache_tilestore = None

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

        if options.role in ('master', 'slave'):
            # Create SQS queue
            self.sqs_tilestore = SQSTileStore(
                gene.get_sqs_queue(), on_empty=await_message if options.daemon else maybe_stop)  # pragma: no cover

        if options.role in ('local', 'slave'):
            self.cache_tilestore = gene.get_tilesstore(options.cache, dimensions)

        if options.tiles:
            gene.set_store(TilesFileStore(options.tiles, options.layer))

        elif options.role in ('local', 'master'):
            # Generate a stream of metatiles
            gene.init_tilecoords()
            gene.add_geom_filter()

        if options.role in ('local', 'master') and 'logging' in gene.config:
            gene.imap(DatabaseLoggerInit(gene.config['logging'], options is not None and options.daemon))

        if options.local_process_number is not None:  # pragma: no cover
            gene.add_local_process_filter()

        elif options.role == 'slave':
            # Get the metatiles from the SQS queue
            gene.set_store(self.sqs_tilestore)  # pragma: no cover

        elif options.role == 'hash':
            try:
                z, x, y = (int(v) for v in options.get_hash.split('/'))
                if gene.layer.get('meta'):
                    gene.set_tilecoords([TileCoord(z, x, y, gene.layer['meta_size'])])
                else:
                    gene.set_tilecoords([TileCoord(z, x, y)])
            except ValueError as e:  # pragma: no cover
                exit(
                    "Tile '{}' is not in the format 'z/x/y'\n{1!r}".format(options.get_hash, e)
                )

        # At this stage, the tilestream contains metatiles that intersect geometry
        gene.add_logger()

        self.count_metatiles = gene.counter()

        if options.role == 'master':  # pragma: no cover
            # Put the metatiles into the SQS queue
            gene.put(self.sqs_tilestore)
            self.count_tiles = gene.counter()

        elif options.role in ('local', 'slave', 'hash'):
            gene.get(MultiTileStore({
                name: self._get_tilestore_for_layer(layer, gene)
                for name, layer in gene.layers.items()
            }), 'Get tile')

            def wrong_content_type_to_error(tile):
                if tile is not None and tile.content_type is not None \
                        and tile.content_type.find("image/") != 0:
                    if tile.content_type.find("application/vnd.ogc.se_xml") == 0:
                        tile.error = "WMS server error: {}".format((
                            self._re_rm_xml_tag.sub(
                                '', tile.error
                            )
                        ))
                    else:  # pragma: no cover
                        tile.error = "{} is not an image format, error: {}".format(
                            tile.content_type,
                            tile.error
                        )
                return tile
            gene.imap(wrong_content_type_to_error)
            gene.add_error_filters()

            if options.role == 'hash':
                if gene.layer.get('meta', False):
                    gene.imap(HashLogger('empty_metatile_detection'))
            elif not options.near:
                droppers = {}
                for lname, layer in gene.layers.items():
                    if 'empty_metatile_detection' in layer:
                        empty_tile = layer['empty_metatile_detection']
                        droppers[lname] = HashDropper(
                            empty_tile['size'], empty_tile['hash'], store=self.cache_tilestore,
                            queue_store=self.sqs_tilestore,
                            count=self.count_metatiles_dropped,
                        )
                if droppers:
                    gene.imap(MultiAction(droppers))

            def add_elapsed_togenerate(metatile):
                if metatile is not None:
                    metatile.elapsed_togenerate = metatile.tilecoord.n ** 2
                    return True
                return False  # pragma: no cover
            gene.ifilter(add_elapsed_togenerate)

            # Split the metatile image into individual tiles
            gene.add_metatile_splitter()
            gene.imap(Logger(logger, logging.INFO, '%(tilecoord)s'))

            gene.imap(self.count_tiles)

            gene.process(key='pre_hash_post_process')

            if options.role == 'hash':
                gene.imap(HashLogger('empty_tile_detection'))
            elif not options.near:
                droppers = {}
                for lname, layer in gene.layers.items():
                    if 'empty_tile_detection' in layer:
                        empty_tile = layer['empty_tile_detection']
                        droppers[lname] = HashDropper(
                            empty_tile['size'], empty_tile['hash'], store=self.cache_tilestore,
                            queue_store=self.sqs_tilestore,
                            count=self.count_tiles_dropped,
                        )
                if droppers:
                    gene.imap(MultiAction(droppers))

            gene.process()
        else:  # pragma: no cover
            self.count_tiles = gene.counter()

        if options.role in ('local', 'slave'):
            self.count_tiles_stored = gene.counter(size=True)

            if options.time:
                def log_size(tile):
                    sys.stdout.write('size: {}\n'.format(len(tile.data)))
                    return tile
                gene.imap(log_size)

            gene.put(self.cache_tilestore, "Store the tile")

        if options.generated_tiles_file:  # pragma: no cover
            generated_tiles_file = open(options.generated_tiles_file, 'a')

            def do(tile):
                generated_tiles_file.write('{}\n'.format(tile.tilecoord))
                return tile
            gene.imap(do)

        if options.role == 'slave':  # pragma: no cover
            def delete_from_store(tile):
                if hasattr(tile, 'metatile'):
                    tile.metatile.elapsed_togenerate -= 1
                    if tile.metatile.elapsed_togenerate == 0:
                        self.sqs_tilestore.delete_one(tile.metatile)
                else:
                    self.sqs_tilestore.delete_one(tile)
                return True
            gene.ifilter(delete_from_store)

        if options.role in ('local', 'slave') and 'logging' in gene.config:
            gene.imap(DatabaseLogger(gene.config['logging'], options is not None and options.daemon))
        gene.add_error_filters()

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

            if gene.layer is not None:
                message = [
                    "The tile generation of layer '{}{}' is finish".format(
                        gene.layer['name'],
                        "" if len(dimensions) == 0 or gene.layer['type'] != 'wms'
                        else " ({})".format(", ".join(["=".join(d) for d in dimensions.items()]))
                    ),
                ]
                if options.role == "master":  # pragma: no cover
                    message.append("Nb of generated jobs: {}".format(self.count_tiles.nb))
                else:
                    if gene.layer.get('meta'):
                        message += [
                            "Nb generated metatiles: {}".format(self.count_metatiles.nb),
                            "Nb metatiles dropped: {}".format(self.count_metatiles_dropped.nb),
                        ]
            else:
                message = [
                    "The tile generation is finish"
                ]

            if options.role != "master":
                message += [
                    "Nb generated tiles: {}".format(self.count_tiles.nb),
                    "Nb tiles dropped: {}".format(self.count_tiles_dropped.nb),
                ]
                if options.role in ('local', 'slave'):
                    message += [
                        "Nb tiles stored: {}".format(self.count_tiles_stored.nb),
                        "Nb tiles in error: {}".format(gene.error),
                        "Total time: {}".format(duration_format(gene.duration)),
                    ]
                    if self.count_tiles_stored.nb != 0:
                        message.append("Total size: {}".format(size_format(self.count_tiles_stored.size)))
                    if self.count_tiles.nb != 0:
                        message.append("Time per tile: {:0.0f} ms".format(
                            (gene.duration / self.count_tiles.nb * 1000).seconds)
                        )
                    if self.count_tiles_stored.nb != 0:
                        message.append("Size per tile: {:0.0f} o".format(
                            self.count_tiles_stored.size / self.count_tiles_stored.nb)
                        )

            if not options.quiet and options.role in ('local', 'slave'):
                print("\n".join(message) + "\n")

        if self.cache_tilestore is not None and hasattr(self.cache_tilestore, 'connection'):
            self.cache_tilestore.connection.close()

        if options.role != 'hash' and options.time is None and 'sns' in gene.config:  # pragma: no cover
            if 'region' in gene.config['sns']:
                connection = sns.connect_to_region(gene.config['sns']['region'])
            else:
                connection = boto.connect_sns()
            sns_message = [message[0]]
            sns_message += [
                "Layer: {}".format(gene.layer['name'] if gene.layer is not None else "(All layers)"),
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
                    'layer': gene.layer['name'] if gene.layer is not None else "All layers"
                })
            )

    def _get_tilestore_for_layer(self, layer, gene):
        if layer['type'] == 'wms':
            params = layer['params'].copy()
            if 'STYLES' not in params:
                params['STYLES'] = ','.join(layer['wmts_style'] for l in layer['layers'].split(','))
            if layer['generate_salt']:
                params['SALT'] = str(random.randint(0, 999999))
            params.update(self.dimensions)

            # Get the metatile image from the WMS server
            return URLTileStore(
                tilelayouts=(WMSTileLayout(
                    url=layer['url'],
                    layers=layer['layers'],
                    srs=layer['grid_ref']['srs'],
                    format=layer['mime_type'],
                    border=layer['meta_buffer'] if layer.get('meta') else 0,
                    tilegrid=gene.get_grid(layer['grid'])['obj'],
                    params=params,
                ),),
                headers=layer['headers'],
            )
        elif layer['type'] == 'mapnik':  # pragma: no cover
            try:
                from tilecloud.store.mapnik_ import MapnikTileStore
                from tilecloud_chain.mapnik_ import MapnikDropActionTileStore
            except ImportError:
                if 'TRAVIS' not in os.environ:  # pragma nocover
                    logger.error("Mapnik is not available")
                return None

            grid = gene.get_grid(layer['grid'])
            if layer['output_format'] == 'grid':
                return MapnikDropActionTileStore(
                    tilegrid=grid['obj'],
                    mapfile=layer['mapfile'],
                    image_buffer=layer['meta_buffer'] if layer.get('meta') else 0,
                    data_buffer=layer['data_buffer'],
                    output_format=layer['output_format'],
                    resolution=layer['resolution'],
                    layers_fields=layer['layers_fields'],
                    drop_empty_utfgrid=layer['drop_empty_utfgrid'],
                    store=self.cache_tilestore,
                    queue_store=self.sqs_tilestore,
                    count=[self.count_tiles, self.count_tiles_dropped],
                    proj4_literal=grid['proj4_literal'],
                )
            else:
                return MapnikTileStore(
                    tilegrid=grid['obj'],
                    mapfile=layer['mapfile'],
                    image_buffer=layer['meta_buffer'] if layer.get('meta') else 0,
                    data_buffer=layer['data_buffer'],
                    output_format=layer['output_format'],
                    proj4_literal=grid['proj4_literal'],
                )


def await_message(queue):  # pragma: no cover
    try:
        while queue.read(visibility_timeout=0, wait_time_seconds=20) is None:
            pass
    except (Exception, KeyboardInterrupt):
        raise StopIteration


def detach():  # pragma: no cover
    try:
        pid = os.fork()
        if pid > 0:
            print("Detached with pid {}.".format(pid))
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
        '--detach', default=False, action="store_true",
        help='run detached from the terminal'
    )
    parser.add_argument(
        '--daemon', default=False, action="store_true",
        help='run continuously as a daemon'
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

    if options.detach:
        detach()  # pragma: no cover

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
        if options.role == 'slave':
            generate = Generate()
            generate.gene(options, gene)
        elif (options.layer):
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
