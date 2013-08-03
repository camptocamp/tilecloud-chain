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

import os
import logging
import httplib2
import types
import datetime
from urllib import urlencode

from tilecloud import Tile, TileCoord
from tilecloud.lib.s3 import S3Connection
from tilecloud_chain import TileGeneration

from pyramid.httpexceptions import HTTPBadRequest, HTTPNoContent, HTTPNotFound, \
    HTTPForbidden


logger = logging.getLogger(__name__)


class Serve:

    def __init__(self, request):
        self.request = request
        self.settings = request.registry.settings
        self.filters = {}
        self.http = httplib2.Http()

        self.tilegeneration = TileGeneration(self.settings['tilegeneration_configfile'])
        if not self.tilegeneration.validate_apache_config():  # pragma: no cover
            raise "Apache configuration error"

        self.expires_hours = self.tilegeneration.config['apache']['expires']
        self.static_allow_extension = self.tilegeneration.config['serve']['static_allow_extension'] \
            if 'static_allow_extension' in self.tilegeneration.config['serve'] \
            else ['jpeg', 'png', 'xml']

        self.cache = self.tilegeneration.caches[
            self.tilegeneration.config['serve']['cache'] if
            'cache' in self.tilegeneration.config['serve'] else
            self.tilegeneration.config['generation']['default_cache']
        ]

        if self.cache['type'] == 's3':  # pragma: no cover
            s3bucket = S3Connection().bucket(self.cache['bucket'])

            def _get(self, path):
                global s3bucket
                try:
                    s3key = s3bucket.key(('%(folder)s' % self.cache) + path)
                    return s3key.get().body
                except:
                    s3bucket = S3Connection().bucket(self.cache['bucket'])
                    s3key = s3bucket.key(('%(folder)s' % self.cache) + path)
                    return s3key.get().body
        else:
            folder = self.cache['folder'] or ''

            def _get(self, path):
                if path.split('.')[-1] not in self.static_allow_extension:  # pragma: no cover
                    raise HTTPForbidden
                if not os.path.isfile(folder + path):  # pragma: no cover
                    raise HTTPNotFound
                with open(folder + path, 'rb') as file:
                    data = file.read()
                return data
        # get capabilities or other static files
        self._get = types.MethodType(_get, self)

        geoms_redirect = bool(self.tilegeneration.config['serve']['geoms_redirect']) if \
            'geoms_redirect' in self.tilegeneration.config['serve'] else False

        self.layers = self.tilegeneration.config['serve']['layers'] if \
            'layers' in self.tilegeneration.config['serve'] else \
            self.tilegeneration.layers.keys()
        self.stores = {}
        for layer_name in self.layers:
            layer = self.tilegeneration.layers[layer_name]

            # build geoms redirect
            if geoms_redirect:
                if not self.tilegeneration.validate_mapcache_config():  # pragma: no cover
                    raise "Mapcache configuration error"

                mapcache_base = self.tilegeneration.config['serve']['mapcache_base'] if \
                    'mapcache_base' in self.tilegeneration.config['serve'] else \
                    'http://localhost/'
                self.mapcache_baseurl = mapcache_base + self.tilegeneration.config['apache']['location']
                self.mapcache_header = self.tilegeneration.config['serve']['mapcache_headers'] if \
                    'mapcache_headers' in self.tilegeneration.config['serve'] else {}

                self.filters[layer_name] = self.tilegeneration.get_geoms_filter(
                    layer=layer,
                    grid=layer['grid_ref'],
                    geoms=self.tilegeneration.get_geoms(layer),
                )
            elif 'min_resolution_seed' in layer:
                max_zoom_seed = layer['grid_ref']['resolutions'].index(layer['min_resolution_seed'])

                def seed_filter(tile):
                    return tile if tile.tilecoord.z <= max_zoom_seed else None
                self.filters[layer_name] = seed_filter

            # build stores
            store_defs = [{
                'ref': [layer_name],
                'dimensions': [],
            }]
            for dimension in layer['dimensions']:
                new_store_defs = []
                for store_def in store_defs:
                    for value in dimension['values']:
                        new_store_defs.append({
                            'ref': store_def['ref'] + [value],
                            'dimensions': store_def['dimensions'] + [(dimension['name'], value)],
                        })
                store_defs = new_store_defs
            for store_def in store_defs:
                self.stores['/'.join(store_def['ref'])] = \
                    self.tilegeneration.get_store(self.cache, layer, store_def['dimensions'])

    def __call__(self):
        params = {}
        dimensions = []

        if 'path' in self.request.matchdict:
            path = self.request.matchdict['path']
            if len(path) >= 1 and path[0] == 'static':
                return self._get('/' + '/'.join(path[1:]))
            elif len(path) >= 1 and path[0] != 'wmts':  # pragma: no cover
                raise HTTPNotFound("Type '%s' don't exists, allows values: 'wmts' or 'static'")
            path = path[1:]  # remove type

            if len(path) == 2 and path[0] == '1.0.0' and path[1].lower() == 'wmtscapabilities.xml':
                params['SERVICE'] = 'WMTS'
                params['VERSION'] = '1.0.0'
                params['REQUEST'] = 'GetCapabilities'
            elif len(path) < 7:
                raise HTTPBadRequest("Not enough path")
            else:
                params['SERVICE'] = 'WMTS'
                params['VERSION'] = path[0]

                params['LAYER'] = path[1]
                params['STYLE'] = path[2]

                if params['LAYER'] in self.layers:
                    layer = self.tilegeneration.layers[params['LAYER']]
                else:
                    raise HTTPBadRequest("Wrong Layer '%s'" % params['LAYER'])

                index = 3
                dimensions = path[index:index+len(layer['dimensions'])]
                for dimension in layer['dimensions']:
                    params[dimension['name'].upper()] = path[index]
                    index += 1

                last = path[-1].split('.')
                if len(path) < index + 4:  # pragma: no cover
                    raise HTTPBadRequest("Not enough path")
                params['TILEMATRIXSET'] = path[index]
                params['TILEMATRIX'] = path[index + 1]
                params['TILEROW'] = path[index + 2]
                if len(path) == index + 4:
                    params['REQUEST'] = 'GetTile'
                    params['TILECOL'] = last[0]
                    if last[1] != layer['extension']:  # pragma: no cover
                        raise HTTPBadRequest("Wrong extention '%s'" % last[1])
                elif len(path) == index + 6:
                    params['REQUEST'] = 'GetFeatureInfo'
                    params['TILECOL'] = path[index + 3]
                    params['I'] = path[index + 4]
                    params['J'] = last[0]
                    params['INFO_FORMAT'] = layer['info_formats'][0]
                else:  # pragma: no cover
                    raise HTTPBadRequest("Wrong path length")

                params['FORMAT'] = layer['mime_type']
        else:
            for param, value in self.request.params.items():
                params[param.upper()] = value

            if \
                    not 'SERVICE' in params or \
                    not 'REQUEST' in params or \
                    not 'VERSION' in params:
                raise HTTPBadRequest("Not all required parameters are present")

        if params['SERVICE'] != 'WMTS':
            raise HTTPBadRequest("Wrong Service '%s'" % params['SERVICE'])
        if params['VERSION'] != '1.0.0':
            raise HTTPBadRequest("Wrong Version '%s'" % params['VERSION'])

        if params['REQUEST'] == 'GetCapabilities':
            wmtscapabilities_file = self.cache['wmtscapabilities_file']
            self.request.response.body = self._get(wmtscapabilities_file)
            self.request.response.content_type = "application/xml"
            return self.request.response

        if \
                not 'FORMAT' in params or \
                not 'LAYER' in params or \
                not 'TILEMATRIXSET' in params or \
                not 'TILEMATRIX' in params or \
                not 'TILEROW' in params or \
                not 'TILECOL' in params:  # pragma: no cover
            raise HTTPBadRequest("Not all required parameters are present")

        if 'path' not in self.request.matchdict:
            if params['LAYER'] in self.layers:
                layer = self.tilegeneration.layers[params['LAYER']]
            else:
                raise HTTPBadRequest("Wrong Layer '%s'" % params['LAYER'])

            for dimension in layer['dimensions']:
                dimensions.append(
                    params[dimension['name'].upper()]
                    if dimension['name'].lower() in params
                    else dimension['default']
                )

        if params['STYLE'] != layer['wmts_style']:
            raise HTTPBadRequest("Wrong Style '%s'" % params['STYLE'])
        if params['TILEMATRIXSET'] != layer['grid']:
            raise HTTPBadRequest("Wrong TileMatrixSet '%s'" % params['TILEMATRIXSET'])

        tile = Tile(TileCoord(
            # TODO fix for matrix_identifier = resolution
            int(params['TILEMATRIX']),
            int(params['TILEROW']),
            int(params['TILECOL']),
        ))

        if params['REQUEST'] == 'GetFeatureInfo':
            if \
                    not 'I' in params or \
                    not 'J' in params or \
                    not 'INFO_FORMAT' in params:  # pragma: no cover
                raise HTTPBadRequest("Not all required parameters are present")
            if 'query_layers' in layer:
                responce, content = self.http.request(
                    layer['url'] + '?' + urlencode({
                        'SERVICE': 'WMS',
                        'VERSION': '1.1.1',
                        'REQUEST': 'GetFeatureInfo',
                        'LAYERS': ','.join(layer['layers']),
                        'QUERY_LAYERS': ','.join(layer['query_layers']),
                        'STYLES': params['STYLE'],
                        'FORMAT': params['FORMAT'],
                        'INFO_FORMAT': params['INFO_FORMAT'],
                        'WIDTH': layer['grid_ref']['tile_size'],
                        'HEIGHT': layer['grid_ref']['tile_size'],
                        'SRS': layer['grid_ref']['srs'],
                        'BBOX': layer['grid_ref']['obj'].extent(tile.tilecoord),
                        'X': params['I'],
                        'Y': params['J'],
                    }),
                )
                self.request.response.body = content
                self.request.response.content_type = responce['content-type']
                self.request.response.status = responce.status
                if responce.status < 300:
                    self.request.response.headers['Expires'] = \
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                    self.request.response.headers['Cache-Control'] = "max-age=" + str(3600 * self.expires_hours)
                return self.request.response
            else:  # pragma: no cover
                raise HTTPBadRequest("Layer '%s' not queryable" % layer['name'])

        if params['REQUEST'] != 'GetTile':
            raise HTTPBadRequest("Wrong Request '%s'" % params['REQUEST'])

        if params['FORMAT'] != layer['mime_type']:
            raise HTTPBadRequest("Wrong Format '%s'" % params['FORMAT'])

        if layer['name'] in self.filters:
            layer_filter = self.filters[layer['name']]
            if not layer_filter(tile):  # pragma: no cover
                responce, content = self.http.request(
                    self.mapcache_baseurl + '?' + urlencode(params),
                    headers=self.mapcache_header
                )
                self.request.response.body = content
                self.request.response.content_type = responce['content-type']
                self.request.response.status = responce.status
                if responce.status < 300:
                    self.request.response.headers['Expires'] = \
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                    self.request.response.headers['Cache-Control'] = "max-age=" + str(3600 * self.expires_hours)
                return self.request.response

        store_ref = '/'.join([params['LAYER']] + dimensions)
        if store_ref in self.stores:  # pragma: no cover
            store = self.stores[store_ref]
        else:  # pragma: no cover
            raise HTTPBadRequest(
                "No store found for layer '%s' and dimensions %s" % (
                    layer['name'], ', '.join(dimensions)
                )
            )

        tile = store.get_one(tile)
        if tile:
            if type(tile.data) == buffer:
                self.request.response.body_file = tile.data
            else:
                self.request.response.body = tile.data
            self.request.response.content_type = tile.content_type
            self.request.response.headers['Expires'] = \
                datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
            self.request.response.headers['Cache-Control'] = "max-age=" + str(3600 * self.expires_hours)
            return self.request.response
        else:
            raise HTTPNoContent()
