# -*- coding: utf-8 -*-

import sys
import math
import logging
import ConfigParser
import urllib2
import simplejson
from datetime import timedelta
from cStringIO import StringIO
from subprocess import call
from optparse import OptionParser
from PIL import Image
from tilecloud.lib.PIL_ import FORMAT_BY_CONTENT_TYPE
from bottle import jinja2_template
from tilecloud import BoundingPyramid, Tile, TileStore, consume
from tilecloud.store.metatile import MetaTileSplitterTileStore
from tilecloud.lib.s3 import S3Connection

from tilecloud_chain import TileGeneration


def main():
    parser = OptionParser(
        'Used to generete the tiles present in the SQS queue')
    parser.add_option('-c', '--config', default='tilegeneration/config.yaml',
            help='path to the configuration file')
    parser.add_option('-d', '--deploy-config',
            default=None, dest="deploy_config",
            help='path to the deploy configuration file')
    parser.add_option('-b', '--bbox',
            help='restrict to specified bounding box')
    parser.add_option('-z', '--zoom-level', type='int',
            help='restrict to specified zoom level')
    parser.add_option('-l', '--layer',
            help='the layer to generate')
    parser.add_option('-t', '--test', type='int', default=None,
            help='test with generating TEST tiles, and add log messages')
    parser.add_option('-s', '--status', default=False,
            action="store_true",
            help='display status and exit')
    parser.add_option('-S', '--disable-sync', default=True,
            action="store_false", dest="sync",
            help='disable geodata synchronisation')
    parser.add_option('-C', '--disable-code', default=True,
            action="store_false", dest="deploy_code",
            help='disable deploy application code')
    parser.add_option('-D', '--disable-database', default=True,
            action="store_false", dest="deploy_database",
            help='disable deploy database')
    parser.add_option('-Q', '--disable-fillqueue', default=True,
            action="store_false", dest="fill_queue",
            help='disable queue filling')
    parser.add_option('-T', '--disable-tilesgen', default=True,
            action="store_false", dest="tiles_gen",
            help='disable tile generation')
    parser.add_option('-H', '--host', default=None,
            help='The host used to generate tiles')
    parser.add_option('--cache', '--destination-cache',
            default=None, dest='cache',
            help='The cache name to use, default to main')
    parser.add_option('--capabilities', '--generate_wmts_capabilities',
            default=False, action="store_true",
            help='Generate the WMTS Capabilities and exit')
    parser.add_option('--cost', '--calculate-cost',
            default=False, action="store_true",
            help='Calculate the cost to generate and upload the tiles')
    parser.add_option('--ol', '--openlayers-test',
            default=False, action="store_true",
            help='Generate openlayers test page')

    (options, args) = parser.parse_args()
    logging.basicConfig(
        format='%(asctime)s:%(levelname)s:%(module)s:%(message)s',
        level=logging.INFO if options.test < 0 else logging.DEBUG)

    gene = TileGeneration(options.config, options.layer)

    if options.status:
        status(options, gene)
        sys.exit(0)

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']
    if options.deploy_config is None and 'deploy_config' in gene.config['generation']:
        options.deploy_config = gene.config['generation']['deploy_config']
    if options.sync and 'disable_sync' in gene.config['generation']:
        options.sync = not gene.config['generation']['disable_sync']
    if options.sync and 'disable_database' in gene.config['generation']:
        options.sync = not gene.config['generation']['disable_database']
    if options.sync and 'disable_fillqueue' in gene.config['generation']:
        options.sync = not gene.config['generation']['disable_fillqueue']
    if options.sync and 'disable_fillqueue' in gene.config['generation']:
        options.sync = not gene.config['generation']['disable_fillqueue']
    if options.sync and 'disable_tilesgen' in gene.config['generation']:
        options.sync = not gene.config['generation']['disable_tilesgen']

    if options.capabilities:
        _generate_wmts_capabilities(gene, options)
        sys.exit(0)

    if options.ol:
        _generate_openlayers(gene, options)
        sys.exit(0)

    if options.cost:
        _calculate_cost(gene, options)
        sys.exit(0)

    # start aws
    if not options.host:
        # not imlpemented yet
        host = aws_start(gene.metadata['aws']['host_type'])
    else:
        host = options.host

    if options.sync:
        # sync geodata
        run_local("rsync %(folder)s rsync://%(host):%(folder)s" % {
            'folder': gene.config['forge']['geodata_folder'],
            'host': host})

    # deploy
    _deploy(options, host)

    if options.deploy_code or options.deploy_database \
            or options.sync:
        # not imlpemented yet
        create_snapshot(host, gene.metadata['aws'])

    if options.fill_queue or options.tiles_gen:
        arguments = _get_arguments(options)
        project_dir = _get_project_dir(options.deploy_config)
        run_remote('./buildout/bin/generate_tiles ' +
            ' '.join(arguments), host, project_dir)


