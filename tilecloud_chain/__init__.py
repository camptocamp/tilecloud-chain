# -*- coding: utf-8 -*-

import sys
import os
import re
import logging
import yaml
import sqlite3
import tempfile
import subprocess
import pkgutil
from six.moves import map, filter
from six import binary_type
from six import BytesIO as StringIO
from math import ceil, sqrt
from hashlib import sha1
from fractions import Fraction
from datetime import datetime
from tilecloud import consume
from itertools import product

from tilecloud_chain.multitilestore import MultiTileStore

try:
    from PIL import Image
    Image  # suppress pyflakes warning
except:  # pragma: no cover
    import Image

import psycopg2
from shapely.wkb import loads as loads_wkb
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
from pykwalify.core import Core
from pykwalify.errors import SchemaError, NotSequenceError, NotMappingError

from tilecloud import Tile, BoundingPyramid, TileCoord, TileStore
from tilecloud.grid.free import FreeTileGrid
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.store.s3 import S3TileStore
from tilecloud.store.mbtiles import MBTilesTileStore
from tilecloud.store.filesystem import FilesystemTileStore
from tilecloud.layout.wmts import WMTSTileLayout
from tilecloud.filter.logger import Logger
from tilecloud.filter.error import LogErrors, MaximumConsecutiveErrors


logger = logging.getLogger('tilecloud_chain')


def add_comon_options(
        parser, tile_pyramid=True, no_geom=True,
        near=True, time=True, dimensions=False, cache=True):
    parser.add_argument(
        '-c', '--config', default='tilegeneration/config.yaml',
        help='path to the configuration file', metavar="FILE"
    )
    parser.add_argument(
        '-l', '--layer', metavar="NAME",
        help='the layer to generate'
    )
    if tile_pyramid:
        parser.add_argument(
            '-b', '--bbox', nargs=4, type=float, metavar=('MINX', 'MINY', 'MAXX', 'MAXY'),
            help='restrict to specified bounding box'
        )
        parser.add_argument(
            '-z', '--zoom',
            help='restrict to specified zoom level, or a zooms range (2-5), or a zooms list (2,4,5)'
        )
        parser.add_argument(
            '-t', '--test', type=int,
            help='test with generating N tiles, and add log messages', metavar="N"
        )
        if near:
            parser.add_argument(
                '--near', type=float, nargs=2, metavar=('X', 'Y'),
                help='This option is a good replacement of --bbox, to used with '
                '--time or --test and --zoom, implies --no-geom. '
                'It automatically measure a bbox around the X Y position that corresponds to the metatiles.'
            )
        if time:
            parser.add_argument(
                '--time', '--measure-generation-time',
                dest='time', metavar="N", type=int,
                help='Measure the generation time by creating N tiles to warm-up, '
                'N tile to do the measure and N tiles to slow-down'
            )
    if no_geom:
        parser.add_argument(
            '--no-geom', default=True, action="store_false", dest="geom",
            help="Don't the geometry available in the SQL"
        )
    if dimensions:
        parser.add_argument(
            '--dimensions', nargs='+', metavar='DIMENSION=VALUE', default=[],
            help='overwrite the dimensions values specified in the config file'
        )
    if cache:
        parser.add_argument(
            '--cache',
            dest='cache', metavar="NAME",
            help='The cache name to use'
        )
    parser.add_argument(
        '--logging-configuration-file',
        help='Configuration file for Python logging.'
    )
    parser.add_argument(
        '-q', '--quiet', default=False, action="store_true",
        help='Display only errors.'
    )
    parser.add_argument(
        '-v', '--verbose', default=False, action="store_true",
        help='Display info message.'
    )
    parser.add_argument(
        '-d', '--debug', default=False, action="store_true",
        help='Display debug message, and stop on first error.'
    )


def get_tile_matrix_identifier(grid, resolution=None, zoom=None):
    if grid is None or grid['matrix_identifier'] == 'zoom':
        return str(zoom)
    else:
        if resolution is None:
            resolution = grid['resolutions'][zoom]
        if int(resolution) == resolution:
            return str(int(resolution))
        else:
            return str(resolution).replace('.', '_')


