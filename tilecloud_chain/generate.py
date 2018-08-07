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
import time

import boto3
from c2cwsgiutils import stats
from tilecloud import TileCoord
from tilecloud.store.url import URLTileStore
from tilecloud.store.sqs import SQSTileStore, maybe_stop
from tilecloud.store.redis import RedisTileStore
from tilecloud.layout.wms import WMSTileLayout
from tilecloud.filter.logger import Logger

from tilecloud_chain import TileGeneration, HashDropper, HashLogger, TilesFileStore, \
    add_comon_options, parse_tilecoord, quote, Count, MultiTileStore, MultiAction, TimedTileStoreWrapper
from tilecloud_chain.format import size_format, duration_format, default_int
from tilecloud_chain.database_logger import DatabaseLoggerInit, DatabaseLogger

logger = logging.getLogger(__name__)


class Generate:
    _re_rm_xml_tag = re.compile('(<[^>]*>|\n)')

    def __init__(self, options, gene):
        self._count_metatiles = None
        self._count_metatiles_dropped = None
        self._count_tiles = None
        self._count_tiles_dropped = None
        self._count_tiles_stored = None
        self._queue_tilestore = None
        self._cache_tilestore = None
        self._options = options
        self._gene = gene

    def gene(self, layer=None):
        if self._options.role != 'slave' and not self._options.get_hash and not self._options.get_bbox:
            self._gene.init_layer(layer, self._options)

        self._generate_init()
        if self._options.role != 'slave':
            self._generate_queue(layer)
            if self._options.role != 'master':
                self._generate_tiles()
        else:
            self._generate_tiles()
        self.generate_consume()
        self.generate_resume(layer)

    def _generate_init(self):
        self._count_metatiles_dropped = Count()
        self._count_tiles = Count()
        self._count_tiles_dropped = Count()

        if self._options.role in ('master', 'slave'):
            if 'redis' in self._gene.config:
                # Create a Redis queue
                config = self._gene.config['redis']
                self._queue_tilestore = TimedTileStoreWrapper(
                    RedisTileStore(config['url'], name=config['queue'],
                                   stop_if_empty=not self._options.daemon),
                    stats_name='redis')
            else:
                # Create a SQS queue
                self._queue_tilestore = TimedTileStoreWrapper(
                    SQSTileStore(self._gene.get_sqs_queue(),
                                 on_empty=await_message if self._options.daemon else maybe_stop),
                    stats_name='SQS')  # pragma: no cover

        if self._options.role in ('local', 'slave'):
            self._cache_tilestore = self._gene.get_tilesstore(self._options.cache)

    def _generate_queue(self, layer):
        assert layer is not None

        if self._options.get_bbox:
            try:
                tilecoord = parse_tilecoord(self._options.get_bbox)
                print("Tile bounds: [{},{},{},{}]".format(
                    *default_int(layer['grid_ref']['obj'].extent(tilecoord))
                ))
                exit()
            except ValueError as e:  # pragma: no cover
                logger.error("Tile '%s' is not in the format 'z/x/y' or z/x/y:+n/+n", self._options.get_bbox,
                             exc_info=True)
                exit(1)

        if self._options.get_hash:
            self._options.role = 'hash'
            self._options.test = 1

        if self._options.tiles:
            self._gene.set_store(TilesFileStore(
                self._options.tiles, layer['name'], self._gene.get_all_dimensions(layer)
            ))

        elif self._options.role in ('local', 'master'):
            # Generate a stream of metatiles
            self._gene.init_tilecoords(layer)
            self._gene.add_geom_filter(layer)

        if self._options.role in ('local', 'master') and 'logging' in self._gene.config:
            self._gene.imap(DatabaseLoggerInit(
                self._gene.config['logging'],
                self._options is not None and self._options.daemon,
            ))

        if self._options.local_process_number is not None:  # pragma: no cover
            self._gene.add_local_process_filter()

        elif self._options.role == 'hash':
            try:
                z, x, y = (int(v) for v in self._options.get_hash.split('/'))
                if layer.get('meta'):
                    self._gene.set_tilecoords([TileCoord(z, x, y, layer['meta_size'])], layer)
                else:
                    self._gene.set_tilecoords([TileCoord(z, x, y)], layer)
            except ValueError as e:  # pragma: no cover
                exit(
                    "Tile '{}' is not in the format 'z/x/y'\n{}".format(
                        self._options.get_hash, repr(e))
                )

        # At this stage, the tilestream contains metatiles that intersect geometry
        self._gene.add_logger()

        self._count_metatiles = self._gene.counter()

        if self._options.role == 'master':  # pragma: no cover
            # Put the metatiles into the SQS or Redis queue
            self._gene.put(self._queue_tilestore)
            self._count_tiles = self._gene.counter()

    def _generate_tiles(self):
        if self._options.role == 'slave':
            # Get the metatiles from the SQS/Redis queue
            self._gene.set_store(self._queue_tilestore)  # pragma: no cover
            self._gene.ifilter(lambda tile: 'layer' in tile.metadata)
            self._count_metatiles = self._gene.counter()

        self._gene.get(TimedTileStoreWrapper(MultiTileStore({
            name: self._get_tilestore_for_layer(layer)
            for name, layer in self._gene.layers.items()
        }), stats_name='get'), 'Get tile')

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
        self._gene.imap(wrong_content_type_to_error)
        if self._options.role in ('local', 'slave') and 'logging' in self._gene.config:
            self._gene.imap(DatabaseLogger(
                self._gene.config['logging'],
                self._options is not None and self._options.daemon
            ))
            self._gene.add_error_filters(
                self._queue_tilestore
                if 'error_file' in self._gene.config['generation']
                else None
            )
        else:
            self._gene.add_error_filters()

        if self._options.role == 'hash':
            self._gene.imap(HashLogger('empty_metatile_detection'))
        elif self._options.role == 'hash':
            pass
        elif not self._options.near:
            droppers = {}
            for lname, layer in self._gene.layers.items():
                if 'empty_metatile_detection' in layer:
                    empty_tile = layer['empty_metatile_detection']
                    droppers[lname] = HashDropper(
                        empty_tile['size'], empty_tile['hash'],
                        store=self._cache_tilestore,
                        queue_store=self._queue_tilestore,
                        count=self._count_metatiles_dropped,
                    )
            if droppers:
                self._gene.imap(MultiAction(droppers))

        def add_elapsed_togenerate(metatile):
            if metatile is not None:
                metatile.elapsed_togenerate = metatile.tilecoord.n ** 2
                return True
            return False  # pragma: no cover
        self._gene.ifilter(add_elapsed_togenerate)

        # Split the metatile image into individual tiles
        self._gene.add_metatile_splitter()
        self._gene.imap(Logger(logger, logging.INFO, '%(tilecoord)s, %(formated_metadata)s'))

        self._gene.imap(self._count_tiles)

        self._gene.process(key='pre_hash_post_process')

        if self._options.role == 'hash':
            self._gene.imap(HashLogger('empty_tile_detection'))
        elif not self._options.near:
            droppers = {}
            for lname, layer in self._gene.layers.items():
                if 'empty_tile_detection' in layer:
                    empty_tile = layer['empty_tile_detection']
                    droppers[lname] = HashDropper(
                        empty_tile['size'], empty_tile['hash'], store=self._cache_tilestore,
                        queue_store=self._queue_tilestore,
                        count=self._count_tiles_dropped,
                    )
            if len(droppers) != 0:
                self._gene.imap(MultiAction(droppers))

        self._gene.process()

        if self._options.role in ('local', 'slave'):
            self._count_tiles_stored = self._gene.counter(size=True)

            if self._options.time:
                def log_size(tile):
                    sys.stdout.write('size: {}\n'.format(len(tile.data)))
                    return tile
                self._gene.imap(log_size)

            self._gene.ifilter(lambda tile: tile is not None)
            self._gene.put(self._cache_tilestore, "Store the tile")

        if self._options.role == 'slave':  # pragma: no cover
            def delete_from_store(tile):
                if hasattr(tile, 'metatile'):
                    tile.metatile.elapsed_togenerate -= 1
                    if tile.metatile.elapsed_togenerate == 0:
                        self._queue_tilestore.delete_one(tile.metatile)
                else:
                    self._queue_tilestore.delete_one(tile)
                return True
            self._gene.ifilter(delete_from_store)

        if self._options.role in ('local', 'slave') and 'logging' in self._gene.config:
            self._gene.imap(DatabaseLogger(
                self._gene.config['logging'],
                self._options is not None and self._options.daemon
            ))
        self._gene.add_error_filters()

    def generate_consume(self):
        if self._options.time is not None:
            options = self._options

            class LogTime:
                n = 0
                t1 = None

                def __call__(self, tile):
                    self.n += 1
                    if self.n == options.time:
                        self.t1 = datetime.now()
                    elif self.n == 2 * options.time:
                        t2 = datetime.now()
                        duration = (t2 - self.t1) / options.time
                        sys.stdout.write('time: {}\n'.format(
                            ((duration.days * 24 * 3600 + duration.seconds) * 1000000 + duration.microseconds)
                        ))
                    return tile
            self._gene.imap(LogTime())

            self._gene.consume(self._options.time * 3)
        else:
            self._gene.consume()

    def generate_resume(self, layer):
        if self._options.time is None:
            if layer is not None:
                all_dimensions = self._gene.get_all_dimensions(layer)
                message = [
                    "The tile generation of layer '{}{}' is finish".format(
                        layer['name'],
                        "" if (
                            (len(all_dimensions) == 1 and len(all_dimensions[0]) == 0) or
                            layer['type'] != 'wms'
                        )
                        else " ({})".format(
                            " - ".join([
                                ", ".join(
                                    ["=".join(d) for d in dimensions.items()]
                                )
                                for dimensions in all_dimensions
                            ])
                        )
                    ),
                ]
            else:
                message = [
                    "The tile generation is finish"
                ]
            if self._options.role == "master":  # pragma: no cover
                message.append("Nb of generated jobs: {}".format(self._count_tiles.nb))
            elif layer.get('meta') if layer is not None else self._options.role == "slave":
                message += [
                    "Nb generated metatiles: {}".format(self._count_metatiles.nb),
                    "Nb metatiles dropped: {}".format(self._count_metatiles_dropped.nb),
                ]

            if self._options.role != "master":
                message += [
                    "Nb generated tiles: {}".format(self._count_tiles.nb),
                    "Nb tiles dropped: {}".format(self._count_tiles_dropped.nb),
                ]
                if self._options.role in ('local', 'slave'):
                    message += [
                        "Nb tiles stored: {}".format(self._count_tiles_stored.nb),
                        "Nb tiles in error: {}".format(self._gene.error),
                        "Total time: {}".format(duration_format(self._gene.duration)),
                    ]
                    if self._count_tiles_stored.nb != 0:
                        message.append("Total size: {}".format(size_format(self._count_tiles_stored.size)))
                    if self._count_tiles.nb != 0:
                        message.append("Time per tile: {:0.0f} ms".format(
                            (self._gene.duration / self._count_tiles.nb * 1000).seconds)
                        )
                    if self._count_tiles_stored.nb != 0:
                        message.append("Size per tile: {:0.0f} o".format(
                            self._count_tiles_stored.size / self._count_tiles_stored.nb)
                        )

            if not self._options.quiet and self._options.role in ('local', 'slave', 'master') and message:
                print("\n".join(message) + "\n")

        if self._cache_tilestore is not None and hasattr(self._cache_tilestore, 'connection'):
            self._cache_tilestore.connection.close()

        if self._options.role != 'hash' and \
                self._options.time is None and \
                'sns' in self._gene.config:  # pragma: no cover
            if 'region' in self._gene.config['sns']:
                sns_client = boto3.client('sns', region_name=self._gene.config['sns']['region'])
            else:
                sns_client = boto3.client('sns')
            sns_message = [message[0]]
            sns_message += [
                "Layer: {}".format(layer['name'] if layer is not None else "(All layers)"),
                "Role: {}".format(self._options.role),
                "Host: {}".format(socket.getfqdn()),
                "Command: {}".format(' '.join([quote(arg) for arg in sys.argv])),
            ]
            sns_message += message[1:]
            sns_client.publish(TopicArn=self._gene.config['sns']['topic'], Message="\n".join(sns_message),
                               Subject="Tile generation ({layer} - {role})".format(
                                   role=self._options.role,
                                   layer=layer['name'] if layer is not None else "All layers"))

    def _get_tilestore_for_layer(self, layer):
        if layer['type'] == 'wms':
            params = layer['params'].copy()
            if 'STYLES' not in params:
                params['STYLES'] = ','.join(layer['wmts_style'] for l in layer['layers'].split(','))
            if layer['generate_salt']:
                params['SALT'] = str(random.randint(0, 999999))

            # Get the metatile image from the WMS server
            return URLTileStore(
                tilelayouts=(WMSTileLayout(
                    url=layer['url'],
                    layers=layer['layers'],
                    srs=layer['grid_ref']['srs'],
                    format=layer['mime_type'],
                    border=layer['meta_buffer'] if layer.get('meta', False) else 0,
                    tilegrid=self._gene.get_grid(layer)['obj'],
                    params=params,
                ),),
                headers=layer['headers'],
            )
        elif layer['type'] == 'mapnik':  # pragma: no cover
            try:
                from tilecloud.store.mapnik_ import MapnikTileStore
                from tilecloud_chain.mapnik_ import MapnikDropActionTileStore
            except ImportError:
                if 'CI' not in os.environ:  # pragma nocover
                    logger.error("Mapnik is not available", exc_info=True)
                return None

            grid = self._gene.get_grid(layer)
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
                    store=self._cache_tilestore,
                    queue_store=self._queue_tilestore,
                    count=[self._count_tiles, self._count_tiles_dropped],
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
        # Just sleep, the SQSTileStore will try again after that...
        time.sleep(10)
    except KeyboardInterrupt:
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
    stats.init_backends({})
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
        generate = Generate(options, gene)
        if options.role == 'slave':
            generate.gene()
        elif options.layer:
            generate.gene(gene.layers[options.layer])
        elif options.get_bbox:  # pragma: no cover
            exit("With --get-bbox option we needs to specify a layer")
        elif options.get_hash:  # pragma: no cover
            exit("With --get-hash option we needs to specify a layer")
        elif options.tiles:  # pragma: no cover
            exit("With --tiles option we needs to specify a layer")
        else:
            for layer in gene.config['generation'].get('default_layers', gene.layers.keys()):
                generate.gene(gene.layers[layer])
    finally:
        gene.close()


if __name__ == "__main__":
    main()