def _get_project_dir(deploy_config):
    config = ConfigParser.ConfigParser()
    config.readfp(open(deploy_config))
    return config.get('code', 'dest_dir')


def _deploy(options, host):
    components = ""
    if options.deploy_code and not options.deploy_database:
        components = "--components=[code]"
    if options.deploy_database and not options.deploy_code:
        components = "--components=[database]"

    if options.deploy_code or options.deploy_database:
        run_local('deploy --remote %s %s %s' %
            (components, options.deploy_config, host))


def _get_arguments(options):
    arguments = [
        "--config", options.config,
        "--layer", options.layer,
        "--destination-cache", options.cache,
        "--role", 'master' if options.fill_queue else 'slave'
        "--daemonize"
    ]
    if options.bbox:
        arguments.extend(["--bbox", options.bbox])
    if options.test:
        arguments.extend(["--test", options.test])
    return arguments


def create_snapshot(host, config):
    pass


def aws_start(host_type):
    pass


def run_local(cmd):
    call("sudo -u deploy " + cmd, shell=True)


def run_remote(cmd, host, project_dir):
    call(
        "ssh -f deploy@%(host)s 'cd %(project_dir)s; %(cmd)s'" % {
            'host': host, 'cmd': cmd, 'project_dir': project_dir},
        shell=True)


def status(options, gene):
    # get SQS status
    attributes = gene.get_sqs_queue().get_attributes()

    print """Approximate number of tiles to generate: %s
    Approximate number of generating tiles: %s
    Last modifiction in tile queue: %s""" % (
        attributes['ApproximateNumberOfMessages'],
        attributes['ApproximateNumberOfMessagesNotVisible'],
        attributes['LastModifiedTimestamp']
    )