class TileGeneration:

    def __init__(self, config_file, options=None, layer_name=None, base_config=None):
        if base_config is None:
            base_config = {}
        self.close_actions = []
        self.geom = None
        self.error = 0

        if options is not None:
            if not hasattr(options, 'bbox'):
                options.bbox = None
            if not hasattr(options, 'zoom'):
                options.zoom = None
            if not hasattr(options, 'test'):
                options.test = None
            if not hasattr(options, 'near'):
                options.near = None
            if not hasattr(options, 'time'):
                options.time = None
            if not hasattr(options, 'geom'):
                options.geom = True

        self._configure_logging(options, '%(levelname)s:%(name)s:%(funcName)s:%(message)s')

        with open(config_file) as f:
            self.config = {}
            self.config.update(base_config)
            self.config.update(yaml.load(f))
        self.options = options
        if 'defaults' in self.config:
            del self.config['defaults']
        # generate base structure
        if 'cost' in self.config:
            if 's3' not in self.config['cost']:
                self.config['cost']['s3'] = {}
            if 'cloudfront' not in self.config['cost']:
                self.config['cost']['cloudfront'] = {}
            if 'sqs' not in self.config['cost']:
                self.config['cost']['sqs'] = {}
        if 'generation' not in self.config:
            self.config['generation'] = {}
        for gname, grid in sorted(self.config.get('grids', {}).items()):
            if grid is not None:
                grid["name"] = gname
        for cname, cache in sorted(self.config.get('caches', {}).items()):
            if cache is not None:
                cache["name"] = cname
        for lname, layer in sorted(self.config.get('layers', {}).items()):
            if layer is not None:
                layer["name"] = lname

        c = Core(
            source_data=self.config,
            schema_data=yaml.load(pkgutil.get_data("tilecloud_chain", "schema.yaml")),
        )
        path_ = ''
        try:
            self.config = c.validate()

            for name, cache in self.config['caches'].items():
                if cache['type'] == 's3':
                    c = Core(
                        source_data=cache,
                        schema_data=yaml.load(pkgutil.get_data("tilecloud_chain", "schema-cache-s3.yaml")),
                    )
                    path_ = 'caches/{}'.format(name)
                    self.config['caches'][name] = c.validate()
            for name, layer in self.config['layers'].items():
                c = Core(
                    source_data=layer,
                    schema_data=yaml.load(pkgutil.get_data(
                        "tilecloud_chain",
                        "schema-layer-{}.yaml".format(layer['type'])
                    )),
                )
                path_ = 'layers/{}'.format(name)
                self.config['layers'][name] = c.validate()

        except SchemaError:
            logger.error("The config file '{}' is invalid.\n{}".format(
                config_file,
                "\n".join(sorted([
                    " - {}: {}".format(
                        os.path.join('/', path_, re.sub('^/', '', error.path)),
                        re.sub(" Path: '{path}'", '', error.msg).format(**error.__dict__)
                    )
                    for error in c.errors
                ]))
            ))
            exit(1)
        except NotSequenceError as e:  # pragma: no cover
            logger.error("The config file '{}' is invalid.\n - {}".format(
                config_file, e.msg
            ))
            exit(1)
        except NotMappingError as e:  # pragma: no cover
            logger.error("The config file '{}' is invalid.\n - {}".format(
                config_file, e.msg
            ))
            exit(1)

        error = False
        self.grids = self.config['grids']
        for gname, grid in sorted(self.grids.items()):
            if 'resolution_scale' in grid:
                scale = grid['resolution_scale']
                for r in grid['resolutions']:
                    if r * scale % 1 != 0.0:
                        logger.error(
                            "The resolution {} * resolution_scale {} is not an integer.".format(
                                r, scale
                            )
                        )
                        error = True
            else:
                grid['resolution_scale'] = self._resolution_scale(grid['resolutions'])

            srs = int(grid["srs"].split(":")[1])
            if 'proj4_literal' not in grid:
                if srs == 3857:  # pragma: no cover
                    grid['proj4_literal'] = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 ' \
                        '+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over'
                elif srs == 21781:
                    grid['proj4_literal'] = \
                        '+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 ' \
                        '+x_0=600000 +y_0=200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 ' \
                        '+units=m +no_defs'
                elif srs == 2056:  # pragma: no cover
                    grid['proj4_literal'] = \
                        '+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 ' \
                        '+x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 ' \
                        '+units=m +no_defs'
                else:  # pragma: no cover
                    grid['proj4_literal'] = '+init={}'.format(grid['srs'])

            scale = grid['resolution_scale']
            grid['obj'] = FreeTileGrid(
                resolutions=[int(r * scale) for r in grid['resolutions']],
                scale=scale,
                max_extent=grid['bbox'],
                tile_size=grid['tile_size']) if not error else None

        self.layers = self.config['layers']
        for lname, layer in sorted(self.layers.items()):
            layer['grid_ref'] = self.grids[layer['grid']] if not error else None
            self.layers[lname] = layer
            if 'geoms' not in layer:
                layer['geoms'] = []
            if 'params' not in layer and layer['type'] == 'wms':
                layer['params'] = {}
            if 'headers' not in layer and layer['type'] == 'wms':
                layer['headers'] = {
                    'Cache-Control': 'no-cache, no-store',
                    'Pragma': 'no-cache',
                }
            if 'dimensions' not in layer:
                layer['dimensions'] = []
            if layer['type'] == 'mapnik' and \
                    layer['output_format'] == 'grid' and \
                    layer.get('meta', False):  # pragma: no cover
                logger.error("The layer '{}' is of type Mapnik/Grid, that can't support matatiles.".format(
                    lname
                ))
                error = True

        self.caches = self.config['caches']

        if error:
            exit(1)

        if 'log_format' in self.config.get('generation', {}):
            self._configure_logging(options, self.config['generation']['log_format'])

        if options is not None and options.zoom is not None:
            error_message = (
                "The zoom argument '%s' has incorect format, "
                "it can be a single value, a range (3-9), a list of values (2,5,7)."
            ) % options.zoom
            if options.zoom.find('-') >= 0:
                r = options.zoom.split('-')
                if len(r) != 2:  # pragma: no cover
                    logger.error(error_message)
                    error = True
                try:
                    options.zoom = range(int(r[0]), int(r[1]) + 1)
                except ValueError:  # pragma: no cover
                    logger.error(error_message)
                    error = True
            elif options.zoom.find(',') >= 0:
                try:
                    options.zoom = [int(z) for z in options.zoom.split(',')]
                except ValueError:  # pragma: no cover
                    logger.error(error_message)
                    error = True
            else:
                try:
                    options.zoom = [int(options.zoom)]
                except ValueError:  # pragma: no cover
                    logger.error(error_message)
                    error = True

        if error:  # pragma: no cover
            exit(1)

        self.layer = None
        if layer_name and not error:
            self.set_layer(layer_name, options)

    def _primefactors(self, x):
        factorlist = []
        loop = 2
        while loop <= x:
            if x % loop == 0:
                x /= loop
                factorlist.append(loop)
            else:
                loop += 1
        return factorlist

    def _resolution_scale(self, resolutions):
        prime_fact = {}
        for resolution in resolutions:
            denominator = Fraction(str(resolution)).denominator
            prime_factors = self._primefactors(denominator)
            for factor in set(prime_factors):
                if factor not in prime_fact:
                    prime_fact[factor] = 0

                prime_fact[factor] = max(prime_fact[factor], len([f for f in prime_factors if f == factor]))

        result = 1
        for fact, nb in prime_fact.items():
            result *= fact ** nb
        return result

    def _configure_logging(self, options, format_):
        if os.environ.get('NOSE', 'FALSE') == 'TRUE':
            pass
        elif options is not None and options.logging_configuration_file:  # pragma: nocover
            logging.config.fileConfig(options.logging_configuration_file)
        else:  # pragma: nocover
            level = logging.WARNING
            other_level = logging.CRITICAL
            if options is not None and options.quiet:
                level = logging.ERROR
            elif options is not None and options.verbose:
                level = logging.INFO
            elif options is not None and options.debug:
                level = logging.DEBUG
                other_level = logging.INFO
            logging.config.dictConfig({
                'version': 1,
                'loggers': {
                    'tilecloud': {
                        'level': level,
                        'handlers': ['console'],
                    },
                    'tilecloud_chain': {
                        'level': level,
                        'handlers': ['console'],
                    },
                    'pykwalify': {
                        'level': other_level,
                        'handlers': ['console'],
                    },
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'default',
                        'stream': 'ext://sys.stdout',
                    },
                },
                'formatters': {
                    'default': {
                        'format': format_,
                    },
                },
            })

    def get_all_dimensions(self, layer=None):
        if layer is None:
            layer = self.layer
        options_dimensions = {}
        for opt_dim in self.options.dimensions:
            opt_dim = opt_dim.split('=')
            if len(opt_dim) != 2:  # pragma: no cover
                exit(
                    'the DIMENSIONS option should be like this '
                    'DATE=2013 VERSION=13.'
                )
            options_dimensions[opt_dim[0]] = opt_dim[1]

        all_dimensions = [
            [
                (dim['name'], d)
                for d in dim['generate']
            ]
            for dim in layer['dimensions']
            if dim['name'] not in options_dimensions
        ]
        all_dimensions += [[p] for p in options_dimensions.items()]
        all_dimensions = product(*all_dimensions)
        return [dict(d) for d in all_dimensions]

    def get_store(self, cache, layer, dimensions=None, read_only=False):
        # build layout
        if dimensions is None:  # pragma: no cover
            dimensions = {}
        grid = layer['grid_ref'] if 'grid_ref' in layer else None
        layout = WMTSTileLayout(
            layer=layer['name'],
            url=cache['folder'],
            style=layer['wmts_style'],
            format='.' + layer['extension'],
            dimensions=[
                (dimension['name'], dimensions[dimension['name']])
                for dimension in layer['dimensions']
            ],
            tile_matrix_set=layer['grid'],
            tile_matrix=lambda z: get_tile_matrix_identifier(grid, zoom=z),
            request_encoding='REST',
        )
        # store
        if cache['type'] == 's3':
            # on s3
            cache_tilestore = S3TileStore(cache['bucket'], layout,
                                          s3_host=cache.get('host'))  # pragma: no cover
        elif cache['type'] == 'mbtiles':
            # on mbtiles file
            filename = layout.filename(TileCoord(0, 0, 0)).replace(
                '/0/0/0', ''
            ) + '.mbtiles'
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            cache_tilestore = MBTilesTileStore(
                sqlite3.connect(filename),
                content_type=layer['mime_type'],
                tilecoord_in_topleft=True,
            )
        elif cache['type'] == 'bsddb':
            try:
                import bsddb3 as bsddb
            except:  # pragma: no cover
                import bsddb
            from tilecloud.store.bsddb import BSDDBTileStore

            # on bsddb file
            filename = layout.filename(TileCoord(0, 0, 0)).replace(
                '/0/0/0', ''
            ) + '.bsddb'
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            db = bsddb.hashopen(
                filename,
                # and os.path.exists(filename) to avoid error on non existing file
                'r' if read_only and os.path.exists(filename) else 'c'
            )

            class Close:
                def __call__(self):
                    self.db.close()

            ca = Close()
            ca.db = db
            self.close_actions.append(ca)

            cache_tilestore = BSDDBTileStore(
                db, content_type=layer['mime_type'],
            )
        elif cache['type'] == 'filesystem':
            # on filesystem
            cache_tilestore = FilesystemTileStore(
                layout,
                content_type=layer['mime_type'],
            )
        else:
            exit('unknown cache type: ' + cache['type'])  # pragma: no cover

        return cache_tilestore

    def set_layer(self, layer, options):
        self.create_log_tiles_error(layer)
        self.layer = self.layers[layer]

        if options.near is not None or (
                options.time is not None and 'bbox' in self.layer and options.zoom is not None
        ):  # pragma: no cover
            if options.zoom is None or len(options.zoom) != 1:  # pragma: no cover
                exit('Option --near needs the option --zoom with one value.')
            if not (options.time is not None or options.test is not None):  # pragma: no cover
                exit('Option --near needs the option --time or --test.')
            position = options.near if options.near is not None else [
                (self.layer['bbox'][0] + self.layer['bbox'][2]) / 2,
                (self.layer['bbox'][1] + self.layer['bbox'][3]) / 2,
            ]
            bbox = self.layer['grid_ref']['bbox']
            diff = [position[0] - bbox[0], position[1] - bbox[1]]
            resolution = self.layer['grid_ref']['resolutions'][options.zoom[0]]
            mt_to_m = self.layer['meta_size'] * self.layer['grid_ref']['tile_size'] * resolution
            mt = [float(d) / mt_to_m for d in diff]

            nb_tile = options.time * 3 if options.time is not None else options.test
            nb_mt = nb_tile / (self.layer['meta_size'] ** 2)
            nb_sqrt_mt = ceil(sqrt(nb_mt))

            mt_origin = [round(m - nb_sqrt_mt / 2) for m in mt]
            self.init_geom([
                bbox[0] + mt_origin[0] * mt_to_m,
                bbox[1] + mt_origin[1] * mt_to_m,
                bbox[0] + (mt_origin[0] + nb_sqrt_mt) * mt_to_m,
                bbox[1] + (mt_origin[1] + nb_sqrt_mt) * mt_to_m,
            ])
        elif options.bbox is not None:
            self.init_geom(options.bbox)
        elif 'bbox' in self.layer:
            self.init_geom(self.layer['bbox'])
        else:
            self.init_geom(self.layer['grid_ref']['bbox'])

    def get_grid(self, name=None):
        if name is None:
            name = self.layer['grid']

        return self.grids[name]

    def get_tilesstore(self, cache_name, dimensions):
        cache = self.caches[cache_name]
        cache_tilestore = MultiTileStore({
            lname: self.get_store(cache, layer, dimensions=dimensions)
            for lname, layer in self.layers.items()
        }, self.layer['name'] if self.layer else None)
        return cache_tilestore

    def get_sqs_queue(self):  # pragma: no cover
        if 'sqs' not in self.config:
            exit("The config hasn't any configured queue")
        connection = boto.sqs.connect_to_region(self.config['sqs']['region'])
        queue = connection.get_queue(self.config['sqs']['queue'])
        queue.set_message_class(JSONMessage)
        return queue

    def init_geom(self, extent=None):
        self.geoms = self.get_geoms(self.layer, extent)

    def get_geoms(self, layer, extent=None):
        if not hasattr(self, 'layers_geoms'):
            self.layers_geoms = {}
        if layer['name'] in self.layers_geoms:  # pragma: no cover
            # already build
            return self.layers_geoms[layer['name']]

        layer_geoms = {}
        self.layers_geoms[layer['name']] = layer_geoms
        if extent:
            geom = Polygon((
                (extent[0], extent[1]),
                (extent[0], extent[3]),
                (extent[2], extent[3]),
                (extent[2], extent[1]),
            ))
            for z, r in enumerate(layer['grid_ref']['resolutions']):
                layer_geoms[z] = geom

        if self.options is None or (
            self.options.near is None and self.options.geom
        ):
            for g in layer['geoms']:
                connection = psycopg2.connect(g['connection'])
                cursor = connection.cursor()
                sql = 'SELECT ST_AsBinary(geom) FROM (SELECT {}) AS g'.format(g['sql'])
                logger.info('Execute SQL: {}.'.format(sql))
                cursor.execute(sql)
                geoms = [loads_wkb(binary_type(r[0])) for r in cursor.fetchall()]
                geom = cascaded_union(geoms)
                if extent:
                    geom = geom.intersection(Polygon((
                        (extent[0], extent[1]),
                        (extent[0], extent[3]),
                        (extent[2], extent[3]),
                        (extent[2], extent[1]),
                    )))
                for z, r in enumerate(layer['grid_ref']['resolutions']):
                    if ('min_resolution' not in g or g['min_resolution'] <= r) and \
                            ('max_resolution' not in g or g['max_resolution'] >= r):
                        layer_geoms[z] = geom
                cursor.close()
                connection.close()
        return layer_geoms

    def add_local_process_filter(self):  # pragma: no cover
        self.ifilter(LocalProcessFilter(
            self.config["generation"]["number_process"],
            self.options.local_process_number
        ))

    def get_geoms_filter(self, layer, grid, geoms, queue_store=None):
        return IntersectGeometryFilter(
            grid=grid,
            geoms=geoms,
            queue_store=queue_store,
            px_buffer=(
                layer['px_buffer'] +
                layer['meta_buffer'] if layer.get('meta', False) else 0
            )
        )

    def add_geom_filter(self, queue_store=None):
        self.ifilter(self.get_geoms_filter(
            layer=self.layer,
            grid=self.get_grid(),
            geoms=self.geoms,
            queue_store=queue_store,
        ), "Intersect with geom")

    def add_logger(self):
        if not self.options.quiet and \
                not self.options.verbose and \
                not self.options.debug:
            def log_tiles(tile):
                variables = dict()
                variables.update(tile.__dict__)
                variables.update(tile.tilecoord.__dict__)
                sys.stdout.write("{tilecoord}          \r".format(**variables))
                sys.stdout.flush()
                return tile
            self.imap(log_tiles)
        elif self.options.verbose:
            self.imap(Logger(logger, logging.INFO, '%(tilecoord)s'))

    def add_metatile_splitter(self):
        class NullSplitter(TileStore):
            @staticmethod
            def get_one(tile):
                return tile

        splitters = {None: NullSplitter()}
        for lname, layer in self.layers.items():
            if layer.get('meta'):
                splitters[lname] = MetaTileSplitterTileStore(
                    layer['mime_type'],
                    layer['grid_ref']['tile_size'],
                    layer['meta_buffer'])

        store = MultiTileStore(splitters)

        if self.options.debug:
            def meta_get(tilestream):  # pragma: no cover
                for metatile in tilestream:
                    substream = store.get((metatile,))
                    for tile in substream:
                        if tile is not metatile:
                            tile.metatile = metatile
                            tile.metadata = metatile.metadata
                            if metatile.error:
                                tile.error = metatile.error
                            elif metatile.data is None:
                                tile.error = "Metatile data is empty"
                        yield tile
            self.tilestream = meta_get(self.tilestream)  # pragma: no cover
        else:
            def safe_get(tilestream):
                for metatile in tilestream:
                    try:
                        substream = store.get((metatile,))
                        for tile in substream:
                            if tile is not metatile:
                                tile.metatile = metatile
                                tile.metadata = metatile.metadata
                                if metatile.error:
                                    tile.error = metatile.error
                                elif metatile.data is None:
                                    tile.error = "Metatile data is empty"
                            yield tile
                    except GeneratorExit as e:
                        raise e
            self.tilestream = safe_get(self.tilestream)

    error_file = None

    def create_log_tiles_error(self, layer):
        if 'error_file' in self.config['generation']:
            now = datetime.now()
            time = now.strftime('%d-%m-%Y %H:%M:%S')
            self.error_file = open(
                self.config['generation']['error_file'].format(
                    layer=layer, datetime=now
                ),
                'a'
            )
            self.error_file.write("# [{}] Start the layer '{}' generation\n".format(time, layer))

    def log_tiles_error(self, tilecoord=None, message=None):
        if 'error_file' in self.config['generation']:
            time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            if self.error_file is None:  # pragma: no cover
                raise "Missing error file"

            tilecoord = "" if tilecoord is None else "{} ".format(tilecoord)
            message = "" if message is None else " {}".format(message)

            self.error_file.write('{}# [{}]{}\n'.format(tilecoord, time, message.replace('\n', ' ')))

    def add_error_filters(self):
        self.imap(LogErrors(
            logger, logging.ERROR,
            "Error in tile: %(tilecoord)s, %(error)r"
        ))

        if 'error_file' in self.config['generation']:

            def do(tile):
                if tile and tile.error:
                    self.log_tiles_error(tilecoord=tile.tilecoord, message=repr(tile.error))
                return tile
            self.imap(do)
        if self.config['generation']['maxconsecutive_errors'] > 0:
            self.tilestream = map(MaximumConsecutiveErrors(
                self.config['generation']['maxconsecutive_errors']), self.tilestream)

        def drop_count(tile):
            if tile and tile.error:
                self.error += 1
                return None
            return tile
        self.ifilter(drop_count)

    def init_tilecoords(self):
        resolutions = self.layer['grid_ref']['resolutions']

        if self.options.time is not None and self.options.zoom is None:
            if 'min_resolution_seed' in self.layer:  # pragma: no cover
                self.options.zoom = [resolutions.index(
                    self.layer['min_resolution_seed']
                )]
            else:
                self.options.zoom = [len(resolutions) - 1]

        if self.options.zoom is not None:
            zoom_max = len(resolutions) - 1
            for zoom in self.options.zoom:
                if zoom > zoom_max:
                    logger.warn(
                        "zoom %i is greater than the maximum zoom %i"
                        " of grid %s of layer %s, ignored." % (
                            zoom, zoom_max, self.layer['grid'], self.layer['name']
                        )
                    )
            self.options.zoom = [z for z in self.options.zoom if z <= zoom_max]

        if 'min_resolution_seed' in self.layer:
            if self.options.zoom is None:
                self.options.zoom = []
                for z, resolution in enumerate(resolutions):
                    if resolution >= self.layer['min_resolution_seed']:
                        self.options.zoom.append(z)
            else:
                for zoom in self.options.zoom:
                    resolution = resolutions[zoom]
                    if resolution < self.layer['min_resolution_seed']:
                        logger.warn(
                            "zoom %i corresponds to resolution %s is smaller"
                            " than the 'min_resolution_seed' %s of layer %s, ignored." %
                            (
                                zoom, resolution, self.layer['min_resolution_seed'], self.layer['name']
                            )
                        )
                self.options.zoom = [
                    z for z in self.options.zoom if
                    resolutions[z] >= self.layer['min_resolution_seed']
                ]

        if self.options.zoom is None:
            self.options.zoom = [z for z, r in enumerate(resolutions)]

        # fill the bounding pyramid
        tilegrid = self.layer['grid_ref']['obj']
        bounding_pyramid = BoundingPyramid(tilegrid=tilegrid)
        for zoom in self.options.zoom:
            if zoom in self.geoms:
                extent = self.geoms[zoom].bounds

                if len(extent) == 0:
                    logger.warn("bounds empty for zoom {}".format(zoom))
                else:
                    minx, miny, maxx, maxy = extent
                    px_buffer = self.layer['px_buffer']
                    m_buffer = px_buffer * resolutions[zoom]
                    minx -= m_buffer
                    miny -= m_buffer
                    maxx += m_buffer
                    maxy += m_buffer
                    bounding_pyramid.add(tilegrid.tilecoord(
                        zoom,
                        max(minx, tilegrid.max_extent[0]),
                        max(miny, tilegrid.max_extent[1]),
                    ))
                    bounding_pyramid.add(tilegrid.tilecoord(
                        zoom,
                        min(maxx, tilegrid.max_extent[2]),
                        min(maxy, tilegrid.max_extent[3]),
                    ))

        if self.layer.get('meta', False):
            self.set_tilecoords(bounding_pyramid.metatilecoords(self.layer['meta_size']))
        else:
            self.set_tilecoords(bounding_pyramid)

    def set_tilecoords(self, tilecoords):
        self.tilestream = (
            Tile(tilecoord, layer=self.layer['name']) for tilecoord in tilecoords
        )

    def set_store(self, store):  # pragma: no cover
        self.tilestream = store.list()

    def counter(self, size=False):
        count = CountSize() if size else Count()
        self.imap(count)
        return count

    def process(self, name=None, key='post_process'):
        processes = {}
        for lname, layer in self.layers.items():
            name_ = name
            if name_ is None:
                name_ = layer.get(key)
            if name_ is not None:
                processes[lname] = Process(self.config['process'][name_], self.options)
        if processes:
            self.imap(MultiAction(processes))

    def get(self, store, time_message=None):
        if self.options.debug:
            self.tilestream = store.get(self.tilestream)  # pragma: no cover
        else:
            def safe_get(tile):
                try:
                    n = datetime.now()
                    t = store.get_one(tile)
                    if time_message:
                        logger.info("{} in {}".format(time_message, str(datetime.now() - n)))
                    return t
                except GeneratorExit as e:  # pragma: no cover
                    raise e
                except SystemExit as e:  # pragma: no cover
                    raise e
                except KeyboardInterrupt:  # pragma: no cover
                    exit("User interrupt")
                except:  # pragma: no cover
                    tile.error = sys.exc_info()[1]
                    return tile
            self.tilestream = map(safe_get, filter(None, self.tilestream))

    def put(self, store, time_message=None):
        if self.options.debug:
            self.tilestream = store.put(self.tilestream)  # pragma: no cover
        else:
            def safe_put(tile):
                try:
                    n = datetime.now()
                    t = store.put_one(tile)
                    if time_message:
                        logger.info("{} in {}".format(time_message, str(datetime.now() - n)))
                    return t
                except GeneratorExit as e:  # pragma: no cover
                    raise e
                except SystemExit as e:  # pragma: no cover
                    raise e
                except KeyboardInterrupt:  # pragma: no cover
                    exit("User interrupt")
                except:  # pragma: no cover
                    tile.error = sys.exc_info()[1]
                    return tile
            self.tilestream = map(safe_put, filter(None, self.tilestream))

    def delete(self, store, time_message=None):  # pragma: no cover
        if self.options.debug:
            self.tilestream = store.delete(self.tilestream)
        else:
            def safe_delete(tile):
                try:
                    n = datetime.now()
                    t = store.delete_one(tile)
                    if time_message:
                        logger.info("{} in {}".format(time_message, str(datetime.now() - n)))
                    return t
                except GeneratorExit as e:  # pragma: no cover
                    raise e
                except SystemExit as e:  # pragma: no cover
                    raise e
                except KeyboardInterrupt:  # pragma: no cover
                    exit("User interrupt")
                except:  # pragma: no cover
                    tile.error = sys.exc_info()[1]
                    return tile
            self.tilestream = map(safe_delete, filter(None, self.tilestream))

    def imap(self, tile_filter, time_message=None):
        if self.options.debug:
            self.tilestream = map(tile_filter, self.tilestream)  # pragma: no cover
        else:
            def safe_imap(tile):
                try:
                    n = datetime.now()
                    t = tile_filter(tile)
                    if time_message:  # pragma: no cover
                        logger.info("{} in {}".format(time_message, str(datetime.now() - n)))
                    return t
                except GeneratorExit as e:  # pragma: no cover
                    raise e
                except SystemExit as e:  # pragma: no cover
                    raise e
                except KeyboardInterrupt:  # pragma: no cover
                    exit("User interrupt")
                except:  # pragma: no cover
                    tile.error = sys.exc_info()[1]
                    return tile
            self.tilestream = map(safe_imap, filter(None, self.tilestream))

    def ifilter(self, tile_filter, time_message=None):
        if self.options.debug:
            self.tilestream = filter(tile_filter, self.tilestream)  # pragma: no cover
        else:
            def safe_filter(tile):
                if tile:
                    try:
                        n = datetime.now()
                        t = tile_filter(tile)
                        if time_message:
                            logger.debug("{} in {}".format(time_message, str(datetime.now() - n)))
                        return t
                    except GeneratorExit as e:  # pragma: no cover
                        raise e
                    except SystemExit as e:  # pragma: no cover
                        raise e
                    except KeyboardInterrupt:  # pragma: no cover
                        exit("User interrupt")
                    except:  # pragma: no cover
                        tile.error = sys.exc_info()[1]
                        return tile
            self.tilestream = filter(safe_filter, self.tilestream)

    def consume(self, test=None):
        if test is None:
            test = self.options.test
        start = datetime.now()
        consume(self.tilestream, test)
        self.duration = datetime.now() - start
        for ca in self.close_actions:
            ca()


