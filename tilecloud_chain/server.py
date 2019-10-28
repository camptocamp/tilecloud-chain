# -*- coding: utf-8 -*-

# Copyright (c) 2013 by Stéphane Brunner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 3. Neither the name of Camptocamp nor the names of its contributors may
# be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
import logging
import mimetypes
import os
import types
from urllib.parse import parse_qs, urlencode

from c2cwsgiutils import health_check
import c2cwsgiutils.pyramid
from pyramid.config import Configurator
import requests

from tilecloud import Tile, TileCoord
import tilecloud.store.s3
from tilecloud_chain import TileGeneration, controller, internal_mapcache

logger = logging.getLogger(__name__)


tilegeneration = None


def init_tilegeneration(config_file):
    global tilegeneration
    if tilegeneration is None:
        logger.info("Config file: '{}'".format(config_file))
        tilegeneration = TileGeneration(config_file, configure_logging=False)


class Server:

    def __init__(self):
        self.filters = {}
        self.max_zoom_seed = {}

        global tilegeneration

        self.expires_hours = tilegeneration.config['server']['expires']
        self.static_allow_extension = tilegeneration.config['server'].get(
            'static_allow_extension', ['jpeg', 'png', 'xml', 'js', 'html', 'css']
        )

        self.cache = tilegeneration.caches[
            tilegeneration.config['server'].get(
                'cache', tilegeneration.config['generation']['default_cache']
            )
        ]

        if self.cache['type'] == 's3':  # pragma: no cover
            self.s3_client = tilecloud.store.s3.get_client(self.cache.get('host'))
            bucket = self.cache['bucket']

            def _read(self, key_name):
                response = self.s3_client.get_object(Bucket=bucket, Key=key_name)
                body = response['Body']
                try:
                    return body.read(), response.get('ContentType')
                finally:
                    body.close()

            def _get(self, path, **kwargs):
                key_name = os.path.join('{folder}'.format(**self.cache), path)
                try:
                    return self._read(key_name)
                except Exception:
                    self.s3_client = tilecloud.store.s3.get_client(self.cache.get('host'))
                    return self._read(key_name)
            self._read = types.MethodType(_read, self)

        else:
            folder = self.cache['folder'] or ''

            def _get(self, path, **kwargs):
                if path.split('.')[-1] not in self.static_allow_extension:  # pragma: no cover
                    return self.error(403, "Extension not allowed", **kwargs), None
                p = os.path.join(folder, path)
                if not os.path.isfile(p):  # pragma: no cover
                    return self.error(404, path + " not found", **kwargs), None
                with open(p, 'rb') as file:
                    data = file.read()
                mime = mimetypes.guess_type(p)
                return data, mime[0]
        # Get capabilities or other static files
        self._get = types.MethodType(_get, self)

        if tilegeneration.config['server']['mapcache_internal']:
            self.mapcache_baseurl = None
            self.mapcache_header = {}
        else:
            mapcache_base = tilegeneration.config['server']['mapcache_base'].rstrip('/')
            mapcache_location = tilegeneration.config['mapcache']['location'].strip('/')
            if mapcache_location == '':
                self.mapcache_baseurl = mapcache_base + '/wmts'
            else:
                self.mapcache_baseurl = '{}/{}/wmts'.format(mapcache_base, mapcache_location)
            self.mapcache_header = tilegeneration.config['server'].get('mapcache_headers', {})

        geoms_redirect = tilegeneration.config['server']['geoms_redirect']

        self.layers = tilegeneration.config['server'].get(
            'layers', tilegeneration.layers.keys()
        )
        self.stores = {}
        for layer_name in self.layers:
            layer = tilegeneration.layers[layer_name]

            # Build geoms redirect
            if geoms_redirect:
                self.filters[layer_name] = tilegeneration.get_geoms_filter(
                    layer=layer,
                    grid=layer['grid_ref'],
                    geoms=tilegeneration.get_geoms(
                        layer,
                        extent=layer['bbox'] if 'bbox' in layer else layer['grid_ref']['bbox'],
                    ),
                )

            if 'min_resolution_seed' in layer:
                max_zoom_seed = -1
                for zoom, resolution in enumerate(layer['grid_ref']['resolutions']):
                    if resolution > layer['min_resolution_seed']:
                        max_zoom_seed = zoom
                self.max_zoom_seed[layer_name] = max_zoom_seed
            else:
                self.max_zoom_seed[layer_name] = 999999

            # Build stores
            store_defs = [{
                'ref': [layer_name],
                'dimensions': {},
            }]
            for dimension in layer['dimensions']:
                new_store_defs = []
                for store_def in store_defs:
                    for value in dimension['values']:
                        dimensions = {}
                        dimensions.update(store_def['dimensions'])
                        dimensions[dimension['name']] = value
                        new_store_defs.append({
                            'ref': store_def['ref'] + [value],
                            'dimensions': dimensions,
                        })
                store_defs = new_store_defs
            for store_def in store_defs:
                self.stores['/'.join(store_def['ref'])] = \
                    tilegeneration.get_store(self.cache, layer, read_only=True)

        self.wmts_path = tilegeneration.config['server']['wmts_path']
        self.static_path = tilegeneration.config['server']['static_path'].split('/')

    def __call__(self, environ, start_response):
        params = {}
        for key, value in parse_qs(environ['QUERY_STRING'], True).items():
            params[key.upper()] = value[0]

        path = None if len(params) > 0 else environ['PATH_INFO'][1:].split('/')

        return self.serve(path, params, start_response=start_response)

    def serve(self, path, params, **kwargs):
        dimensions = []
        metadata = {}

        if path:
            if path[:len(self.static_path)] == self.static_path:
                body, mime = self._get('/'.join(path[len(self.static_path):]), **kwargs)
                if mime is not None:
                    return self.response(body, {
                        'Content-Type': mime,
                        'Expires': (
                            datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                        ).isoformat(),
                        'Cache-Control': "max-age={}".format((3600 * self.expires_hours)),
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET',
                    }, **kwargs)
                else:  # pragma: no cover
                    return body
            elif len(path) >= 1 and path[0] != self.wmts_path:  # pragma: no cover
                return self.error(
                    404,
                    "Type '{}' don't exists, allows values: '{}' or '{}'".format(
                        path[0], self.wmts_path, '/'.join(self.static_path)
                    ),
                    **kwargs
                )
            path = path[1:]  # remove type

            if len(path) == 2 and path[0] == '1.0.0' and path[1].lower() == 'wmtscapabilities.xml':
                params['SERVICE'] = 'WMTS'
                params['VERSION'] = '1.0.0'
                params['REQUEST'] = 'GetCapabilities'
            elif len(path) < 7:
                return self.error(400, "Not enough path", **kwargs)
            else:
                params['SERVICE'] = 'WMTS'
                params['VERSION'] = path[0]

                params['LAYER'] = path[1]
                params['STYLE'] = path[2]

                if params['LAYER'] in self.layers:
                    layer = tilegeneration.layers[params['LAYER']]
                else:
                    return self.error(400, "Wrong Layer '{}'".format(params['LAYER']), **kwargs)

                index = 3
                dimensions = path[index:index + len(layer['dimensions'])]
                for dimension in layer['dimensions']:
                    metadata["dimension_" + dimension['name']] = path[index]
                    params[dimension['name'].upper()] = path[index]
                    index += 1

                last = path[-1].split('.')
                if len(path) < index + 4:  # pragma: no cover
                    return self.error(400, "Not enough path", **kwargs)
                params['TILEMATRIXSET'] = path[index]
                params['TILEMATRIX'] = path[index + 1]
                params['TILEROW'] = path[index + 2]
                if len(path) == index + 4:
                    params['REQUEST'] = 'GetTile'
                    params['TILECOL'] = last[0]
                    if last[1] != layer['extension']:  # pragma: no cover
                        return self.error(400, "Wrong extension '{}'".format(last[1]), **kwargs)
                elif len(path) == index + 6:
                    params['REQUEST'] = 'GetFeatureInfo'
                    params['TILECOL'] = path[index + 3]
                    params['I'] = path[index + 4]
                    params['J'] = last[0]
                    params['INFO_FORMAT'] = layer.get('info_formats', ['application/vnd.ogc.gml'])[0]
                else:  # pragma: no cover
                    return self.error(400, "Wrong path length", **kwargs)

                params['FORMAT'] = layer['mime_type']
        else:
            if \
                    'SERVICE' not in params or \
                    'REQUEST' not in params or \
                    'VERSION' not in params:
                return self.error(400, "Not all required parameters are present", **kwargs)

        if params['SERVICE'] != 'WMTS':
            return self.error(400, "Wrong Service '{}'".format(params['SERVICE']), **kwargs)
        if params['VERSION'] != '1.0.0':
            return self.error(400, "Wrong Version '{}'".format(params['VERSION']), **kwargs)

        if params['REQUEST'] == 'GetCapabilities':
            if 'wmtscapabilities_file' in self.cache:
                wmtscapabilities_file = self.cache['wmtscapabilities_file']
                body, mime = self._get(wmtscapabilities_file, **kwargs)
            else:
                body = controller.get_wmts_capabilities(tilegeneration, self.cache).encode('utf-8')
                mime = "application/xml"
            if mime is not None:
                return self.response(body, headers={
                    'Content-Type': "application/xml",
                    'Expires': (
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                    ).isoformat(),
                    'Cache-Control': "max-age={}".format((3600 * self.expires_hours)),
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET',
                }, **kwargs)
            else:  # pragma: no cover
                return body

        if \
                'FORMAT' not in params or \
                'LAYER' not in params or \
                'TILEMATRIXSET' not in params or \
                'TILEMATRIX' not in params or \
                'TILEROW' not in params or \
                'TILECOL' not in params:  # pragma: no cover
            return self.error(400, "Not all required parameters are present", **kwargs)

        if not path:
            if params['LAYER'] in self.layers:
                layer = tilegeneration.layers[params['LAYER']]
            else:
                return self.error(400, "Wrong Layer '{}'".format(params['LAYER']), **kwargs)

            for dimension in layer['dimensions']:
                value = params[dimension['name'].upper()] \
                    if dimension['name'].upper() in params \
                    else dimension['default']
                dimensions.append(value)
                metadata["dimension_" + dimension['name']] = value

        if params['STYLE'] != layer['wmts_style']:
            return self.error(400, "Wrong Style '{}'".format(params['STYLE']), **kwargs)
        if params['TILEMATRIXSET'] != layer['grid']:
            return self.error(400, "Wrong TileMatrixSet '{}'".format(params['TILEMATRIXSET']), **kwargs)

        metadata['layer'] = layer['name']
        tile = Tile(TileCoord(
            # TODO fix for matrix_identifier = resolution
            int(params['TILEMATRIX']),
            int(params['TILECOL']),
            int(params['TILEROW']),
        ), metadata=metadata)

        if params['REQUEST'] == 'GetFeatureInfo':
            if \
                    'I' not in params or \
                    'J' not in params or \
                    'INFO_FORMAT' not in params:  # pragma: no cover
                return self.error(400, "Not all required parameters are present", **kwargs)
            if 'query_layers' in layer:
                return self.forward(
                    layer['url'] + '?' + urlencode({
                        'SERVICE': 'WMS',
                        'VERSION': layer['version'],
                        'REQUEST': 'GetFeatureInfo',
                        'LAYERS': layer['layers'],
                        'QUERY_LAYERS': layer['query_layers'],
                        'STYLES': params['STYLE'],
                        'FORMAT': params['FORMAT'],
                        'INFO_FORMAT': params['INFO_FORMAT'],
                        'WIDTH': layer['grid_ref']['tile_size'],
                        'HEIGHT': layer['grid_ref']['tile_size'],
                        'SRS': layer['grid_ref']['srs'],
                        'BBOX': layer['grid_ref']['obj'].extent(tile.tilecoord),
                        'X': params['I'],
                        'Y': params['J'],
                    }), no_cache=True, **kwargs
                )
            else:  # pragma: no cover
                return self.error(400, "Layer '{}' not queryable".format(layer['name']), **kwargs)

        if params['REQUEST'] != 'GetTile':
            return self.error(400, "Wrong Request '{}'".format(params['REQUEST']), **kwargs)

        if params['FORMAT'] != layer['mime_type']:
            return self.error(400, "Wrong Format '{}'".format(params['FORMAT']), **kwargs)

        if tile.tilecoord.z > self.max_zoom_seed[layer['name']]:  # pragma: no cover
            return self._map_cache(layer, tile, params, kwargs)

        if layer['name'] in self.filters:
            layer_filter = self.filters[layer['name']]
            meta_size = layer['meta_size']
            meta_tilecoord = TileCoord(
                # TODO fix for matrix_identifier = resolution
                tile.tilecoord.z,
                tile.tilecoord.x / meta_size * meta_size,
                tile.tilecoord.y / meta_size * meta_size,
                meta_size,
            ) if meta_size != 1 else tile.tilecoord
            if not layer_filter.filter_tilecoord(meta_tilecoord):  # pragma: no cover
                return self._map_cache(layer, tile, params, kwargs)

        store_ref = '/'.join([params['LAYER']] + list(dimensions))
        if store_ref in self.stores:  # pragma: no cover
            store = self.stores[store_ref]
        else:  # pragma: no cover
            return self.error(
                400,
                "No store found for layer '{}' and dimensions {}".format(
                    layer['name'], ', '.join(dimensions)
                ),
                **kwargs
            )

        tile = store.get_one(tile)
        if tile:
            if tile.error:
                return self.error(500, tile.error, **kwargs)

            return self.response(tile.data, headers={
                'Content-Type': tile.content_type,
                'Expires': (
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                ).isoformat(),
                'Cache-Control': "max-age={}".format((3600 * self.expires_hours)),
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Tile-Backend': 'Cache'
            }, **kwargs)
        else:
            return self.error(204, **kwargs)

    def _map_cache(self, layer, tile, params, kwargs):
        if self.mapcache_baseurl is not None:
            return self.forward(
                self.mapcache_baseurl + '?' + urlencode(params),
                headers=self.mapcache_header,
                **kwargs
            )
        else:
            global tilegeneration
            return internal_mapcache.fetch(self, tilegeneration, layer, tile, kwargs)

    def forward(self, url, headers=None, no_cache=False, **kwargs):
        if headers is None:
            headers = {}
        if no_cache:
            headers['Cache-Control'] = 'no-cache'
            headers['Pragma'] = 'no-cache'

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response_headers = response.headers.copy()
            if no_cache:
                response_headers['Cache-Control'] = 'no-cache, no-store'
                response_headers['Pragma'] = 'no-cache'
            else:  # pragma: no cover
                response_headers['Expires'] = (
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                ).isoformat()
                response_headers['Cache-Control'] = "max-age={}".format((3600 * self.expires_hours))
                response_headers['Access-Control-Allow-Origin'] = '*'
                response_headers['Access-Control-Allow-Methods'] = 'GET'
            return self.response(response.content, headers=response_headers, **kwargs)
        else:  # pragma: no cover
            message = "The URL '{}' return '{} {}', content:\n{}".format(
                url, response.status_code, response.reason, response.text
            )
            logger.warning(message)
            return self.error(502, message=message, **kwargs)

    HTTP_MESSAGES = {
        204: '204 No Content',
        400: '400 Bad Request',
        403: '403 Forbidden',
        404: '404 Not Found',
        502: '502 Bad Gateway',
    }

    def error(self, code, message='', **kwargs):
        kwargs['start_response'](self.HTTP_MESSAGES[code], [])
        return [message]

    @staticmethod
    def response(data, headers=None, **kwargs):
        if headers is None:  # pragma: no cover
            headers = {}
        headers['Content-Length'] = str(len(data))
        kwargs['start_response']('200 OK', headers.items())
        return [data]


