# -*- coding: utf-8 -*-

import os
import sys
import math
import logging
import yaml
from math import exp, log
from copy import copy
from argparse import ArgumentParser
from hashlib import sha1
from urllib import urlencode
from cStringIO import StringIO

import requests
from bottle import jinja2_template
from PIL import Image
from tilecloud.lib.s3 import S3Connection
from tilecloud.lib.PIL_ import FORMAT_BY_CONTENT_TYPE

from tilecloud_chain import TileGeneration, add_comon_options, get_tile_matrix_identifier
from tilecloud_chain.cost import validate_calculate_cost


logger = logging.getLogger(__name__)


def main():
    parser = ArgumentParser(
        description='Used to generate the contextual file like the capabilities, the legends, '
        'the Apache and MapCache configuration',
        prog='./buildout/bin/generate_controller'
    )
    add_comon_options(parser, tile_pyramid=False, no_geom=False)
    parser.add_argument(
        '--capabilities', '--generate_wmts_capabilities', default=False, action="store_true",
        help='Generate the WMTS Capabilities'
    )
    parser.add_argument(
        '--legends', '--generate_legend_images', default=False, action="store_true", dest='legends',
        help='Generate the legend images'
    )
    parser.add_argument(
        '--openlayers', '--generate-openlayers-test-page', default=False,
        action="store_true", dest='openlayers',
        help='Generate openlayers test page'
    )
    parser.add_argument(
        '--mapcache', '--generate-mapcache-config', default=False, action="store_true", dest='mapcache',
        help='Generate MapCache configuration file'
    )
    parser.add_argument(
        '--apache', '--generate-apache-config', default=False, action="store_true", dest='apache',
        help='Generate Apache configuration file'
    )
    parser.add_argument(
        '--dump-config', default=False, action="store_true",
        help='Dump the used config with default values and exit'
    )

    options = parser.parse_args()
    gene = TileGeneration(options.config, options, layer_name=options.layer)

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if options.dump_config:
        for layer in gene.config['layers'].keys():
            gene.set_layer(layer, options)
            validate_calculate_cost(gene)
        _validate_generate_wmts_capabilities(gene, gene.caches[options.cache])
        gene.validate_mapcache_config()
        gene.validate_apache_config()
        _validate_generate_openlayers(gene)
        for grid in gene.config['grids'].values():
            if 'obj' in grid:
                del grid['obj']
        print yaml.dump(gene.config)
        sys.exit(0)

    if options.legends:
        _generate_legend_images(gene)

    if options.capabilities:
        _generate_wmts_capabilities(gene)

    if options.mapcache:
        _generate_mapcache_config(gene)

    if options.apache:
        _generate_apache_config(gene)

    if options.openlayers:
        _generate_openlayers(gene)


def _send(data, path, mime_type, cache):
    if cache['type'] == 's3':  # pragma: no cover
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key(os.path.join('%(folder)s' % cache, path))
        s3key.body = data
        s3key['Content-Encoding'] = 'utf-8'
        s3key['Content-Type'] = mime_type
        s3key.put()
    else:
        folder = cache['folder'] or ''
        filename = os.path.join(folder, path)
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        f = open(filename, 'wb')
        f.write(data)
        f.close()


def _get(path, cache):
    if cache['type'] == 's3':  # pragma: no cover
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key(os.path.join('%(folder)s' % cache, path))
        return s3key.get().body
    else:
        p = os.path.join(cache['folder'], path)
        if not os.path.isfile(p):  # pragma: no cover
            return None
        with open(p, 'rb') as file:
            return file.read()