def _calculate_cost(gene, options):
    nb_metatiles = {}
    nb_tiles = {}

    if options.bbox:
        geometry = gene.get_geom(options.bbox)
    elif 'bbox' in gene.layer:
        geometry = gene.get_geom(gene.layer['bbox'])
    else:
        geometry = gene.get_geom(gene.layer['grid_ref']['bbox'])
    extent = geometry.bounds

    bounding_pyramid = BoundingPyramid(tilegrid=gene.layer['grid_ref']['obj'])
    bounding_pyramid.fill(None, extent)

    meta = gene.layer.get('meta', False)
    if meta:
        gene.set_tilecoords(bounding_pyramid.metatilecoords(gene.layer['meta_size']))
    if options.zoom:
        gene.set_tilecoords(bounding_pyramid.ziter(options.zoom))
    else:
        gene.set_tilecoords(bounding_pyramid)
    gene.add_geom_filter()

    if meta:
        def count_metatile(tile):
            if tile:
                if tile.tilecoord.z in nb_metatiles:
                    nb_metatiles[tile.tilecoord.z] += 1
                else:
                    nb_metatiles[tile.tilecoord.z] = 1
            return tile
        gene.imap(count_metatile)

        class MetaTileSplitter(TileStore):
            def get(self, tiles):
                for metatile in tiles:
                    for tilecoord in metatile.tilecoord:
                        yield Tile(tilecoord)
        gene.get(MetaTileSplitter())

        # Only keep tiles that intersect geometry
        gene.add_geom_filter()

    def count_tile(tile):
        if tile:
            if tile.tilecoord.z in nb_tiles:
                nb_tiles[tile.tilecoord.z] += 1
            else:
                print "Calculate zoom %i." % tile.tilecoord.z
                nb_tiles[tile.tilecoord.z] = 1
        return tile
    gene.imap(count_tile)

    consume(gene.tilestream, None)

    times = {}
    print
    for z in nb_metatiles:
        print "%i meta tiles in zoom %i." % (nb_metatiles[z], z)
        times[z] = gene.config['cost']['metatile_generation_time'] * nb_metatiles[z]

    price = 0
    all_size = 0
    all_time = 0
    for z in nb_tiles:
        print
        print "%i tiles in zoom %i." % (nb_tiles[z], z)
        if meta:
            time = times[z] + gene.config['cost']['tile_generation_time'] * nb_tiles[z]
        else:
            time = gene.config['cost']['tileonly_generation_time'] * nb_tiles[z]
        size = gene.config['cost']['tile_size'] * nb_tiles[z]
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print "Time to generate: %d %d:%02d [d h:m]" % (td.days, td.seconds / 3600, td.seconds % 3600 / 60)
        c = gene.config['cost']['s3']['put'] * nb_tiles[z] / 1000.0
        price += c
        print 'S3 PUT: %0.2f [$]' % c
        c = time * gene.config['cost']['ec2']['usage'] / (1000.0 * 3600)
        price += c
        print 'EC2 usage: %0.2f [$]' % c
        c = gene.config['cost']['esb']['io'] * time / (1000.0 * 2600 * 24 * 30)
        price += c
        print 'ESB usage: %0.2f [$]' % c
        if meta:
            nb_sqs = nb_metatiles[z] * 3
        else:
            nb_sqs = nb_tiles[z] * 3
        c = nb_sqs * gene.config['cost']['sqs']['request'] / 1000000.0
        price += c
        print 'SQS usage: %0.2f [$]' % c

    print
    td = timedelta(milliseconds=all_time)
    print 'Total generation time : %d %d:%02d [d h:m]' % (td.days, td.seconds / 3600, td.seconds % 3600 / 60)
    print 'Total generation cost : %0.2f [$]' % price
    print
    print 'S3 Storage: %0.2f [$/month]' % (all_size * gene.config['cost']['s3']['storage'] / (1024.0 * 1024 * 1024))
    print 'S3 get: %0.2f [$/month]' % (
        gene.config['cost']['s3']['get'] * gene.config['cost']['request'] / 10000.0 +
        gene.config['cost']['s3']['download'] * gene.config['cost']['request'] * gene.config['cost']['tile_size'] / (1024.0 * 1024))
    if 'cloudfront' in gene.config['cost']:
        print 'CloudFront: %0.2f [$/month]' % (
            gene.config['cost']['cloudfront']['get'] * gene.config['cost']['request'] / 10000.0 +
            gene.config['cost']['cloudfront']['download'] * gene.config['cost']['request'] * gene.config['cost']['tile_size'] / (1024.0 * 1024))
    print 'ESB storage: %0.2f [$/month]' % (gene.config['cost']['esb']['storage'] * gene.config['cost']['esb_size'])


def _send(data, path, cache):
    if cache['type'] == 's3':
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key(('%(folder)s' % cache) + path)
        s3key.body = data
        s3key['Content-Encoding'] = 'utf-8'
        s3key['Content-Type'] = 'text/xml'
        s3key.put()
    else:
        folder = cache['folder'] or ''
        f = open(folder + path, 'w')
        f.write(data)
        f.close()

def _generate_wmts_capabilities(gene, options):
    from tilecloud_chain.wmts_get_capabilities_template import wmts_get_capabilities_template

    cache = gene.caches[options.cache]

    base_url = cache['http_url'] % cache
    capabilities = jinja2_template(wmts_get_capabilities_template,
            layers=gene.layers,
            grids=gene.grids,
            getcapabilities=base_url + '/1.0.0/WMTSCapabilities.xml',
            gettile=base_url,
            enumerate=enumerate, ceil=math.ceil, int=int)

    _send(capabilities, '/1.0.0/WMTSCapabilities.xml', cache)


def _generate_openlayers(gene, options):
    from tilecloud_chain.openlayers_html import openlayers_html
    from tilecloud_chain.openlayers_js import openlayers_js
    from tilecloud_chain.openlayers import openlayers

    cache = gene.caches[options.cache]

    base_url = cache['http_url'] % cache
    js = jinja2_template(openlayers_js,
            srs=gene.config['openlayers']['srs'],
            center_x=gene.config['openlayers']['center_x'],
            center_y=gene.config['openlayers']['center_y'],
            http_url=cache['http_url'],
            layers=[{
                'name': name,
                'grid': layer.get('output_format', None) == 'grid',
                'resolution': layer.get('resolution', None),
            } for name, layer in gene.layers.items() if layer['grid_ref']['srs'] == gene.config['openlayers']['srs']])

    _send(openlayers_html, '/index.html', cache)
    _send(js, '/wmts.js', cache)
    _send(openlayers, '/OpenLayers.js', cache)