def app_factory(
    global_config,
    configfile=os.environ.get('TILEGENERATION_CONFIGFILE', 'tilegeneration/config.yaml'),
    **local_conf
):
    del global_config
    del local_conf

    init_tilegeneration(configfile)

    return Server()


class PyramidServer(Server):

    def error(self, code, message=None, **kwargs):
        from pyramid.httpexceptions import exception_response
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
        }
        if code == 204:
            headers.update({
                'Expires': (
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                ).isoformat(),
                'Cache-Control': "max-age={}".format((3600 * self.expires_hours)),
            })
            return exception_response(code, detail=message, headers=headers)

        raise exception_response(code, detail=message, headers=headers)

    def response(self, data, headers=None, **kwargs):
        if headers is None:  # pragma: no cover
            headers = {}
        kwargs['request'].response.headers = headers
        if isinstance(data, memoryview):
            kwargs['request'].response.body_file = data
        else:
            kwargs['request'].response.body = data
        return kwargs['request'].response


pyramid_server = None


class PyramidView():

    def __init__(self, request):
        self.request = request
        global pyramid_server

        init_tilegeneration(request.registry.settings['tilegeneration_configfile'])

        if pyramid_server is None:
            pyramid_server = PyramidServer()
        self.server = pyramid_server

    def __call__(self):
        params = {}
        path = None

        if 'path' in self.request.matchdict:
            path = self.request.matchdict['path']
        if not path:
            for param, value in self.request.params.items():
                params[param.upper()] = value

        return self.server.serve(path, params, request=self.request)


def main(global_config, **settings):
    from pyramid_mako import add_mako_renderer
    del global_config  # unused

    config = Configurator(settings=settings)

    init_tilegeneration(settings['tilegeneration_configfile'])
    global tilegeneration

    config.include(c2cwsgiutils.pyramid.includeme)
    health_check.HealthCheck(config)

    add_mako_renderer(config, ".html")

    config.add_route(
        'admin', '/{}/'.format(tilegeneration.config['server']['admin_path']),
        request_method='GET',
    )
    config.add_route(
        'admin_run', '/{}/run'.format(tilegeneration.config['server']['admin_path']),
        request_method='POST',
    )

    config.add_route('tiles', '/*path', request_method='GET')
    config.add_view(PyramidView, route_name='tiles')

    config.scan('tilecloud_chain.views')

    return config.make_wsgi_app()