class Count:

    def __init__(self):
        self.nb = 0

    def __call__(self, tile=None):
        self.nb += 1
        return tile


class CountSize:

    def __init__(self):
        self.nb = 0
        self.size = 0

    def __call__(self, tile=None):
        if tile and tile.data:
            self.nb += 1
            self.size += len(tile.data)
        return tile


class HashDropper:
    """
    Create a filter to remove the tiles data where they have
    the specified size and hash.

    Used to drop the empty tiles.

    The ``store`` is used to delete the empty tiles.
    """

    def __init__(self, size, sha1code, store=None, queue_store=None, count=None):
        self.size = size
        self.sha1code = sha1code
        self.store = store
        self.queue_store = queue_store
        self.count = count

    def __call__(self, tile):
        if len(tile.data) != self.size or \
                sha1(tile.data).hexdigest() != self.sha1code:
            return tile
        else:
            if self.store is not None:
                if tile.tilecoord.n != 1:
                    for tilecoord in tile.tilecoord:
                        self.store.delete_one(Tile(tilecoord))
                else:
                    self.store.delete_one(tile)
            logger.info("The tile {} is dropped".format(str(tile.tilecoord)))
            if hasattr(tile, 'metatile'):
                tile.metatile.elapsed_togenerate -= 1
                if tile.metatile.elapsed_togenerate == 0 and self.queue_store is not None:
                    self.queue_store.delete_one(tile.metatile)  # pragma: no cover
            elif self.queue_store is not None:  # pragma: no cover
                self.queue_store.delete_one(tile)

            if self.count:
                self.count()

            return None


