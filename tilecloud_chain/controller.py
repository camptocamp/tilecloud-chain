# -*- coding: utf-8 -*-

import logging
import math
import os
import pkgutil
import sys
from argparse import ArgumentParser
from copy import copy
from hashlib import sha1
from io import BytesIO
from math import exp, log
from urllib.parse import urlencode, urljoin

import requests
import yaml
from bottle import jinja2_template
from c2cwsgiutils import stats
from PIL import Image

import tilecloud.store.s3
from tilecloud.lib.PIL_ import FORMAT_BY_CONTENT_TYPE
from tilecloud_chain import (TileGeneration, add_comon_options,
                             get_queue_store, get_tile_matrix_identifier)

logger = logging.getLogger(__name__)


def main():
    stats.init_backends({})
    parser = ArgumentParser(
        description='Used to generate the contextual file like the capabilities, the legends, '
        'the Apache and MapCache configuration',
        prog=sys.argv[0]
    )
    add_comon_options(parser, tile_pyramid=False, no_geom=False)
    parser.add_argument(
        '--status', default=False, action="store_true",
        help='Display the SQS queue status and exit'
    )
    parser.add_argument(
        '--capabilities', '--generate-wmts-capabilities', default=False, action='store_true',
        help='Generate the WMTS Capabilities'
    )
    parser.add_argument(
        '--legends', '--generate-legend-images', default=False, action='store_true', dest='legends',
        help='Generate the legend images'
    )
    parser.add_argument(
        '--openlayers', '--generate-openlayers-testpage', default=False,
        action='store_true', dest='openlayers',
        help='Generate openlayers test page'
    )
    parser.add_argument(
        '--mapcache', '--generate-mapcache-config', default=False, action='store_true', dest='mapcache',
        help='Generate MapCache configuration file'
    )
    parser.add_argument(
        '--mapcache-version', default='1.4', choices=('1.4', '1.6'),
        help='The used version of MapCache'
    )
    parser.add_argument(
        '--apache', '--generate-apache-config', default=False, action='store_true', dest='apache',
        help='Generate Apache configuration file'
    )
    parser.add_argument(
        '--dump-config', default=False, action='store_true',
        help='Dump the used config with default values and exit'
    )

    options = parser.parse_args()
    gene = TileGeneration(options.config, options, layer_name=options.layer)

    if options.status:  # pragma: no cover
        status(gene)
        sys.exit(0)

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']

    if options.dump_config:
        for layer in gene.config['layers'].values():
            gene.init_layer(layer, options)
        _validate_generate_wmts_capabilities(gene.caches[options.cache], True)
        for grid in gene.config['grids'].values():
            if 'obj' in grid:
                del grid['obj']
        print(yaml.dump(gene.config))
        sys.exit(0)

    if options.legends:
        _generate_legend_images(gene)

    if options.capabilities:
        _generate_wmts_capabilities(gene)

    if options.mapcache:
        _generate_mapcache_config(gene, options.mapcache_version)

    if options.apache:
        _generate_apache_config(gene)

    if options.openlayers:
        _generate_openlayers(gene)


def _send(data, path, mime_type, cache):
    if cache['type'] == 's3':  # pragma: no cover
        client = tilecloud.store.s3.get_client(cache.get('host'))
        key_name = os.path.join('{folder!s}'.format(**cache), path)
        bucket = cache['bucket']
        client.put_object(ACL='public-read', Body=data, Key=key_name, Bucket=bucket, ContentEncoding='utf-8',
                          ContentType=mime_type)
    else:
        if isinstance(data, str):
            data = data.encode('utf-8')

        folder = cache['folder'] or ''
        filename = os.path.join(folder, path)
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filename, 'wb') as f:
            f.write(data)


def _get(path, cache):
    if cache['type'] == 's3':  # pragma: no cover
        client = tilecloud.store.s3.get_client(cache.get('host'))
        key_name = os.path.join('{folder!s}'.format(**cache), path)
        bucket = cache['bucket']
        response = client.get_object(Bucket=bucket, Key=key_name)
        return response['Body'].read()
    else:
        p = os.path.join(cache['folder'], path)
        if not os.path.isfile(p):  # pragma: no cover
            return None
        with open(p, 'rb') as file:
            return file.read()


