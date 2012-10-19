# -*- coding: utf-8 -*-

import sys
import logging
import yaml
from itertools import imap, ifilter
from hashlib import sha1
from cStringIO import StringIO

try:
    from PIL import Image
    Image  # suppress pyflakes warning
except:
    import Image

import psycopg2
from shapely.wkt import loads as loads_wkt
from shapely.geometry import Polygon
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage

from tilecloud import Tile, BoundingPyramid, TileCoord
from tilecloud.grid.free import FreeTileGrid
from tilecloud.filter.error import LogErrors, MaximumConsecutiveErrors, DropErrors


logger = logging.getLogger(__name__)


class TileGeneration:
    geom = None

    def __init__(self, config_file, options, layer_name=None):
        self.config = yaml.load(file(config_file))
        self.options = options

        self.validate_exists(self.config, 'config', 'grids')
        self.grids = self.config['grids']
        error = False
        for gname, grid in self.config['grids'].items():
            name = "grid[%s]" % gname
            error = self.validate(grid, name, 'name', attribute_type=str, default=gname) or error
            error = self.validate(grid, name, 'resolution_scale',
                attribute_type=int, default=1) or error
            error = self.validate(grid, name, 'resolutions',
                attribute_type=float, is_array=True, required=True) or error
            error = self.validate(grid, name, 'bbox', attribute_type=float, is_array=True, required=True) or error
            error = self.validate(grid, name, 'srs', attribute_type=str, required=True) or error
            error = self.validate(grid, name, 'tile_size', attribute_type=int, default=256) or error
            scale = grid['resolution_scale']
            for r in grid['resolutions']:
                if r * scale % 1 != 0.0:
                    logger.error("The reolution %f * 'resolution_scale' is not an integer" % r)
                    error = True

            grid['obj'] = FreeTileGrid(
                resolutions=[int(r * scale) for r in grid['resolutions']],
                scale=scale,
                max_extent=grid['bbox'],
                tile_size=grid['tile_size']) if not error else None

        default = self.config['layer_default']
        self.layers = {}
        self.validate_exists(self.config, 'config', 'layers')
        for lname, layer in self.config['layers'].items():
            name = "layer[%s]" % lname
            for k, v in default.items():
                if k not in layer:
                    layer[k] = v

            error = self.validate(layer, name, 'name', attribute_type=str, default=lname) or error
            error = self.validate(layer, name, 'grid', attribute_type=str, required=True) or error
            error = self.validate(layer, name, 'type', attribute_type=str, required=True,
                enumeration=['wms', 'mapnik']) or error

            error = self.validate(layer, name, 'meta', attribute_type=bool, default=False) or error
            error = self.validate(layer, name, 'meta_size', attribute_type=int, default=8) or error
            error = self.validate(layer, name, 'meta_buffer', attribute_type=int,
                default=0 if layer['type'] == 'mapnik' else 128) or error

            if layer['type'] == 'wms':
                error = self.validate(layer, name, 'url', attribute_type=str, required=True) or error
                error = self.validate(layer, name, 'layers', attribute_type=str, required=True) or error
            if layer['type'] == 'mapnik':
                error = self.validate(layer, name, 'mapfile', attribute_type=str, required=True) or error
                error = self.validate(layer, name, 'output_format', attribute_type=str, default='png',
                    enumeration=['png', 'png256', 'jpeg', 'grid']) or error
                error = self.validate(layer, name, 'data_buffer', attribute_type=int, default=128) or error
                if layer['output_format'] == 'grid':
                    error = self.validate(layer, name, 'resolution', attribute_type=int, default=4) or error
                    error = self.validate(layer, name, 'layers_fields', attribute_type=dict, default={}) or error
                    if layer['meta']:
                        logger.error("The layer '%s' is of type Mapnik/Grid, that can't support matatiles." %
                            (layer['name']))
                        error = True

            error = self.validate(layer, name, 'extension', attribute_type=str, required=True) or error
            error = self.validate(layer, name, 'mime_type', attribute_type=str, required=True) or error
            error = self.validate(layer, name, 'wmts_style', attribute_type=str, required=True) or error
            error = self.validate(layer, name, 'dimensions', is_array=True, default=[]) or error
            for d in layer['dimensions']:
                dname = name + ".dimensions[%s]" % d.get('name', '')
                error = self.validate(d, dname, 'name', attribute_type=str, required=True) or error
                error = self.validate(d, dname, 'value', attribute_type=str, required=True) or error
                error = self.validate(d, dname, 'values', attribute_type=str, is_array=True,
                    default=[d['value']]) or error
                error = self.validate(d, dname, 'default', attribute_type=str, default=d['value']) or error

            if 'empty_tile_detection' in layer:
                error = self.validate(layer['empty_tile_detection'], name + '.empty_tile_detection',
                        'size', attribute_type=int, required=True) or error
                error = self.validate(layer['empty_tile_detection'], name + '.empty_tile_detection',
                        'hash', attribute_type=str, required=True) or error
            if 'empty_metatile_detection' in layer:
                error = self.validate(layer['empty_metatile_detection'], name + '.empty_metatile_detection',
                        'size', attribute_type=int, required=True) or error
                error = self.validate(layer['empty_metatile_detection'], name + '.empty_metatile_detection',
                        'hash', attribute_type=str, required=True) or error

            layer['grid_ref'] = self.grids[layer['grid']] if not error else None

            self.layers[lname] = layer

        self.layer = None
        if layer_name and not error:
            self.set_layer(layer_name, options)

        self.validate_exists(self.config, 'config', 'caches')
        self.caches = self.config['caches']
        for cname, cache in self.caches.items():
            name = "caches[%s]" % cname
            error = self.validate(cache, name, 'name', attribute_type=str, default=gname) or error
            error = self.validate(cache, name, 'type', attribute_type=str, required=True,
                enumeration=['s3', 'filesystem']) or error
            if cache == 'filesystem':
                error = self.validate(cache, name, 'folder', attribute_type=str, required=True) or error
            elif cache == 's3':
                error = self.validate(cache, name, 'bucket', attribute_type=str, required=True) or error
                error = self.validate(cache, name, 'folder', attribute_type=str, default='') or error

        error = self.validate(self.config, 'generation', 'config', attribute_type=dict, default={}) or error
        error = self.validate(self.config['generation'], 'generation', 'default_cache', attribute_type=str) or error
        error = self.validate(self.config['generation'], 'generation', 'default_layers',
            is_array=True, attribute_type=str) or error
        error = self.validate(self.config['generation'], 'generation', 'authorised_user', attribute_type=str) or error
        error = self.validate(self.config['generation'], 'generation', 'number_process',
            attribute_type=int, default=1) or error
        error = self.validate(self.config['generation'], 'generation', 'maxconsecutive_errors',
            attribute_type=int, default=10) or error
        error = self.validate(self.config['generation'], 'generation', 'geodata_folder', attribute_type=str) or error
        error = self.validate(self.config['generation'], 'generation', 'deploy_config',
            attribute_type=str, default="tilegeneration/deploy.cfg") or error
        error = self.validate(self.config['generation'], 'generation', 'disable_sync',
            attribute_type=bool, default=False) or error
        error = self.validate(self.config['generation'], 'generation', 'disable_code',
            attribute_type=bool, default=False) or error
        error = self.validate(self.config['generation'], 'generation', 'disable_database',
            attribute_type=bool, default=False) or error
        error = self.validate(self.config['generation'], 'generation', 'disable_fillqueue',
            attribute_type=bool, default=False) or error
        error = self.validate(self.config['generation'], 'generation', 'disable_tilesgen',
            attribute_type=bool, default=False) or error

        if 'sns' in self.config:
            error = self.validate(self.config['sns'], 'sns', 'topic', attribute_type=str, required=True) or error

        if error:
            exit(1)

    def validate_exists(self, obj, obj_name, attribute):
        if attribute not in obj:
            logger.error("The attribute '%s' is required in the object %s." % (attribute, obj_name))
            exit(1)

    def _validate_type(self, value, attribute_type, enumeration):
        if attribute_type is not None:
            if attribute_type == float:
                if type(value) == int:
                    value = float(value)
                elif type(value) != attribute_type:
                    return (True, None, str(attribute_type))
            elif attribute_type == str:
                if type(value) != str:
                    value = str(value)
            else:
                if type(value) != attribute_type:
                    return (True, None, str(attribute_type))
        if enumeration:
            return (value not in enumeration, value, str(enumeration))
        return (False, value, None)

    def validate(self, obj, obj_name, attribute, attribute_type=None, is_array=False,
            default=None, required=False, enumeration=None):
        if attribute in obj:
            if is_array:
                if type(obj[attribute]) == list:
                    for n, v in enumerate(obj[attribute]):
                        result, value, type_error = self._validate_type(v, attribute_type, enumeration)
                        if result:
                            logger.error("The attribute '%s' of the object %s has an element who is not a %s." %
                                (attribute, obj_name, type_error))
                            return True
                        obj[attribute][n] = value
                else:
                    logger.error("The attribute '%s' of the object %s is not an array." % (attribute, obj_name))
                    return True
            else:
                result, value, type_error = self._validate_type(obj[attribute], attribute_type, enumeration)
                if result:
                    logger.error("The attribute '%s' of the object %s is not a %s." %
                        (attribute, obj_name, type_error))
                    return True
                obj[attribute] = value
        elif required:
            logger.error("The attribute '%s' is required in the object %s." % (attribute, obj_name))
            return True
        elif default is not None:
            obj[attribute] = default
        return False

    def set_layer(self, layer, options):
        self.layer = self.layers[layer]

        if options.bbox:
            self.init_geom(options.bbox)
        elif options.time and 'bbox' in self.layer:
            self.init_geom([
                (self.layer['bbox'][0] + self.layer['bbox'][2]) / 2,
                (self.layer['bbox'][1] + self.layer['bbox'][3]) / 2,
                self.layer['bbox'][2], self.layer['bbox'][3]
            ])
        elif 'bbox' in self.layer:
            self.init_geom(self.layer['bbox'])
        else:
            self.init_geom(self.layer['grid_ref']['bbox'])

    def get_grid(self, name=None):
        if not name:
            name = self.layer['grid']

        return self.grids[name]

    def get_sqs_queue(self):
        config_sqs = self.config['forge']['sqs']
        connection = boto.sqs.connect_to_region(config_sqs['region_name'])
        queue = connection.create_queue(config_sqs['queue_name'])
        queue.set_message_class(JSONMessage)
        return queue

    def init_geom(self, extent=None):
        self.geom = None
        if 'connection' in self.layer and 'sql' in self.layer:
            conn = psycopg2.connect(self.layer['connection'])
            cursor = conn.cursor()
            cursor.execute("SELECT ST_AsText((SELECT " +
                self.layer['sql'].strip('" ') + "))")
            self.geom = loads_wkt(cursor.fetchone()[0])
        elif extent:
            self.geom = Polygon((
                    (extent[0], extent[1]),
                    (extent[0], extent[3]),
                    (extent[2], extent[3]),
                    (extent[2], extent[1]),
                ))

    def add_geom_filter(self):
        if self.geom:
            self.ifilter(IntersectGeometryFilter(
                    grid=self.get_grid(),
                    geom=self.geom))

    def add_error_filters(self, logger):
        self.imap(LogErrors(logger, logging.ERROR,
                "Error in tile: %(tilecoord)s, %(error)r"))
        if 'maxconsecutive_errors' in self.config['generation']:
            self.tilestream = imap(MaximumConsecutiveErrors(
                    self.config['generation']['maxconsecutive_errors']), self.tilestream)
        self.ifilter(DropErrors())

    def init_tilecoords(self, options):
        bounding_pyramid = BoundingPyramid(tilegrid=self.layer['grid_ref']['obj'])
        bounding_pyramid.fill(None, self.geom.bounds)

        if options.time and not (options.zoom or options.zoom == 0):
            options.zoom = max(bounding_pyramid.bounds)

        meta = self.layer['meta']
        if meta:
            if options.zoom or options.zoom == 0:
                def metatilecoords(n, z):
                    xbounds, ybounds = bounding_pyramid.bounds[z]
                    metatilecoord = TileCoord(z, xbounds.start, ybounds.start).metatilecoord(n)
                    x = metatilecoord.x
                    while x < xbounds.stop:
                        y = metatilecoord.y
                        while y < ybounds.stop:
                            yield TileCoord(z, x, y, n)
                            y += n
                        x += n
                self.set_tilecoords(metatilecoords(self.layer['meta_size'], options.zoom))
            else:
                self.set_tilecoords(bounding_pyramid.metatilecoords(self.layer['meta_size']))
        elif options.zoom or options.zoom == 0:
            self.set_tilecoords(bounding_pyramid.ziter(options.zoom))
        else:
            self.set_tilecoords(bounding_pyramid)

    def set_tilecoords(self, tilecoords):
        self.tilestream = (
            Tile(tilecoord) for tilecoord in tilecoords)

    def set_store(self, store):
        self.tilestream = store.list()

    def get(self, store, multiprocess=False):
        if self.options.test > 0:
            self.tilestream = store.get(self.tilestream)
        else:
            def safe_get(tile):
                try:
                    return store.get_one(tile)
                except:
                    tile.error = sys.exc_info()[0]
                    return tile
            self.tilestream = imap(safe_get, ifilter(None, self.tilestream))

    def get2(self, store, multiprocess=False):
        if self.options.test > 0:
            self.tilestream = store.get(self.tilestream)
        else:
            def safe_get(tilestream):
                for tile in tilestream:
                    try:
                        substream = store.get((tile,))
                        for t in substream:
                            yield t
                    except:
                        tile.error = sys.exc_info()[1]
                        yield tile
            self.tilestream = safe_get(self.tilestream)

    def put(self, store, multiprocess=False):
        if self.options.test > 0:
            self.tilestream = store.put(self.tilestream)
        else:
            def safe_put(tile):
                try:
                    return store.put_one(tile)
                except:
                    tile.error = sys.exc_info()[0]
                    return tile
            self.tilestream = imap(safe_put, ifilter(None, self.tilestream))

    def delete(self, store, multiprocess=False):
        if self.options.test > 0:
            self.tilestream = store.delete(self.tilestream)
        else:
            def safe_delete(tile):
                try:
                    return store.delete_one(tile)
                except:
                    tile.error = sys.exc_info()[0]
                    return tile
            self.tilestream = imap(safe_delete, ifilter(None, self.tilestream))

    def imap(self, tile_filter, multiprocess=False):
        if self.options.test > 0:
            self.tilestream = imap(tile_filter, self.tilestream)
        else:
            def safe_imap(tile):
                try:
                    return tile_filter(tile)
                except:
                    tile.error = sys.exc_info()[0]
                    return tile
            self.tilestream = imap(safe_imap, ifilter(None, self.tilestream))

    def ifilter(self, tile_filter):
        if self.options.test > 0:
            self.tilestream = ifilter(tile_filter, self.tilestream)
        else:
            def safe_filter(tile):
                if tile:
                    try:
                        return tile_filter(tile)
                    except:
                        tile.error = sys.exc_info()[0]
                        return tile
            self.tilestream = ifilter(safe_filter, self.tilestream)