class MultiAction:
    """
    Used to perform an action based on the tile's layer name. E.g a HashDropper or Process
    """

    def __init__(self, actions):
        self.actions = actions

    def __call__(self, tile):
        layer = tile.metadata.get('layer')
        action = self.actions.get(layer, self.noop)
        return action(tile)

    @staticmethod
    def noop(tile):
        return tile


class HashLogger:
    """
    Log the tile size and hash.
    """

    def __init__(self, block):
        self.block = block

    def __call__(self, tile):
        ref = None
        try:
            image = Image.open(StringIO(tile.data))
        except IOError as e:  # pragma: no cover
            logger.error(tile.data)
            raise e
        for px in image.getdata():
            if ref is None:
                ref = px
            elif px != ref:
                exit("Error: image is not uniform.")

        print("""Tile: {}
    {}:
        size: {}
        hash: {}""".format(str(tile.tilecoord), self.block, len(tile.data), sha1(tile.data).hexdigest()))
        return tile


class LocalProcessFilter:  # pragma: no cover

    def __init__(self, nb_process, process_nb):
        self.nb_process = nb_process
        self.process_nb = int(process_nb)

    def filter(self, tilecoord):
        nb = tilecoord.z + tilecoord.x / tilecoord.n + tilecoord.y / tilecoord.n
        return nb % self.nb_process == self.process_nb

    def __call__(self, tile):
        return tile if self.filter(tile.tilecoord) else None