def _validate_generate_wmts_capabilities(gene, cache):
    error = False
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_url', attribute_type=str, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_urls', attribute_type=list, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'hosts', attribute_type=list, default=False) or error
    if not cache['http_url'] and not cache['http_urls']:  # pragma: no cover
        logger.error(
            "The attribute 'http_url' or 'http_urls' is required in the object %s." %
            ('cache[%s]' % cache['name'])
        )
        error = True
    if cache['http_url'] and cache['http_url'][-1] == '/':  # pragma: no cover
        logger.error(
            "The attribute 'http_url' shouldn't ends with a '/' in the object %s." %
            ('cache[%s]' % cache['name'])
        )
        error = True
    elif cache['http_urls']:
        for url in cache['http_urls']:
            if url[-1] == '/':  # pragma: no cover
                logger.error(
                    "The element '%s' of the attribute 'http_urls' shouldn't ends"
                    " with a '/' in the object %s." %
                    ('cache[%s]' % cache['name'])
                )
                error = True

    if error:  # pragma: no cover
        exit(1)


def _generate_wmts_capabilities(gene):
    from tilecloud_chain.wmts_get_capabilities_template import wmts_get_capabilities_template

    cache = gene.caches[gene.options.cache]
    _validate_generate_wmts_capabilities(gene, cache)
    server = 'server' in gene.config

    base_urls = []
    if cache['http_url']:
        if cache['hosts']:
            cc = copy(cache)
            for host in cache['hosts']:
                cc['host'] = host
                base_urls.append(cache['http_url'] % cc)
        else:
            base_urls = [cache['http_url'] % cache]
    if cache['http_urls']:
        base_urls = [url % cache for url in cache['http_urls']]

    base_urls = [url + '/' if url[-1] != '/' else url for url in base_urls]

    for layer in gene.layers.values():
        previous_legend = None
        previous_resolution = None
        if 'legend_mime' in layer and 'legend_extention' in layer and 'legends' not in layer:
            layer['legends'] = []
            for zoom, resolution in enumerate(layer['grid_ref']['resolutions']):
                path = '/'.join(['1.0.0', layer['name'], layer['wmts_style'], 'legend%s.%s' % (
                    zoom,
                    layer['legend_extention']
                )])
                img = _get(path, cache)
                if img is not None:
                    new_legend = {
                        'mime_type': layer['legend_mime'],
                        'href': os.path.join(base_urls[0], 'static/' if server else '', path),
                    }
                    layer['legends'].append(new_legend)
                    if previous_legend is not None:
                        middle_res = exp((log(previous_resolution) + log(resolution)) / 2)
                        previous_legend['min_resolution'] = middle_res
                        new_legend['max_resolution'] = middle_res
                    try:
                        pil_img = Image.open(StringIO(img))
                        new_legend['width'] = pil_img.size[0]
                        new_legend['height'] = pil_img.size[1]
                    except:  # pragma: nocover
                        logger.warn("Unable to read legend image '%s', with '%r'" % (path, img))
                    previous_legend = new_legend
                previous_resolution = resolution

    capabilities = jinja2_template(
        wmts_get_capabilities_template,
        layers=gene.layers,
        grids=gene.grids,
        getcapabilities=base_urls[0] + (
            'wmts/1.0.0/WMTSCapabilities.xml' if server
            else cache['wmtscapabilities_file']),
        base_urls=base_urls,
        base_url_postfix='wmts/' if server else '',
        get_tile_matrix_identifier=get_tile_matrix_identifier,
        server=server,
        enumerate=enumerate, ceil=math.ceil, int=int
    )

    _send(capabilities, cache['wmtscapabilities_file'], 'application/xml', cache)


