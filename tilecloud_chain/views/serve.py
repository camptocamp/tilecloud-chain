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

import logging

import httplib2

from tilecloud import Tile, TileCoord
from tilecloud.lib.s3 import S3Connection
from tilecloud_chain import TileGeneration, IntersectGeometryFilter

from pyramid.httpexceptions import HTTPBadRequest, HTTPNoContent


logger = logging.getLogger(__name__)


class Serve(TileGeneration):

    def __init__(self, request):
        self.request = request
        self.settings = request.registry.settings['tilegeneration']
        self.filters = {}
        self.http = httplib2.Http()

        self.tilegeneration = TileGeneration(self.settings['configfile'])
        self.cache = self.tilegeneration.caches[
            self.settings['cache'] if 'cache' in self.settings
            else self.tilegeneration.config['generation']['default_cache']
        ]
        self.stores = {}

    # get capabilities or legend files
    def _get(self, path):
        if self.cache['type'] == 's3':  # pragma: no cover
            s3bucket = S3Connection().bucket(self.cache['bucket'])
            s3key = s3bucket.key(('%(folder)s' % self.cache) + path)
            return s3key.get().body
        else:
            folder = self.cache['folder'] or ''
            with open(folder + path, 'rb') as file:
                data = file.read()
            return data

    def __call__(self):
        params = {}
        dimensions = None
        if 'path' in self.request.matchdict:
            path = self.request.matchdict['path']
            if len(path) < 7:
                wmtscapabilities_file = self.cache['wmtscapabilities_file']
                if '/'.join(path) == wmtscapabilities_file[1:]:
                    params['service'] = 'WMTS'
                    params['version'] = '1.0.0'
                    params['request'] = 'GetCapabilities'
                else:
                    raise HTTPBadRequest("Not enough path")
            else:
                params['service'] = 'WMTS'
                params['version'] = path[0]
                params['request'] = 'GetTile'

                last = path[-1].split('.')
                params['format'] = last[-1]
                params['layer'] = path[1]
                params['style'] = path[2]
                dimensions = [('Dimension', v) for v in path[3:-4]]
                params['tilematrixset'] = path[-4]
                params['tilematrix'] = path[-3]
                params['tilerow'] = path[-2]
                params['tilecol'] = last[0]
        else:
            for param, value in self.request.params.items():
                params[param.lower()] = value

            if \
                    not 'service' in params or \
                    not 'request' in params or \
                    not 'version' in params or \
                    not 'format' in params or \
                    not 'layer' in params or \
                    not 'tilematrixset' in params or \
                    not 'tilematrix' in params or \
                    not 'tilerow' in params or \
                    not 'tilecol' in params:
                raise HTTPBadRequest("Not all required parameters are present")

        if params['service'] != 'WMTS':
            raise HTTPBadRequest("Wrong Service '%s'" % params['service'])
        if params['version'] != '1.0.0':
            raise HTTPBadRequest("Wrong Version '%s'" % params['version'])

        if params['request'] == 'GetCapabilities':
            wmtscapabilities_file = self.cache['wmtscapabilities_file']
            self.request.response.body = self._get(wmtscapabilities_file)
            self.request.response.content_type = "application/xml"
            return self.request.response

        if params['request'] != 'GetTile':
            raise HTTPBadRequest("Wrong Request '%s'" % params['request'])

        if params['layer'] in self.tilegeneration.layers:
            layer = self.tilegeneration.layers[params['layer']]
        else:
            raise HTTPBadRequest("Wrong Layer '%s'" % params['layer'])

        if params['format'] != layer['extension']:
            raise HTTPBadRequest("Wrong Format '%s'" % params['format'])
        if params['style'] != layer['wmts_style']:
            raise HTTPBadRequest("Wrong Style '%s'" % params['style'])
        if params['tilematrixset'] != layer['grid']:
            raise HTTPBadRequest("Wrong TileMatrixSet '%s'" % params['tilematrixset'])

        tile = Tile(TileCoord(
            # TODO fix for matrix_identifier = resolution
            int(params['tilematrix']),
            int(params['tilerow']),
            int(params['tilecol']),
        ))

        store_ref = [
            params['layer'],
            params['style'],
            params['tilematrixset'],
            params['format'],
        ]

        if 'path' not in self.request.matchdict:
            dimensions = []
            for dimension in layer['dimensions']:
                value = \
                    params[dimension['name'].lower()] \
                    if dimension['name'].lower() in params \
                    else dimension['default']
                dimensions.append((dimension['name'], value))
                store_ref.extend((dimension['name'], value))

        if layer['name'] not in self.filters:
            self.filters[layer['name']] = IntersectGeometryFilter(
                grid=layer['grid_ref'],
                geoms=self.tilegeneration.get_geoms(layer),
                px_buffer=layer['px_buffer'] + layer['meta_buffer']
            )
        layer_filter = self.filters[layer['name']]
        if not layer_filter(tile):  # TODO integrate with mapcache
            url = 'base_url/' + '/'.join(['path'])
            self.http.request(url, headers={
                'Host': 'host'
            })

        store_ref = '/'.join(store_ref)
        if store_ref in self.stores:
            store = self.stores[store_ref]  # pragma: no cover
        else:
            store = self.tilegeneration.get_store(self.cache, layer, dimensions)

        tile = store.get_one(tile)
        if tile:
            if type(tile.data) == buffer:
                self.request.response.body_file = tile.data
            else:
                self.request.response.body = tile.data
            self.request.response.content_type = tile.content_type
            return self.request.response
        else:
            raise HTTPNoContent()