def _validate_generate_wmts_capabilities(cache, exit_):
    if 'http_url' not in cache and 'http_urls' not in cache:  # pragma: no cover
        logger.error(
            "The attribute 'http_url' or 'http_urls' is required in the object cache[{}].".format(
                cache['name']
            )
        )
        if exit_:
            exit(1)
        return False
    return True


def get_wmts_capabilities(gene, cache, exit_=False):
    if _validate_generate_wmts_capabilities(cache, exit_):
        server = gene.config.get('server')

        base_urls = _get_base_urls(cache)
        _fill_legend(gene, cache, server, base_urls)

        return jinja2_template(
            pkgutil.get_data("tilecloud_chain", "wmts_get_capabilities.jinja").decode('utf-8'),
            layers=gene.layers,
            grids=gene.grids,
            getcapabilities=urljoin(base_urls[0], (
                server.get('wmts_path', 'wmts') + '/1.0.0/WMTSCapabilities.xml' if server
                else cache.get('wmtscapabilities_file', '1.0.0/WMTSCapabilities.xml')
            )),
            base_urls=base_urls,
            base_url_postfix=(server.get('wmts_path', 'wmts') + '/') if server else '',
            get_tile_matrix_identifier=get_tile_matrix_identifier,
            server=server is not None,
            has_metadata=gene.metadata is not None,
            metadata=gene.metadata,
            has_provider=gene.provider is not None,
            provider=gene.provider,
            enumerate=enumerate, ceil=math.ceil, int=int, sorted=sorted,
        )


def _get_base_urls(cache):
    base_urls = []
    if 'http_url' in cache:
        if 'hosts' in cache:
            cc = copy(cache)
            for host in cache['hosts']:
                cc['host'] = host
                base_urls.append(cache['http_url'] % cc)
        else:
            base_urls = [cache['http_url'] % cache]
    if 'http_urls' in cache:
        base_urls = [url % cache for url in cache['http_urls']]
    base_urls = [url + '/' if url[-1] != '/' else url for url in base_urls]
    return base_urls


def _fill_legend(gene, cache, server, base_urls):
    for layer in gene.layers.values():
        previous_legend = None
        previous_resolution = None
        if 'legend_mime' in layer and 'legend_extention' in layer and 'legends' not in layer:
            layer['legends'] = []
            for zoom, resolution in enumerate(layer['grid_ref']['resolutions']):
                path = '/'.join(['1.0.0', layer['name'], layer['wmts_style'], 'legend{}.{}'.format(
                    zoom,
                    layer['legend_extention']
                )])
                img = _get(path, cache)
                if img is not None:
                    new_legend = {
                        'mime_type': layer['legend_mime'],
                        'href': os.path.join(
                            base_urls[0],
                            server.get('static_path', 'static') + '/' if server else '',
                            path
                        ),
                    }
                    layer['legends'].append(new_legend)
                    if previous_legend is not None:
                        middle_res = exp((log(previous_resolution) + log(resolution)) / 2)
                        previous_legend['min_resolution'] = middle_res
                        new_legend['max_resolution'] = middle_res
                    try:
                        pil_img = Image.open(BytesIO(img))
                        new_legend['width'] = pil_img.size[0]
                        new_legend['height'] = pil_img.size[1]
                    except Exception:  # pragma: nocover
                        logger.warning("Unable to read legend image '{}', with '{}'".format(
                            path, repr(img)), exc_info=True)
                    previous_legend = new_legend
                previous_resolution = resolution