def _generate_legend_images(gene):
    cache = gene.caches[gene.options.cache]

    for layer in gene.layers.values():
        if 'legend_mime' in layer and 'legend_extention' in layer:
            if layer['type'] == 'wms':
                session = requests.session()
                session.headers.update(layer['headers'])
                previous_hash = None
                for zoom, resolution in enumerate(layer['grid_ref']['resolutions']):
                    legends = []
                    for l in layer['layers']:
                        response = session.get(layer['url'] + '?' + urlencode({
                            'SERVICE': 'WMS',
                            'VERSION': '1.1.1',
                            'REQUEST': 'GetLegendGraphic',
                            'LAYER': l,
                            'FORMAT': layer['legend_mime'],
                            'TRANSPARENT': 'TRUE' if layer['legend_mime'] == 'image/png' else 'FALSE',
                            'STYLE': layer['wmts_style'],
                            'SCALE': resolution / 0.00028
                        }))
                        try:
                            legends.append(Image.open(StringIO(response.content)))
                        except:  # pragma: nocover
                            logger.warn(
                                "Unable to read legend image for layer '%s', resolution '%i': %r" % (
                                    layer['name'], resolution, response.content
                                )
                            )
                    width = max(i.size[0] for i in legends)
                    height = sum(i.size[1] for i in legends)
                    image = Image.new("RGBA", (width, height))
                    y = 0
                    for i in legends:
                        image.paste(i, (0, y))
                        y += i.size[1]
                    string_io = StringIO()
                    image.save(string_io, FORMAT_BY_CONTENT_TYPE[layer['legend_mime']])
                    result = string_io.getvalue()
                    new_hash = sha1(result).hexdigest()
                    if new_hash != previous_hash:
                        previous_hash = new_hash
                        _send(
                            result,
                            '1.0.0/%s/%s/legend%s.%s' % (
                                layer['name'],
                                layer['wmts_style'],
                                zoom,
                                layer['legend_extention']
                            ),
                            layer['legend_mime'],
                            cache
                        )


def _generate_mapcache_config(gene):
    from tilecloud_chain.mapcache_config_template import mapcache_config_template

    if not gene.validate_mapcache_config():
        exit(1)  # pragma: no cover

    for layer in gene.layers.values():
        if layer['type'] == 'wms' or 'wms_url' in layer:
            if 'FORMAT' not in layer['params']:
                layer['params']['FORMAT'] = layer['mime_type']
            if 'LAYERS' not in layer['params']:
                layer['params']['LAYERS'] = ','.join(layer['layers'])
            if 'TRANSPARENT' not in layer['params']:
                layer['params']['TRANSPARENT'] = 'TRUE' if layer['mime_type'] == 'image/png' else 'FALSE'
    config = jinja2_template(
        mapcache_config_template,
        layers=gene.layers,
        grids=gene.grids,
        mapcache=gene.config['mapcache'],
        min=min
    )

    f = open(gene.config['mapcache']['config_file'], 'w')
    f.write(config)
    f.close()


def _generate_apache_config(gene):
    if not gene.validate_apache_config():
        exit(1)  # pragma: no cover

    cache = gene.caches[gene.options.cache]
    use_server = 'server' in gene.config

    f = open(gene.config['apache']['config_file'], 'w')

    folder = cache['folder']
    if folder and folder[-1] != '/':
        folder += '/'

    if not use_server:
        f.write("""<Location %(location)s>
    ExpiresActive on
    ExpiresDefault "now plus %(expires)i hours"
</Location>
""" % {
            'location': gene.config['apache']['location'],
            'expires': gene.config['apache']['expires']
        })
        if cache['type'] == 's3':
            f.write("""
<Proxy http://s3-%(region)s.amazonaws.com/%(bucket)s/%(folder)s*>
    Order deny,allow
    Allow from all
</Proxy>
ProxyPass %(location)s/ http://s3-%(region)s.amazonaws.com/%(bucket)s/%(folder)s
ProxyPassReverse %(location)s/ http://s3-%(region)s.amazonaws.com/%(bucket)s/%(folder)s
""" % {
                'location': gene.config['apache']['location'],
                'region': cache['region'],
                'bucket': cache['bucket'],
                'folder': folder
            })
        elif cache['type'] == 'filesystem':
            f.write("""
Alias %(location)s %(files_folder)s
""" % {
                'location': gene.config['apache']['location'],
                'files_folder': folder
            })

    use_mapcache = 'mapcache' in gene.config
    if use_mapcache:
        if not gene.validate_mapcache_config():
            exit(1)  # pragma: no cover
    if use_mapcache and not use_server:
        f.write("\n")
        for l in gene.config['layers']:
            layer = gene.config['layers'][l]
            if 'min_resolution_seed' in layer:
                res = [r for r in layer['grid_ref']['resolutions'] if r < layer['min_resolution_seed']]
                dim = len(layer['dimensions'])
                for r in res:
                    f.write(
                        """RewriteRule ^%(tiles_location)s/1.0.0/%(layer)s/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/"""
                        """%(dimensions_re)s/%(zoom)s/(.*)$ %(mapcache_location)s/wmts/1.0.0/%(layer)s/$1/$2/"""
                        """%(dimensions_rep)s/%(zoom)s/%(final)s [PT]\n""" % {
                            'tiles_location': gene.config['apache']['location'],
                            'mapcache_location': gene.config['mapcache']['location'],
                            'layer': layer['name'],
                            'dimensions_re': '/'.join(['([a-zA-Z0-9_]+)' for e in range(dim)]),
                            'dimensions_rep': '/'.join(['$%i' % (e + 3) for e in range(dim)]),
                            'final': '$%i' % (3 + dim),
                            'zoom': layer['grid_ref']['resolutions'].index(r)
                        }
                    )

    if use_mapcache:
        f.write("""
MapCacheAlias %(mapcache_location)s "%(mapcache_config)s"
""" % {
            'mapcache_location': gene.config['mapcache']['location'],
            'mapcache_config': os.path.abspath(gene.config['mapcache']['config_file'])
        })

    f.close()