class HashDropper(object):
    """
    Create a filter to remove the tiles data where they have
    the specified size and hash.

    Used to drop the empty tiles.

    The ``store`` is used to delete the empty tiles.
    """

    def __init__(self, size, sha1code, store=None):
        self.size = size
        self.sha1code = sha1code
        self.store = store

    def __call__(self, tile):
        if len(tile.data) != self.size or \
                sha1(tile.data).hexdigest() != self.sha1code:
            return tile
        else:
            if self.store is not None:
                if tile.tilecoord.n != 1:
                    self.store.delete((Tile(tilecoord) for tilecoord in tile.tilecoord))
                else:
                    self.store.delete_one(tile)
            return None


class HashLogger(object):  # pragma: no cover
    """
    Log the tile size and hash.
    """

    def __init__(self, block, logger):
        self.block = block
        self.logger = logger

    def __call__(self, tile):
        ref = None
        image = Image.open(StringIO(tile.data))
        for px in image.getdata():
            if ref is None:
                ref = px
            elif px != ref:
                self.logger.info("Warning: image is not uniform.")
                break

        self.logger.info("""Tile: %s
    %s:
        size: %i
        hash: %s""" % (str(tile.tilecoord), self.block, len(tile.data), sha1(tile.data).hexdigest()))
        return tile


class IntersectGeometryFilter(object):

    def __init__(self, grid, geom=None, queue_store=None):
        self.grid = grid
        self.geom = geom or self.bbox_polygon(self.grid.max_extent)
        self.queue_store = queue_store

    def __call__(self, tile):
        intersects = self.bbox_polygon(
                self.grid['obj'].extent(tile.tilecoord)). \
                intersects(self.geom)

        if not intersects and hasattr(tile, 'metatile'):
            tile.metatile.elapsed_togenerate -= 1
            if tile.metatile.elapsed_togenerate == 0:
                self.queue_store.delete_one(tile.metatile)

        return tile if intersects else None

    def bbox_polygon(self, bbox):
        return Polygon((
                (bbox[0], bbox[1]),
                (bbox[0], bbox[3]),
                (bbox[2], bbox[3]),
                (bbox[2], bbox[1])))

    def bounds_polygon(self, bounds):
        return self.bbox_polygon((
                bounds[0].start, bounds[1].start,
                bounds[0].stop, bounds[1].stop))


class DropEmpty(object):
    """
    Create a filter for dropping all tiles with errors.
    """

    def __call__(self, tile):
        if not tile or not tile.data:
            return None
        else:
            return tile
