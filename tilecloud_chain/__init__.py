# -*- coding: utf-8 -*-

import sys
import os
import re
import logging
import logging.config
import yaml
import sqlite3
import tempfile
import subprocess
import pkgutil
import traceback
import time
from six.moves import map, filter
from six import binary_type
from six import BytesIO as StringIO
from math import ceil, sqrt
from hashlib import sha1
from fractions import Fraction
from datetime import datetime
from itertools import product

from tilecloud_chain.multitilestore import MultiTileStore
from tilecloud_chain.timedtilestore import TimedTileStoreWrapper

from PIL import Image

import psycopg2
from shapely.wkb import loads as loads_wkb
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
import boto3
from pykwalify.core import Core
from pykwalify.errors import SchemaError, NotSequenceError, NotMappingError
from c2cwsgiutils import stats, sentry

from tilecloud import Tile, BoundingPyramid, TileCoord, TileStore, consume
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
        '-c', '--config', default=os.environ.get('TILEGENERATION_CONFIGFILE', 'tilegeneration/config.yaml'),
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
    _geom = None

    geoms = None
    tilestream = None
    duration = 0
    error = 0

    def __init__(self, config_file, options=None, layer_name=None, base_config=None):
        self._close_actions = []
        self._layers_geoms = {}
        self.error_files_ = {}

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
            self.config.update({} if base_config is None else base_config)
            self.config.update(yaml.safe_load(f))
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
            schema_data=yaml.safe_load(pkgutil.get_data("tilecloud_chain", "schema.yaml")),
        )
        path_ = ''
        try:
            self.config = c.validate()

            for name, cache in self.config['caches'].items():
                if cache['type'] == 's3':
                    c = Core(
                        source_data=cache,
                        schema_data=yaml.safe_load(
                            pkgutil.get_data("tilecloud_chain", "schema-cache-s3.yaml")),
                    )
                    path_ = 'caches/{}'.format(name)
                    self.config['caches'][name] = c.validate()
            for name, layer in self.config['layers'].items():
                c = Core(
                    source_data=layer,
                    schema_data=yaml.safe_load(
                        pkgutil.get_data("tilecloud_chain", "schema-layer-{}.yaml".format(layer['type']))
                    ),
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
        self.metadata = self.config.get('metadata')
        self.provider = self.config.get('provider')

        if error:
            exit(1)

        if 'log_format' in self.config.get('generation', {}):
            self._configure_logging(options, self.config['generation']['log_format'])

        if options is not None and options.zoom is not None:
            error_message = (
                "The zoom argument '%s' has incorrect format, "
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
                    logger.error(error_message, exc_info=True)
                    error = True
            elif options.zoom.find(',') >= 0:
                try:
                    options.zoom = [int(z) for z in options.zoom.split(',')]
                except ValueError:  # pragma: no cover
                    logger.error(error_message, exc_info=True)
                    error = True
            else:
                try:
                    options.zoom = [int(options.zoom)]
                except ValueError:  # pragma: no cover
                    logger.error(error_message, exc_info=True)
                    error = True

        if error:  # pragma: no cover
            exit(1)

        if layer_name and not error:
            self.init_layer(self.layers[layer_name], options)

    @staticmethod
    def _primefactors(x):
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

    @staticmethod
    def _configure_logging(options, format_):
        if os.environ.get('CI', 'FALSE') == 'TRUE':
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
                'disable_existing_loggers': False,  # Without that, existing loggers are silent
                'loggers': {
                    'tilecloud': {
                        'level': level
                    },
                    'tilecloud_chain': {
                        'level': level
                    }
                },
                'root': {
                    'level': other_level,
                    'handlers': [os.environ.get('LOG_TYPE', 'console')]
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'default',
                        'stream': 'ext://sys.stdout'
                    },
                    'logstash': {
                        'class': 'c2cwsgiutils.pyramid_logging.PyramidCeeSysLogHandler',
                        'address': (
                            os.environ.get('LOG_HOST', 'localhost'),
                            int(os.environ.get('LOG_PORT', '514'))
                        )
                    },
                    'json': {
                        'class': 'c2cwsgiutils.pyramid_logging.JsonLogHandler',
                        'stream': 'ext://sys.stdout'
                    },
                },
                'formatters': {
                    'default': {
                        'format': format_
                    }
                }
            })
        sentry.init()

    def get_all_dimensions(self, layer):
        assert layer is not None

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
        return [{}] if len(all_dimensions) == 0 else[dict(d) for d in product(*all_dimensions)]

    def get_store(self, cache, layer, read_only=False):
        grid = layer['grid_ref'] if 'grid_ref' in layer else None
        layout = WMTSTileLayout(
            layer=layer['name'],
            url=cache['folder'],
            style=layer['wmts_style'],
            format='.' + layer['extension'],
            dimensions_name=[dimension['name'] for dimension in layer['dimensions']],
            tile_matrix_set=layer['grid'],
            tile_matrix=lambda z: get_tile_matrix_identifier(grid, zoom=z),
            request_encoding='REST',
        )
        # store
        if cache['type'] == 's3':
            # on s3
            cache_tilestore = S3TileStore(
                cache['bucket'], layout,
                s3_host=cache.get('host'),
                cache_control=cache.get('cache_control'))  # pragma: no cover
        elif cache['type'] == 'mbtiles':
            metadata = {}
            for dimension in layer['dimensions']:
                metadata['dimension_' + dimension['name']] = dimension['default']
            # on mbtiles file
            filename = layout.filename(
                TileCoord(0, 0, 0), metadata=metadata
            ).replace('/0/0/0', '') + '.mbtiles'
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            cache_tilestore = MBTilesTileStore(
                sqlite3.connect(filename),
                content_type=layer['mime_type'],
                tilecoord_in_topleft=True,
            )
        elif cache['type'] == 'bsddb':
            metadata = {}
            for dimension in layer['dimensions']:
                metadata['dimension_' + dimension['name']] = dimension['default']
            import bsddb3 as bsddb
            from tilecloud.store.bsddb import BSDDBTileStore

            # on bsddb file
            filename = layout.filename(
                TileCoord(0, 0, 0), metadata=metadata
            ).replace('/0/0/0', '') + '.bsddb'
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            db = bsddb.hashopen(
                filename,
                # and os.path.exists(filename) to avoid error on non existing file
                'r' if read_only and os.path.exists(filename) else 'c'
            )

            class Close:
                def __init__(self, db):
                    self.db = db

                def __call__(self):
                    self.db.close()

            self._close_actions.append(Close(db))

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

    def init_layer(self, layer, options):
        self.create_log_tiles_error(layer['name'])

        if options.near is not None or (
                options.time is not None and 'bbox' in layer and options.zoom is not None
        ):  # pragma: no cover
            if options.zoom is None or len(options.zoom) != 1:  # pragma: no cover
                exit('Option --near needs the option --zoom with one value.')
            if not (options.time is not None or options.test is not None):  # pragma: no cover
                exit('Option --near needs the option --time or --test.')
            position = options.near if options.near is not None else [
                (layer['bbox'][0] + layer['bbox'][2]) / 2,
                (layer['bbox'][1] + layer['bbox'][3]) / 2,
            ]
            bbox = layer['grid_ref']['bbox']
            diff = [position[0] - bbox[0], position[1] - bbox[1]]
            resolution = layer['grid_ref']['resolutions'][options.zoom[0]]
            mt_to_m = layer['meta_size'] * layer['grid_ref']['tile_size'] * resolution
            mt = [float(d) / mt_to_m for d in diff]

            nb_tile = options.time * 3 if options.time is not None else options.test
            nb_mt = nb_tile / (layer['meta_size'] ** 2)
            nb_sqrt_mt = ceil(sqrt(nb_mt))

            mt_origin = [round(m - nb_sqrt_mt / 2) for m in mt]
            self.init_geom([
                bbox[0] + mt_origin[0] * mt_to_m,
                bbox[1] + mt_origin[1] * mt_to_m,
                bbox[0] + (mt_origin[0] + nb_sqrt_mt) * mt_to_m,
                bbox[1] + (mt_origin[1] + nb_sqrt_mt) * mt_to_m,
            ])
        elif options.bbox is not None:
            self.init_geom(layer, options.bbox)
        elif 'bbox' in layer:
            self.init_geom(layer, layer['bbox'])
        else:
            self.init_geom(layer, layer['grid_ref']['bbox'])

    def get_grid(self, layer, name=None):
        if name is None:
            name = layer['grid']

        return self.grids[name]

    def get_tilesstore(self, cache_name):
        cache = self.caches[cache_name]
        cache_tilestore = TimedTileStoreWrapper(MultiTileStore({
            lname: self.get_store(cache, layer)
            for lname, layer in self.layers.items()
        }), stats_name='store')
        return cache_tilestore

    def get_sqs_queue(self):  # pragma: no cover
        if 'sqs' not in self.config:
            exit("The config hasn't any configured queue")
        sqs = boto3.resource('sqs', region_name=self.config['sqs']['region'])
        queue = sqs.get_queue_by_name(QueueName=self.config['sqs']['queue'])
        return queue

    def init_geom(self, layer, extent=None):
        self.geoms = self.get_geoms(layer, extent)

    def get_geoms(self, layer, extent=None):
        if layer['name'] in self._layers_geoms:  # pragma: no cover
            # already build
            return self._layers_geoms[layer['name']]

        layer_geoms = {}
        self._layers_geoms[layer['name']] = layer_geoms
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
                with stats.timer_context(['geoms_get', layer['name']]):
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

    @staticmethod
    def get_geoms_filter(layer, grid, geoms):
        return IntersectGeometryFilter(
            grid=grid,
            geoms=geoms,
            px_buffer=(
                layer['px_buffer'] +
                layer['meta_buffer'] if layer.get('meta', False) else 0
            )
        )

    def add_geom_filter(self, layer):
        self.ifilter(self.get_geoms_filter(
            layer=layer,
            grid=self.get_grid(layer),
            geoms=self.geoms,
        ), "Intersect with geom")

    def add_logger(self):
        if not self.options.quiet and \
                not self.options.verbose and \
                not self.options.debug:
            def log_tiles(tile):
                variables = dict()
                variables.update(tile.__dict__)
                variables.update(tile.tilecoord.__dict__)
                sys.stdout.write("{tilecoord} {metadata}                         \r".format(**variables))
                sys.stdout.flush()
                return tile
            self.imap(log_tiles)
        elif not self.options.quiet:
            self.imap(Logger(logger, logging.INFO, '%(tilecoord)s, %(formated_metadata)s'))

    def add_metatile_splitter(self):
        assert self.tilestream is not None

        splitters = {}
        for lname, layer in self.layers.items():
            if layer.get('meta'):
                splitters[lname] = MetaTileSplitterTileStore(
                    layer['mime_type'],
                    layer['grid_ref']['tile_size'],
                    layer['meta_buffer'])

        store = TimedTileStoreWrapper(MultiTileStore(splitters), stats_name='splitter')

        if self.options.debug:
            def meta_get(tilestream):  # pragma: no cover
                for metatile in tilestream:
                    substream = store.get((metatile,))
                    for tile in substream:
                        yield tile
            self.tilestream = meta_get(self.tilestream)  # pragma: no cover
        else:
            def safe_get(tilestream):
                for metatile in tilestream:
                    try:
                        substream = store.get((metatile,))
                        for tile in substream:
                            yield tile
                    except GeneratorExit as e:
                        raise e
            self.tilestream = safe_get(self.tilestream)

    def create_log_tiles_error(self, layer):
        if 'error_file' in self.config['generation']:
            now = datetime.now()
            time = now.strftime('%d-%m-%Y %H:%M:%S')
            error_file = open(
                self.config['generation']['error_file'].format(
                    layer=layer, datetime=now
                ),
                'a'
            )
            error_file.write("# [{}] Start the layer '{}' generation\n".format(time, layer))
            self.error_files_[layer] = error_file
            return error_file

    def close(self):
        for file_ in self.error_files_.values():
            file_.close()

    def get_log_tiles_error_file(self, layer):
        return self.error_files_[layer] if layer in self.error_files_ else \
            self.create_log_tiles_error(layer)

    def log_tiles_error(self, tile=None, message=None):
        if 'error_file' in self.config['generation']:
            time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            if self.get_log_tiles_error_file(tile.metadata.get('layer')) is None:  # pragma: no cover
                raise Exception("Missing error file")

            tilecoord = "" \
                if tile.tilecoord is None \
                else "{} {} ".format(tile.tilecoord, tile.formated_metadata)
            message = "" if message is None else " {}".format(message)

            self.get_log_tiles_error_file(tile.metadata.get('layer')).write('{}# [{}]{}\n'.format(
                tilecoord, time, message.replace('\n', ' ')
            ))

    def add_error_filters(self, queue_store=None):
        assert self.tilestream is not None

        self.imap(LogErrors(
            logger, logging.ERROR,
            "Error in tile: %(tilecoord)s, %(formated_metadata)s, %(error)r"
        ))

        if stats.BACKENDS:
            def add_stats(tile):
                if tile and tile.error:
                    stats.increment_counter(['error', tile.metadata.get('layer', 'None')])
                return tile
            self.imap(add_stats)

        if 'error_file' in self.config['generation']:

            def do(tile):
                if tile and tile.error:
                    self.log_tiles_error(tile=tile, message=repr(tile.error))
                return tile
            self.imap(do)
        if self.config['generation']['maxconsecutive_errors'] > 0:
            self.tilestream = map(MaximumConsecutiveErrors(
                self.config['generation']['maxconsecutive_errors']), self.tilestream)

        def drop_count(tile):
            if tile and tile.error:
                if queue_store is not None:
                    queue_store.delete_one(tile)
                self.error += 1
                return False
            return True
        self.ifilter(drop_count)

    def init_tilecoords(self, layer):
        resolutions = layer['grid_ref']['resolutions']

        if self.options.time is not None and self.options.zoom is None:
            if 'min_resolution_seed' in layer:  # pragma: no cover
                self.options.zoom = [resolutions.index(
                    layer['min_resolution_seed']
                )]
            else:
                self.options.zoom = [len(resolutions) - 1]

        if self.options.zoom is not None:
            zoom_max = len(resolutions) - 1
            for zoom in self.options.zoom:
                if zoom > zoom_max:
                    logger.warning(
                        "zoom %i is greater than the maximum zoom %i"
                        " of grid %s of layer %s, ignored." % (
                            zoom, zoom_max, layer['grid'], layer['name']
                        )
                    )
            self.options.zoom = [z for z in self.options.zoom if z <= zoom_max]

        if 'min_resolution_seed' in layer:
            if self.options.zoom is None:
                self.options.zoom = []
                for z, resolution in enumerate(resolutions):
                    if resolution >= layer['min_resolution_seed']:
                        self.options.zoom.append(z)
            else:
                for zoom in self.options.zoom:
                    resolution = resolutions[zoom]
                    if resolution < layer['min_resolution_seed']:
                        logger.warning(
                            "zoom %i corresponds to resolution %s is smaller"
                            " than the 'min_resolution_seed' %s of layer %s, ignored." %
                            (
                                zoom, resolution, layer['min_resolution_seed'], layer['name']
                            )
                        )
                self.options.zoom = [
                    z for z in self.options.zoom if
                    resolutions[z] >= layer['min_resolution_seed']
                ]

        if self.options.zoom is None:
            self.options.zoom = [z for z, r in enumerate(resolutions)]

        # fill the bounding pyramid
        tilegrid = layer['grid_ref']['obj']
        bounding_pyramid = BoundingPyramid(tilegrid=tilegrid)
        for zoom in self.options.zoom:
            if zoom in self.geoms:
                extent = self.geoms[zoom].bounds

                if len(extent) == 0:
                    logger.warning("bounds empty for zoom {}".format(zoom))
                else:
                    minx, miny, maxx, maxy = extent
                    px_buffer = layer['px_buffer']
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

        if layer.get('meta', False):
            self.set_tilecoords(bounding_pyramid.metatilecoords(layer['meta_size']), layer)
        else:
            self.set_tilecoords(bounding_pyramid, layer)

    @staticmethod
    def _tilestream(tilecoords, default_metadata, all_dimensions):
        for tilecoord in tilecoords:
            for dimensions in all_dimensions:
                metadata = {}
                if default_metadata is not None:
                    metadata.update(default_metadata)
                for k, v in dimensions.items():
                    metadata["dimension_" + k] = v
                yield Tile(tilecoord, metadata=metadata)

    def set_tilecoords(self, tilecoords, layer):
        assert tilecoords is not None

        self.tilestream = self._tilestream(
            tilecoords,
            {'layer': layer['name']},
            self.get_all_dimensions(layer))

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
        assert self.tilestream is not None
        assert store is not None

        self.tilestream = store.get(self.tilestream)
        if not self.options.debug:
            self.tilestream = _safe_generator(self.tilestream, time_message)

    def put(self, store, time_message=None):
        assert self.tilestream is not None
        assert store is not None

        self.tilestream = store.put(self.tilestream)
        if not self.options.debug:
            self.tilestream = _safe_generator(self.tilestream, time_message)

    def delete(self, store, time_message=None):
        assert self.tilestream is not None
        assert store is not None

        self.tilestream = store.delete(self.tilestream)
        if not self.options.debug:
            self.tilestream = _safe_generator(self.tilestream, time_message)

    def imap(self, tile_filter, time_message=None):
        assert self.tilestream is not None
        assert tile_filter is not None

        self.tilestream = map(tile_filter, self.tilestream)
        if not self.options.debug:
            self.tilestream = _safe_generator(self.tilestream, time_message)

    def ifilter(self, tile_filter, time_message=None):
        assert self.tilestream is not None
        assert tile_filter is not None

        self.tilestream = filter(tile_filter, self.tilestream)
        if not self.options.debug:
            self.tilestream = _safe_generator(self.tilestream, time_message)

    def consume(self, test=None, force=False):
        assert self.tilestream is not None

        if hasattr(self.options, 'daemon') and self.options.daemon and \
                not self.options.debug and not force:
            while True:
                try:
                    self.consume(test, True)
                except KeyboardInterrupt:
                    sys.exit()
                except Exception as e:
                    logger.error(e, exc_info=True)
                    traceback.print_exc()
                    time.sleep(1)

        test = self.options.test if test is None else test

        start = datetime.now()
        consume(self.tilestream, test)
        self.duration = datetime.now() - start
        for ca in self._close_actions:
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
                        self.store.delete_one(Tile(tilecoord, metadata=tile.metadata))
                else:
                    self.store.delete_one(tile)
            logger.info("The tile {} {} is dropped".format(tile.tilecoord, tile.formated_metadata))
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
        layer = tile.metadata['layer']
        if layer in self.actions:
            action = self.actions[layer]
            return action(tile)
        else:
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
            logger.error(tile.data, exc_info=True)
            raise e
        for px in image.getdata():
            if ref is None:
                ref = px
            elif px != ref:
                exit("Error: image is not uniform.")

        print("""Tile: {} {}
    {}:
        size: {}
        hash: {}""".format(
            tile.tilecoord, tile.formated_metadata, self.block, len(tile.data),
            sha1(tile.data).hexdigest()
        ))
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

    def __init__(self, grid, geoms=None, px_buffer=0):
        self.grid = grid
        self.geoms = geoms
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

    @staticmethod
    def bbox_polygon(bbox):
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
            logger.error("The tile: {tilecoord}{formated_metadata} is empty".format(**{
                'tilecoord': tile.tilecoord if tile else 'not defined',
                'formated_metadata': ' ' + tile.formated_metadata if tile else '',
            }))
            if 'error_file' in self.gene.config['generation'] and tile:
                self.gene.log_tiles_error(tile=tile, message='The tile is empty')
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
                    tile.error = "Command '{}' on tile {} return error code {}".format(
                        command, tile.tilecoord, code)
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