def _validate_generate_openlayers(gene):
    error = False
    error = gene.validate(gene.config, 'config', 'openlayers', attribute_type=dict, default={}) or error
    error = gene.validate(
        gene.config['openlayers'], 'openlayers', 'srs',
        attribute_type=str, default='EPSG:21781'
    ) or error
    error = gene.validate(
        gene.config['openlayers'], 'openlayers', 'center_x',
        attribute_type=float, default=600000
    ) or error
    error = gene.validate(
        gene.config['openlayers'], 'openlayers', 'center_y',
        attribute_type=float, default=200000
    ) or error
    if error:
        exit(1)  # pragma: no cover


def _get_resource(ressource):
    path = os.path.join(os.path.dirname(__file__), ressource)
    f = open(path)
    data = f.read()
    f.close()
    return data


def _generate_openlayers(gene):
    from tilecloud_chain.openlayers_html import openlayers_html
    from tilecloud_chain.openlayers_js import openlayers_js

    _validate_generate_openlayers(gene)

    cache = gene.caches[gene.options.cache]

    http_url = ''
    if 'http_url' in cache and cache['http_url']:
        if 'hosts' in cache and cache['hosts']:
            cc = copy(cache)
            cc['host'] = cache['hosts'][0]
            http_url = cache['http_url'] % cc
        else:
            http_url = cache['http_url'] % cache
    if 'http_urls' in cache and cache['http_urls']:
        http_url = cache['http_urls'][0] % cache

    if http_url and http_url[-1] != '/':
        http_url += '/'

    js = jinja2_template(
        openlayers_js,
        srs=gene.config['openlayers']['srs'],
        center_x=gene.config['openlayers']['center_x'],
        center_y=gene.config['openlayers']['center_y'],
        http_url=http_url + ('wmts/' if 'server' in gene.config else ''),
        layers=[
            {
                'name': name,
                'grid': layer['type'] == 'mapnik' and layer['output_format'] == 'grid',
                'maxExtent': layer['grid_ref']['bbox'],
                'resolution': layer['resolution'] if
                layer['type'] == 'mapnik' and layer['output_format'] == 'grid' else None,
            } for name, layer in gene.layers.items() if layer['grid_ref']['srs'] == gene.config['openlayers']['srs']
        ]
    )

    _send(openlayers_html, 'index.html', 'text/html', cache)
    _send(js, 'wmts.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers.js'), 'OpenLayers.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers-style.css'), 'theme/default/style.css', 'text/css', cache)
    _send(_get_resource('layer-switcher-maximize.png'), 'img/layer-switcher-maximize.png', 'image/png', cache)
    _send(_get_resource('layer-switcher-minimize.png'), 'img/layer-switcher-minimize.png', 'image/png', cache)