class IntersectGeometryFilter:

    def __init__(self, grid, geoms=None, queue_store=None, px_buffer=0):
        self.grid = grid
        self.geoms = geoms
        self.queue_store = queue_store
        self.px_buffer = px_buffer

    def filter_tilecoord(self, tilecoord):
        return self.bbox_polygon(
            self.grid['obj'].extent(
                tilecoord,
                self.grid['resolutions'][tilecoord.z] * self.px_buffer
            )
        ).intersects(self.geoms[tilecoord.z])

    def __call__(self, tile):
        return tile if self.filter_tilecoord(tile.tilecoord) else None

    def bbox_polygon(self, bbox):
        return Polygon((
            (bbox[0], bbox[1]),
            (bbox[0], bbox[3]),
            (bbox[2], bbox[3]),
            (bbox[2], bbox[1])
        ))


class DropEmpty:
    """
    Create a filter for dropping all tiles with errors.
    """

    def __init__(self, gene):
        self.gene = gene

    def __call__(self, tile):
        if not tile or not tile.data:  # pragma: no cover
            logger.error("The tile: {tilecoord!s} is empty".format(**{
                'tilecoord': tile.tilecoord if tile else 'not defined'
            }))
            if 'error_file' in self.gene.config['generation'] and tile:
                self.gene.log_tiles_error(tilecoord=tile.tilecoord, message='The tile is empty')
            return None
        else:
            return tile