class TilesFileStore(TileStore):
    def __init__(self, tiles_file, layer, all_dimensions):
        assert isinstance(layer, str)

        self.tiles_file = open(tiles_file)
        self.layer = layer
        self.all_dimensions = all_dimensions

    def list(self):
        while True:
            line = self.tiles_file.readline()
            if not line:
                return
            line = line.split('#')[0].strip()
            if line != '':
                try:
                    tilecoord = parse_tilecoord(line)
                except ValueError as e:  # pragma: no cover
                    logger.error("A tile '{}' is not in the format 'z/x/y' or z/x/y:+n/+n\n{}".format(
                        line, repr(e), exc_info=True)
                    )
                    continue

                for dimensions in self.all_dimensions:
                    metadata = {'layer': self.layer}
                    for k, v in dimensions.items():
                        metadata["dimension_" + k] = v
                    yield Tile(tilecoord, metadata=metadata)


def _safe_generator(generator, time_message=None):
    while True:  # will exit when next(generator) raises StopIteration
        tile = None
        try:
            n = datetime.now()
            tile = next(generator)
            if tile is None:
                continue
            if time_message:
                logger.info("{} in {}".format(time_message, str(datetime.now() - n)))
        except GeneratorExit as e:  # pragma: no cover
            raise e
        except SystemExit as e:  # pragma: no cover
            raise e
        except KeyboardInterrupt:  # pragma: no cover
            exit("User interrupt")
        except StopIteration:
            return
        yield tile