def _generate_wmts_capabilities(gene):
    cache = gene.caches[gene.options.cache]

    capabilities = get_wmts_capabilities(gene, cache, True)
    _send(
        capabilities,
        cache.get('wmtscapabilities_file', '1.0.0/WMTSCapabilities.xml'),
        'application/xml',
        cache,
    )


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
                    for l in layer['layers'].split(','):
                        response = session.get(layer['url'] + '?' + urlencode({
                            'SERVICE': 'WMS',
                            'VERSION': layer['version'],
                            'REQUEST': 'GetLegendGraphic',
                            'LAYER': l,
                            'FORMAT': layer['legend_mime'],
                            'TRANSPARENT': 'TRUE' if layer['legend_mime'] == 'image/png' else 'FALSE',
                            'STYLE': layer['wmts_style'],
                            'SCALE': resolution / 0.00028
                        }))
                        try:
                            legends.append(Image.open(BytesIO(response.content)))
                        except Exception:  # pragma: nocover
                            logger.warning(
                                "Unable to read legend image for layer '{}'-'{}', resolution '{}': {}".format(
                                    layer['name'], l, resolution, response.content
                                ), exc_info=True
                            )
                    width = max(i.size[0] for i in legends)
                    height = sum(i.size[1] for i in legends)
                    image = Image.new('RGBA', (width, height))
                    y = 0
                    for i in legends:
                        image.paste(i, (0, y))
                        y += i.size[1]
                    string_io = BytesIO()
                    image.save(string_io, FORMAT_BY_CONTENT_TYPE[layer['legend_mime']])
                    result = string_io.getvalue()
                    new_hash = sha1(result).hexdigest()
                    if new_hash != previous_hash:
                        previous_hash = new_hash
                        _send(
                            result,
                            '1.0.0/{}/{}/legend{}.{}'.format(
                                layer['name'],
                                layer['wmts_style'],
                                zoom,
                                layer['legend_extention']
                            ),
                            layer['legend_mime'],
                            cache
                        )


def _generate_mapcache_config(gene, version):
    for layer in gene.layers.values():
        if layer['type'] == 'wms' or 'wms_url' in layer:
            params = {}
            params.update(layer.get('params', {}))
            if 'FORMAT' not in params:
                params['FORMAT'] = layer['mime_type']
            if 'LAYERS' not in layer.get('params', {}):
                params['LAYERS'] = layer['layers']
            if 'TRANSPARENT' not in layer.get('params', {}):
                params['TRANSPARENT'] = 'TRUE' \
                    if layer['mime_type'] == 'image/png' else 'FALSE'
            layer['params'] = params

    config = jinja2_template(
        pkgutil.get_data("tilecloud_chain", "mapcache_config.jinja").decode('utf-8'),
        layers=gene.layers,
        grids=gene.grids,
        mapcache=gene.config['mapcache'],
        version=version,
        min=min,
        len=len,
        sorted=sorted,
    )

    with open(gene.config['mapcache']['config_file'], 'w') as f:
        f.write(config)


