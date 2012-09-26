# -*- coding: utf-8 -*-

import sys
import math
import logging
import ConfigParser
from subprocess import call
from optparse import OptionParser
from bottle import jinja2_template
from tilecloud.lib.s3 import S3Connection

from tilecloud_chain import TileGeneration
from tilecloud_chain.wmts_get_capabilities_template import wmts_get_capabilities_template


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


def _generate_wmts_capabilities(gene, options):
    cache = gene.caches[options.cache]

    base_url = cache['http_url'] % cache
    capabilities = jinja2_template(wmts_get_capabilities_template,
            layers=gene.layers,
            grids=gene.grids,
            getcapabilities=base_url + '/capabilities.xml',
            gettile=base_url,
            enumerate=enumerate, ceil=math.ceil, int=int)

    if cache['type'] == 's3':
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key('%(folder)s/capabilities.xml' % cache)
        s3key.body = capabilities
        s3key['Content-Encoding'] = 'utf-8'
        s3key['Content-Type'] = 'text/xml'
        s3key.put()
    else:
        folder = cache['folder'] or ''
        f = open(folder + '/1.0.0/WMTSCapabilities.xml', 'w')
        f.write(capabilities)
        f.close()