def quote(arg):
    if ' ' in arg:
        if "'" in arg:
            if '"' in arg:
                return "'{}'".format(arg.replace("'", "\\'"))
            else:
                return '"{}"'.format(arg)
        else:
            return "'{}'".format(arg)
    elif arg == '':
        return "''"
    else:
        return arg


def parse_tilecoord(string_representation):
    parts = string_representation.split(':')
    coords = [int(v) for v in parts[0].split('/')]
    if len(coords) != 3:  # pragma: no cover
        raise ValueError("Wrong number of coordinates")
    z, x, y = coords
    if len(parts) == 1:
        tilecoord = TileCoord(z, x, y)
    elif len(parts) == 2:
        meta = parts[1].split('/')
        if len(meta) != 2:  # pragma: no cover
            raise ValueError("No one '/' in meta coordinates")
        tilecoord = TileCoord(z, x, y, int(meta[0]))
    else:  # pragma: no cover
        raise ValueError("More than on ':' in the tilecoord")
    return tilecoord


class Process:
    def __init__(self, config, options):
        self.config = config
        self.options = options

    def __call__(self, tile):
        if tile and tile.data:
            fd_in, name_in = tempfile.mkstemp()
            with open(name_in, 'wb') as file_in:
                file_in.write(tile.data)

            for cmd in self.config:
                args = []
                if not self.options.verbose and \
                        not self.options.debug and \
                        not self.options.quiet and \
                        'default' in cmd['arg']:
                    args.append(cmd['arg']['default'])
                if self.options.verbose and 'verbose' in cmd['arg']:
                    args.append(cmd['arg']['verbose'])
                if self.options.debug and 'debug' in cmd['arg']:
                    args.append(cmd['arg']['debug'])
                if self.options.quiet and 'quiet' in cmd['arg']:
                    args.append(cmd['arg']['quiet'])

                if cmd['need_out']:
                    fd_out, name_out = tempfile.mkstemp()
                    os.unlink(name_out)
                else:  # pragma: no cover
                    name_out = name_in

                command = cmd['cmd'] % {
                    'in': name_in,
                    'out': name_out,
                    'args': ' '.join(args),
                    'x': tile.tilecoord.x,
                    'y': tile.tilecoord.y,
                    'z': tile.tilecoord.z
                }
                logger.info('process: {}'.format(command))
                code = subprocess.call(command, shell=True)
                if code != 0:  # pragma: no cover
                    tile.error = "Command '%s' on tile %s " \
                        "return error code %i" % \
                        (command, tile.tilecoord, code)
                    tile.data = None
                    return tile

                if cmd['need_out']:
                    os.close(fd_in)
                    name_in = name_out
                    fd_in = fd_out

            with open(name_in, 'rb') as file_out:
                tile.data = file_out.read()
            os.close(fd_in)

        return tile


class TilesFileStore:
    def __init__(self, tiles_file, layer=None):
        self.tiles_file = open(tiles_file)
        self.layer = layer

    def list(self):
        while True:
            line = self.tiles_file.readline()
            if not line:
                return
            line = line.split('#')[0].strip()
            if line != '':
                try:
                    yield Tile(parse_tilecoord(line), layer=self.layer)
                except ValueError as e:  # pragma: no cover
                    logger.error("A tile '{}' is not in the format 'z/x/y' or z/x/y:+n/+n\n{1!r}".format(line, e))