def _generate_apache_config(gene):
    cache = gene.caches[gene.options.cache]
    use_server = 'server' in gene.config

    with open(gene.config['apache']['config_file'], 'w') as f:

        folder = cache['folder']
        if folder and folder[-1] != '/':
            folder += '/'

        if not use_server:
            f.write("""
    <Location {location!s}>
        ExpiresActive on
        ExpiresDefault "now plus {expires} hours"
    {headers!s}
    </Location>
    """.format(**{
                'location': gene.config['apache']['location'],
                'expires': gene.config['apache']['expires'],
                'headers': ''.join([
                    '    Header set {} "{}"'.format(*h)
                    for h in gene.config['apache'].get('headers', {
                        'Cache-Control': 'max-age=864000, public'
                    }).items()
                ]),
            }))
            if cache['type'] == 's3':
                tiles_url = (cache['tiles_url'] % cache) if 'tiles_url' in cache else \
                    'http://s3-{region!s}.amazonaws.com/{bucket!s}/{folder!s}'.format(**{
                        'region': cache['region'],
                        'bucket': cache['bucket'],
                        'folder': folder
                    })
                f.write(
                    """
    <Proxy {tiles_url!s}*>
        Order deny,allow
        Allow from all
    </Proxy>
    ProxyPass {location!s}/ {tiles_url!s}
    ProxyPassReverse {location!s}/ {tiles_url!s}
    """.format(**{
                        'location': gene.config['apache']['location'],
                        'tiles_url': tiles_url,
                    })
                )
            elif cache['type'] == 'filesystem':
                f.write(
                    """
    Alias {location!s} {files_folder!s}
    """.format(**{
                        'location': gene.config['apache']['location'],
                        'files_folder': folder,
                        'headers': ''.join([
                            "    Header set {} '{}'".format(*h)
                            for h in gene.config['apache'].get('headers', {
                                'Cache-Control': 'max-age=864000, public'
                            }).items()
                        ]),
                    })
                )

        use_mapcache = 'mapcache' in gene.config
        if use_mapcache and not use_server:
            token_regex = r'([a-zA-Z0-9_\-\+~\.]+)'
            f.write('\n')

            for _, layer in sorted(gene.config['layers'].items()):
                if 'min_resolution_seed' in layer:
                    res = [r for r in layer['grid_ref']['resolutions'] if r < layer['min_resolution_seed']]
                    dim = len(layer['dimensions'])
                    for r in res:
                        f.write(
                            'RewriteRule'
                            ' '
                            '^%(tiles_location)s/1.0.0/%(layer)s/%(token_regex)s'  # Baseurl/layer/Style
                            '%(dimensions_re)s'  # Dimensions : variable number of values
                            # TileMatrixSet/TileMatrix/TileRow/TileCol.extension
                            '/%(token_regex)s/%(zoom)s/(.*)$'
                            ' '
                            '%(mapcache_location)s/wmts/1.0.0/%(layer)s/$1'
                            '%(dimensions_rep)s'
                            '/$%(tilematrixset)s/%(zoom)s/$%(final)s'
                            ' '
                            '[PT]\n' % {
                                'tiles_location': gene.config['apache']['location'],
                                'mapcache_location': gene.config['mapcache']['location'],
                                'layer': layer['name'],
                                'token_regex': token_regex,
                                'dimensions_re': ''.join(['/' + token_regex for e in range(dim)]),
                                'dimensions_rep': ''.join(['/${}'.format((e + 2)) for e in range(dim)]),
                                'tilematrixset': dim + 2,
                                'final': dim + 3,
                                'zoom': layer['grid_ref']['resolutions'].index(r)
                            }
                        )

        if use_mapcache:
            f.write("""
    MapCacheAlias {mapcache_location!s} "{mapcache_config!s}"
    """.format(**{
                'mapcache_location': gene.config['mapcache']['location'],
                'mapcache_config': os.path.abspath(gene.config['mapcache']['config_file'])
            }))


def _get_resource(resource):
    path = os.path.join(os.path.dirname(__file__), resource)
    with open(path, 'rb') as f:
        return f.read()


def _generate_openlayers(gene):
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

    js = jinja2_template(
        pkgutil.get_data("tilecloud_chain", "openlayers.js").decode('utf-8'),
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
            } for name, layer in sorted(gene.layers.items())
            if layer['grid_ref']['srs'] == gene.config['openlayers']['srs']
        ],
        sorted=sorted,
    )

    _send(
        pkgutil.get_data("tilecloud_chain", "openlayers.html"),
        'index.html', 'text/html', cache
    )
    _send(js, 'wmts.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers.js'), 'OpenLayers.js', 'application/javascript', cache)
    _send(_get_resource('OpenLayers-style.css'), 'theme/default/style.css', 'text/css', cache)
    _send(_get_resource('layer-switcher-maximize.png'), 'img/layer-switcher-maximize.png', 'image/png', cache)
    _send(_get_resource('layer-switcher-minimize.png'), 'img/layer-switcher-minimize.png', 'image/png', cache)


def status(gene):  # pragma: no cover
    print('\n'.join(get_status(gene)))


def get_status(gene):
    store = get_queue_store(gene.config, False)
    kind = 'redis' if 'redis' in gene.config else 'sqs'
    stats_prefix = [kind, gene.config[kind]['queue']]
    with stats.timer_context(stats_prefix + ['get_stats']):
        status = store.get_status()
    return [name + ': ' + str(value) for name, value in status.items()]
