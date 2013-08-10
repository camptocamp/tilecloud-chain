# -*- coding: utf-8 -*-

import os
import sys
import math
import logging
import yaml
from copy import copy
from argparse import ArgumentParser

from bottle import jinja2_template
from tilecloud.lib.s3 import S3Connection

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
        help='Generate the WMTS Capabilities and exit'
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
    if options.capabilities:
        _generate_wmts_capabilities(gene, options)
        sys.exit(0)

    if options.mapcache:
        _generate_mapcache_config(gene)
        sys.exit(0)

    if options.apache:
        _generate_apache_config(gene, options)
        sys.exit(0)

    if options.openlayers:
        _generate_openlayers(gene, options)
        sys.exit(0)

    if options.dump_config:
        for layer in gene.config['layers'].keys():
            gene.set_layer(layer, options)
            validate_calculate_cost(gene)
        _validate_generate_wmts_capabilities(gene, gene.caches[options.cache])
        gene.validate_mapcache_config()
        gene.validate_apache_config()
        _validate_generate_openlayers(gene)
        for grild in gene.config['grids'].values():
            del grild['obj']
        print yaml.dump(gene.config)
        sys.exit(0)


def _send(data, path, mime_type, cache):
    if cache['type'] == 's3':  # pragma: no cover
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key(('%(folder)s' % cache) + path)
        s3key.body = data
        s3key['Content-Encoding'] = 'utf-8'
        s3key['Content-Type'] = mime_type
        s3key.put()
    else:
        folder = cache['folder'] or ''
        filename = folder + path
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        f = open(folder + path, 'wb')
        f.write(data)
        f.close()


def _validate_generate_wmts_capabilities(gene, cache):
    error = False
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_url', attribute_type=str, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_urls', attribute_type=list, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'hosts', attribute_type=list, default=False) or error
    if not cache['http_url'] and not cache['http_urls']:
        logger.error(
            "The attribute 'http_url' or 'http_urls' is required in the object %s." %
            ('cache[%s]' % cache['name'])
        )  # pragma: no cover
        error = True  # pragma: no cover
    if error:
        exit(1)  # pragma: no cover


def _generate_wmts_capabilities(gene, options):
    from tilecloud_chain.wmts_get_capabilities_template import wmts_get_capabilities_template

    cache = gene.caches[options.cache]
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

    capabilities = jinja2_template(
        wmts_get_capabilities_template,
        layers=gene.layers,
        grids=gene.grids,
        getcapabilities=base_urls[0] + (
            '/1.0.0/WMTSCapabilities.xml' if server
            else cache['wmtscapabilities_file']),
        base_urls=base_urls,
        get_tile_matrix_identifier=get_tile_matrix_identifier,
        server=server,
        enumerate=enumerate, ceil=math.ceil, int=int
    )

    _send(capabilities, cache['wmtscapabilities_file'], 'application/xml', cache)


def _generate_mapcache_config(gene):
    from tilecloud_chain.mapcache_config_template import mapcache_config_template

    if not gene.validate_mapcache_config():
        exit(1)  # pragma: no cover

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


def _generate_apache_config(gene, options):
    if not gene.validate_apache_config():
        exit(1)  # pragma: no cover

    cache = gene.caches[options.cache]
    use_server = 'server' in gene.config

    f = open(gene.config['apache']['config_file'], 'w')

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
                'folder': cache['folder']
            })
        elif cache['type'] == 'filesystem':
            f.write("""
Alias %(location)s %(files_folder)s
""" % {
                'location': gene.config['apache']['location'],
                'files_folder': cache['folder']
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
                    f.write("""RewriteRule ^%(tiles_location)s/1.0.0/%(layer)s/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/"""
                            """%(dimensions_re)s/%(zoom)s/(.*)$ %(mapcache_location)s/wmts/1.0.0/%(layer)s/$1/$2/"""
                            """%(dimensions_rep)s/%(zoom)s/%(final)s [PT]
""" % {
                        'tiles_location': gene.config['apache']['location'],
                        'mapcache_location': gene.config['mapcache']['location'],
                        'layer': layer['name'],
                        'dimensions_re': '/'.join(['([a-zA-Z0-9_]+)' for e in range(dim)]),
                        'dimensions_rep': '/'.join(['$%i' % (e + 3) for e in range(dim)]),
                        'final': '$%i' % (3 + dim),
                        'zoom': layer['grid_ref']['resolutions'].index(r)
                    })

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


def _generate_openlayers(gene, options):
    from tilecloud_chain.openlayers_html import openlayers_html
    from tilecloud_chain.openlayers_js import openlayers_js

    _validate_generate_openlayers(gene)

    cache = gene.caches[options.cache]

    http_url = ''
    if 'http_url' in cache:
        if 'hosts' in cache:
            cc = copy(cache)
            cc['host'] = cache['hosts'][0]
            http_url = cache['http_url'] % cc
        else:
            http_url = cache['http_url'] % cache
    if 'http_urls' in cache:
        http_url = cache['http_urls'][0] % cache

    js = jinja2_template(
        openlayers_js,
        srs=gene.config['openlayers']['srs'],
        center_x=gene.config['openlayers']['center_x'],
        center_y=gene.config['openlayers']['center_y'],
        http_url=http_url,
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

    _send(openlayers_html, '/index.html', 'text/html', cache)
    _send(js, '/wmts.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers.js'), '/OpenLayers.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers-style.css'), '/theme/default/style.css', 'text/css', cache)
    _send(_get_resource('layer-switcher-maximize.png'), '/img/layer-switcher-maximize.png', 'image/png', cache)
    _send(_get_resource('layer-switcher-minimize.png'), '/img/layer-switcher-minimize.png', 'image/png', cache)
