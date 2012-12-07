# -*- coding: utf-8 -*-

import os
import sys
import math
import logging
import boto
import yaml
from boto import sns
from copy import copy
from datetime import timedelta
from subprocess import Popen, PIPE
from optparse import OptionParser
from bottle import jinja2_template
from tilecloud import Tile, TileStore, consume
from tilecloud.lib.s3 import S3Connection

from tilecloud_chain import TileGeneration, add_comon_options


logger = logging.getLogger(__name__)


def main():
    parser = OptionParser(
        'Used to generate the tiles from a WMS or Mapnik, to WMST on filsystem or S3, optionaly use an SQS queue')
    add_comon_options(parser)
    parser.add_option('--deploy-config', default=None, dest="deploy_config", metavar="FILE",
            help='path to the deploy configuration file')
    parser.add_option('-s', '--status', default=False, action="store_true",
            help='display status and exit')
    parser.add_option('--disable-geodata', default=True, action="store_false", dest="geodata",
            help='disable geodata synchronisation')
    parser.add_option('--disable-code', default=True, action="store_false", dest="deploy_code",
            help='disable deploy application code')
    parser.add_option('--disable-database', default=True, action="store_false", dest="deploy_database",
            help='disable deploy database')
    parser.add_option('--disable-fillqueue', default=True, action="store_false", dest="fill_queue",
            help='disable queue filling')
    parser.add_option('--disable-tilesgen', default=True, action="store_false", dest="tiles_gen",
            help='disable tile generation')
    parser.add_option('-H', '--host', default=None,
            help='The host used to generate tiles')
    parser.add_option('--capabilities', '--generate_wmts_capabilities', default=False, action="store_true",
            help='Generate the WMTS Capabilities and exit')
    parser.add_option('--cost', '--calculate-cost', default=False, action="store_true",
            help='Calculate the cost to generate and upload the tiles')
    parser.add_option('--cost-algo', '--calculate-cost-algorithm', default='area', dest='cost_algo',
            metavar="ALGORITHM", help="The ALGORITHM use to calculate the cost default base on the 'area' "
            "of the genaration geometry, can also be 'count', to be base on number of tiles to generate.")
    parser.add_option('--ol', '--openlayers-test', default=False, action="store_true",
            help='Generate openlayers test page')
    parser.add_option('--mapcache', '--generate-mapcache-config', default=False, action="store_true", dest='mapcache',
            help='Generate MapCache configuration file')
    parser.add_option('--dump-config', default=False, action="store_true",
            help='Dump the used config with default values and exit')
    parser.add_option('--shutdown', default=False, action="store_true",
            help='Shut done the remote host after the task.')

    (options, args) = parser.parse_args()
    gene = TileGeneration(options.config, options, layer_name=options.layer)

    if options.status:  # pragma: no cover
        status(options, gene)
        sys.exit(0)

    if options.cache is None:
        options.cache = gene.config['generation']['default_cache']
    if options.capabilities:
        _generate_wmts_capabilities(gene, options)
        sys.exit(0)

    if options.mapcache:
        _generate_mapcache_config(gene, options)
        sys.exit(0)

    if options.ol:
        _generate_openlayers(gene, options)
        sys.exit(0)

    if options.dump_config:
        if (options.layer):
            _validate_calculate_cost(gene)
        else:
            for layer in gene.config['generation']['default_layers']:
                gene.set_layer(layer, options)
                _validate_calculate_cost(gene)
        _validate_generate_wmts_capabilities(gene, gene.caches[options.cache])
        _validate_generate_mapcache_config(gene)
        _validate_generate_openlayers(gene)
        for grild in gene.config['grids'].values():
            del grild['obj']
        print yaml.dump(gene.config)
        sys.exit(0)

    if options.cost:
        all_size = 0
        tile_size = 0
        all_tiles = 0
        if (options.layer):
            (all_size, all_time, all_price, all_tiles) = _calculate_cost(gene, options)
            tile_size = gene.layer['cost']['tile_size'] / (1024.0 * 1024)
        else:
            all_time = timedelta()
            all_price = 0
            for layer in gene.config['generation']['default_layers']:
                print
                print "===== %s =====" % layer
                gene.set_layer(layer, options)
                (size, time, price, tiles) = _calculate_cost(gene, options)
                tile_size += gene.layer['cost']['tile_size'] / (1024.0 * 1024)
                all_time += time
                all_price += price
                all_size += size
                all_tiles += tiles

            print
            print "===== GLOBAL ====="
            print "Total number of tiles: %i" % all_tiles
            print 'Total generation time: %d %d:%02d:%02d [d h:mm:ss]' % \
                (all_time.days, all_time.seconds / 3600, all_time.seconds % 3600 / 60, all_time.seconds % 60)
            print 'Total generation cost: %0.2f [$]' % all_price
        print
        print 'S3 Storage: %0.2f [$/month]' % (all_size * gene.config['cost']['s3']['storage'] / (1024.0 * 1024 * 1024))
        print 'S3 get: %0.2f [$/month]' % (
            gene.config['cost']['s3']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
            gene.config['cost']['s3']['download'] * gene.config['cost']['request_per_layers'] * tile_size)
        if 'cloudfront' in gene.config['cost']:
            print 'CloudFront: %0.2f [$/month]' % (
                gene.config['cost']['cloudfront']['get'] * gene.config['cost']['request_per_layers'] / 10000.0 +
                gene.config['cost']['cloudfront']['download'] * gene.config['cost']['request_per_layers'] * tile_size)
        print 'ESB storage: %0.2f [$/month]' % (gene.config['cost']['esb']['storage'] * gene.config['cost']['esb_size'])
        sys.exit(0)

    if options.deploy_config is None:
        options.deploy_config = gene.config['generation']['deploy_config']
    if options.geodata:
        options.geodata = not gene.config['generation']['disable_geodata']
    if options.deploy_code:
        options.deploy_code = not gene.config['generation']['disable_code']
    if options.deploy_database:
        options.deploy_database = not gene.config['generation']['disable_database']
    if options.fill_queue:  # pragma: no cover
        options.fill_queue = not gene.config['generation']['disable_fillqueue']
    if options.tiles_gen:  # pragma: no cover
        options.tiles_gen = not gene.config['generation']['disable_tilesgen']

    # start aws
    if not options.host:
        # TODO not imlpemented yet
        host = aws_start(gene.config['generation']['ec2_host_type'])  # pragma: no cover
    else:
        host = options.host

    if options.geodata and 'geodata_folder' in gene.config['generation']:
        print "==== Sync geodata ===="
        ssh_options = ''
        if 'ssh_options' in gene.config['generation']:
            ssh_options = gene.config['generation']['ssh_options']
        # sync geodata
        run_local(['rsync', '--delete', '-e', 'ssh ' + ssh_options,
            '-r', gene.config['generation']['geodata_folder'],
            host + ':' + gene.config['generation']['geodata_folder']])

    if options.deploy_code:
        print "==== Sync and build code ===="
        error = gene.validate(gene.config['generation'], 'generation', 'code_folder', required=True)
        if error:
            exit(1)  # pragma: no cover

        cmd = ['rsync', '--delete', ]
        if 'ssh_options' in gene.config['generation']:
            cmd += ['-e', 'ssh ' + gene.config['generation']['ssh_options']]
            ssh_options = gene.config['generation']['ssh_options']

        project_dir = gene.config['generation']['code_folder']
        cmd += ['-r', '.', host + ':' + project_dir]
        run_local(cmd)

        for cmd in gene.config['generation']['build_cmds']:
            run_remote(cmd, host, project_dir, gene)
        if 'apache_content' in gene.config['generation'] and 'apache_config' in gene.config['generation']:
            run_remote('echo %s > %s' % (gene.config['generation']['apache_content'],
                gene.config['generation']['apache_config']), host, project_dir, gene)
        run_remote('sudo apache2ctl graceful', host, project_dir, gene)

    # deploy
    if options.deploy_database:
        _deploy(gene, host)

    if options.deploy_code or options.deploy_database \
            or options.geodata:
        # TODO not implemented yet
        create_snapshot(host, gene)

    if options.time:
        arguments = _get_arguments(options)
        arguments.extend(['--role', 'local'])
        arguments.extend(['--time', str(options.time)])

        project_dir = gene.config['generation']['code_folder']
        processes = []
        for i in range(gene.config['generation']['number_process']):
            processes.append(run_remote_process('./buildout/bin/generate_tiles ' +
                ' '.join(arguments), host, project_dir, gene))

        tiles_size = []
        times = []
        for p in processes:
            results = p.communicate()
            if results[1] != '':
                logger.debug('ERROR: %s' % results[1])
            for r in results[0].split('\n'):
                if r.startswith('time: '):
                    times.append(int(r.replace('time: ', '')))
                elif r.startswith('size: '):
                    tiles_size.append(int(r.replace('size: ', '')))

        if len(times) == 0:  # pragma: no cover
            logger.error("Not enough data")
            sys.exit(1)
        mean_time = reduce(lambda x, y: x + y,
            [timedelta(microseconds=int(r)) for r in times],
            timedelta()) / len(times) ** 2
        mean_time_ms = mean_time.seconds * 1000 + mean_time.microseconds / 1000.0

        mean_size = reduce(lambda x, y: x + y, [int(r) for r in tiles_size], 0) / len(tiles_size)
        mean_size_kb = mean_size / 1024.0

        print '==== Time results ===='
        print 'A tile is generated in: %0.3f [ms]' % mean_time_ms
        print 'Than mean generated tile size: %0.3f [kb]' % (mean_size_kb)
        print '''config:
    cost:
        tileonly_generation_time: %0.3f
        tile_generation_time: %0.3f
        metatile_generation_time: 0
        tile_size: %0.3f''' % (mean_time_ms, mean_time_ms, mean_size_kb)

        if options.shutdown:  # pragma: no cover
            run_remote('sudo shutdown 0', host, project_dir, gene)
        sys.exit(0)

    if options.fill_queue:  # pragma: no cover
        print "==== Till queue ===="
        # TODO test
        arguments = _get_arguments(options)
        arguments.extend(['--role', 'master'])

        project_dir = gene.config['generation']['code_folder']
        run_remote('./buildout/bin/generate_tiles ' +
                ' '.join(arguments), host, project_dir, gene)

    if options.tiles_gen:  # pragma: no cover
        print "==== Generate tiles ===="
        # TODO test
        arguments = _get_arguments(options)
        arguments.extend(['--role', 'slave'])
        arguments.append("--daemonize")

        project_dir = gene.config['generation']['code_folder']
        processes = []
        for i in range(gene.config['generation']['number_process']):
            processes.append(run_remote_process('./buildout/bin/generate_tiles ' +
                ' '.join(arguments), host, project_dir, gene))

        if options.shutdown or 'sns' in gene.config:
            for p in processes:
                p.communicate()  # wait process end
        else:
            print 'Tile generation started in background'

        if options.shutdown:
            run_remote('sudo shutdown 0')

        if 'sns' in gene.config:
            if 'region' in gene.config['sns']:
                connection = sns.connect_to_region(gene.config['sns']['region'])
            else:
                connection = boto.connect_sns()
            connection.publish(gene.config['sns']['topic'], "The tile generation is finish", "Tile generation")


def _deploy(gene, host):
    print "==== Deploy database ===="
    deploy_cmd = 'deploy'
    if 'deploy_user' in gene.config['generation']:
        deploy_cmd = 'sudo -u %s deploy' % gene.config['generation']['deploy_user']
        index = host.find('@')
        if index >= 0:  # pragma: no cover
            host = host[index + 1:]
    run_local('%s --remote --components=[databases] %s %s' %
        (deploy_cmd, gene.options.deploy_config, host))


def _get_arguments(options):
    arguments = [
        "--config", options.config,
        "--destination-cache", options.cache
    ]
    if options.layer:
        arguments.extend(["--layer", options.layer])
    if options.near:
        arguments.extend(["--near", str(options.near)])
    elif options.bbox:
        arguments.extend(["--bbox", options.bbox])
    if options.zoom or options.zoom == 0:
        arguments.extend(["--zoom-level", str(options.zoom)])
    if options.test:
        arguments.extend(["--test", str(options.test)])
    if not options.geom:
        arguments.append("--no-geom")
    return arguments


def create_snapshot(host, gene):
    pass  # TODO


def aws_start(host_type):  # pragma: no cover
    pass  # TODO


def _quote(arg):
    if ' ' in arg:
        if "'" in arg:
            if '"' in arg:
                return "'%s'" % arg.replace("'", "\\'")
            else:
                return '"%s"' % arg
        else:
            return "'%s'" % arg
    elif arg == '':
        return "''"
    else:
        return arg


def run_local(cmd):
    if type(cmd) != list:
        cmd = cmd.split(' ')

    logger.debug('Run: %s.' % ' '.join([_quote(c) for c in cmd]))
    result = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    logger.info(result[0])
    logger.error(result[1])
    return result


def run_remote_process(remote_cmd, host, project_dir, gene):
    cmd = ['ssh']
    if 'ssh_options' in gene.config['generation']:
        cmd.extend(gene.config['generation']['ssh_options'].split(' '))
    if host is None:  # pragma: no cover
        exit('host option is required.')
    cmd.append(host)
    env = ''
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):  # pragma: no cover
        env = 'export AWS_ACCESS_KEY_ID=%(access_key)s;export AWS_SECRET_ACCESS_KEY=%(secret_key)s;' % {
            'access_key': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        }
    cmd.append('cd %(project_dir)s;'
            '%(env)s'
            '%(cmd)s' % {
        'cmd': remote_cmd,
        'env': env,
        'project_dir': project_dir
    })

    logger.debug('Run: %s.' % ' '.join([_quote(c) for c in cmd]))
    return Popen(cmd, stdout=PIPE, stderr=PIPE)


def run_remote(remote_cmd, host, project_dir, gene):
    result = run_remote_process(remote_cmd, host, project_dir, gene).communicate()
    logger.info(result[0])
    logger.error(result[1])
    return result


def status(options, gene):  # pragma: no cover
    # get SQS status
    attributes = gene.get_sqs_queue().get_attributes()

    print """Approximate number of tiles to generate: %s
    Approximate number of generating tiles: %s
    Last modification in tile queue: %s""" % (
        attributes['ApproximateNumberOfMessages'],
        attributes['ApproximateNumberOfMessagesNotVisible'],
        attributes['LastModifiedTimestamp']
    )


def _validate_calculate_cost(gene):
    error = False
    name = "layer[%s]" % gene.layer['name']
    error = gene.validate(gene.layer, name, 'cost', attribute_type=dict, default={}) or error
    error = gene.validate(gene.layer['cost'], name + '.cost', 'tileonly_generation_time',
            attribute_type=float, default=40.0) or error
    error = gene.validate(gene.layer['cost'], name + '.cost', 'tile_generation_time',
            attribute_type=float, default=30.0) or error
    error = gene.validate(gene.layer['cost'], name + '.cost', 'metatile_generation_time',
            attribute_type=float, default=30.0) or error
    error = gene.validate(gene.layer['cost'], name + '.cost', 'tile_size',
            attribute_type=float, default=20.0) or error

    error = gene.validate(gene.config, 'config', 'cost', attribute_type=dict, default={}) or error
    error = gene.validate(gene.config['cost'], 'cost', 'request_per_layers',
        attribute_type=int, default=10000000) or error
    error = gene.validate(gene.config['cost'], 'cost', 'esb_size', attribute_type=int, default=100) or error
    # http://aws.amazon.com/s3/pricing/
    error = gene.validate(gene.config['cost'], 'cost', 's3', attribute_type=dict, default={}) or error
    # [$/Go/month]
    error = gene.validate(gene.config['cost']['s3'], 'cost.s3', 'storage', attribute_type=float, default=0.125) or error
    # [$/put/1000]
    error = gene.validate(gene.config['cost']['s3'], 'cost.s3', 'put', attribute_type=float, default=0.01) or error
    # [$/get/10000]
    error = gene.validate(gene.config['cost']['s3'], 'cost.s3', 'get', attribute_type=float, default=0.01) or error
    # [$/Go]
    error = gene.validate(gene.config['cost']['s3'], 'cost.s3', 'download', attribute_type=float, default=0.12) or error
    # http://aws.amazon.com/cloudfront/pricing/
    error = gene.validate(gene.config['cost'], 'cost', 'cloudfront', attribute_type=dict, default={}) or error
    # [$/get/10000]
    error = gene.validate(gene.config['cost']['cloudfront'], 'cost.cloudfront', 'get',
        attribute_type=float, default=0.009) or error
    # [$/Go]
    error = gene.validate(gene.config['cost']['cloudfront'], 'cost.cloudfront', 'download',
        attribute_type=float, default=0.12) or error
    # http://aws.amazon.com/ec2/pricing/
    error = gene.validate(gene.config['cost'], 'cost', 'ec2', attribute_type=dict, default={}) or error
    # [$/hour]
    ec2cost = {
        't1.micro': 0.02,
        'm1.small': 0.085,
        'm1.medium': 0.17,
        'm1.large': 0.34,
        'm1.xlarge': 0.68,
        'm2.xlarge': 0.506,
        'm2.2xlarge': 1.012,
        'm2.4xlarge': 2.024,
        'c1.medium': 0.186,
        'c1.xlarge': 0.744,
        'cc1.4xlarge': 1.3,  # usa-est-1
        'cc1.8xlarge': 2.7,
        'cg1.4xlarge': 2.36,
        'hi1.4xlarge': 3.41,
    }
    error = gene.validate(gene.config['cost']['ec2'], 'cost.ec2', 'usage', attribute_type=float,
        default=ec2cost[gene.config['generation']['ec2_host_type']]) or error
    # http://aws.amazon.com/ebs/
    error = gene.validate(gene.config['cost'], 'cost', 'esb', attribute_type=dict, default={}) or error
    # [$/1Go/month]
    error = gene.validate(gene.config['cost']['esb'], 'cost.esb', 'storage',
        attribute_type=float, default=0.11) or error
    # [$/ 1000 E/S/s /month]
    error = gene.validate(gene.config['cost']['esb'], 'cost.esb', 'io', attribute_type=float, default=260.0) or error
    # http://aws.amazon.com/sqs/pricing/
    error = gene.validate(gene.config['cost'], 'cost', 'sqs', attribute_type=dict, default={}) or error
    # [$/10000]
    error = gene.validate(gene.config['cost']['sqs'], 'cost.sqs', 'request',
        attribute_type=float, default=0.01) or error

    if error:
        exit(1)  # pragma: no cover


def _calculate_cost(gene, options):
    _validate_calculate_cost(gene)

    nb_metatiles = {}
    nb_tiles = {}

    meta = gene.layer['meta']
    if options.cost_algo == 'area':
        meta_size = gene.layer['meta_size'] if meta else None
        tile_size = gene.layer['grid_ref']['tile_size']
        res = [{'r': r, 'i': i} for i, r in enumerate(gene.layer['grid_ref']['resolutions'])]
        geom = gene.geom
        geom_buffer = 0
        meta_geom = gene.geom
        meta_geom_buffer = 0
        for res in sorted(res, key=lambda r: r['r']):
            i = res['i']
            resolution = res['r']
            print "Calculate zoom %i." % i

            if meta:
                size = meta_size * tile_size * resolution
                meta_geom = meta_geom.buffer(size * 0.6 - meta_geom_buffer)
                meta_geom_buffer = size * 0.6
                nb_metatiles[i] = int(round(meta_geom.area / size ** 2))
            size = tile_size * resolution
            geom = geom.buffer(size * 0.6 - geom_buffer)
            geom_buffer = size * 0.6
            nb_tiles[i] = int(round(geom.area / size ** 2))

    elif options.cost_algo == 'count':
        gene.init_tilecoords(options)
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
            gene.tilestream = MetaTileSplitter().get(gene.tilestream)

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
        times[z] = gene.layer['cost']['metatile_generation_time'] * nb_metatiles[z]

    price = 0
    all_size = 0
    all_time = 0
    all_tiles = 0
    for z in nb_tiles:
        print
        print "%i tiles in zoom %i." % (nb_tiles[z], z)
        all_tiles += nb_tiles[z]
        if meta:
            time = times[z] + gene.layer['cost']['tile_generation_time'] * nb_tiles[z]
        else:
            time = gene.layer['cost']['tileonly_generation_time'] * nb_tiles[z]
        size = gene.layer['cost']['tile_size'] * nb_tiles[z]
        all_size += size

        all_time += time
        td = timedelta(milliseconds=time)
        print "Time to generate: %d %d:%02d:%02d [d h:mm:ss]" % \
            (td.days, td.seconds / 3600, td.seconds % 3600 / 60, td.seconds % 60)
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
    print "Number of tiles: %i" % all_tiles
    print 'Generation time: %d %d:%02d:%02d [d h:mm:ss]' % \
        (td.days, td.seconds / 3600, td.seconds % 3600 / 60, td.seconds % 60)
    print 'Generation cost: %0.2f [$]' % price

    return (all_size, td, price, all_tiles)


def _send(data, path, cache):
    if cache['type'] == 's3':  # pragma: no cover
        s3bucket = S3Connection().bucket(cache['bucket'])
        s3key = s3bucket.key(('%(folder)s' % cache) + path)
        s3key.body = data
        s3key['Content-Encoding'] = 'utf-8'
        s3key['Content-Type'] = 'text/xml'
        s3key.put()
    else:
        folder = cache['folder'] or ''
        filename = folder + path
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        f = open(folder + path, 'w')
        f.write(data)
        f.close()


def _validate_generate_wmts_capabilities(gene, cache):
    error = False
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_url', attribute_type=str, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'http_urls', attribute_type=list, default=False) or error
    error = gene.validate(cache, 'cache[%s]' % cache['name'], 'hosts', attribute_type=list, default=False) or error
    if not cache['http_url'] and not cache['http_urls']:
        logger.error("The attribute 'http_url' or 'http_urls' is required in the object %s." %
            ('cache[%s]' % cache['name']))  # pragma: no cover
        error = True  # pragma: no cover
    if error:
        exit(1)  # pragma: no cover


def _generate_wmts_capabilities(gene, options):
    from tilecloud_chain.wmts_get_capabilities_template import wmts_get_capabilities_template

    cache = gene.caches[options.cache]
    _validate_generate_wmts_capabilities(gene, cache)

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
    capabilities = jinja2_template(wmts_get_capabilities_template,
            layers=gene.layers,
            grids=gene.grids,
            getcapabilities=base_urls[0] + '/1.0.0/WMTSCapabilities.xml',
            gettiles=base_urls,
            enumerate=enumerate, ceil=math.ceil, int=int)

    _send(capabilities, '/1.0.0/WMTSCapabilities.xml', cache)


def _validate_generate_mapcache_config(gene):
    error = False
    error = gene.validate(gene.config, 'config', 'mapcache', attribute_type=dict, default={}) or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'mapserver_url', attribute_type=str,
        default='http://${vars:host}/${vars:instanceid}/mapserv') or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'config_file', attribute_type=str,
        default='apache/mapcache.xml.in') or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'resolutions', attribute_type=float,
        is_array=True, required=True) or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'memcache_host', attribute_type=str,
        default='localhost') or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'memcache_port', attribute_type=int,
        default='11211') or error
    error = gene.validate(gene.config['mapcache'], 'mapcache', 'layers', attribute_type=str, is_array=True,
        required=True, enumeration=gene.config['layers'].keys()) or error

    if 'layers' in gene.config['mapcache'] and 'resolutions' in gene.config['mapcache']:
        for layer in gene.config['mapcache']['layers']:
            if len(gene.layers[layer]['grid_ref']['resolutions']) > gene.config['mapcache']['resolutions']:
                logger.error("The layer '%s' (grid '%s') has more resolutions than mapcache." %
                    (layer, gene.layers[layer]['grid']))  # pragma: no cover
                error = True  # pragma: no cover
            else:
                for i, resolution in enumerate(gene.layers[layer]['grid_ref']['resolutions']):
                    if resolution != gene.config['mapcache']['resolutions'][i]:
                        logger.error("The resolutions of layer '%s' (grid '%s') "
                            "don't corresponds to mapcache resolutions (%f != %s)." %
                            (layer, gene.layers[layer]['grid'],
                            resolution, gene.config['mapcache']['resolutions'][i]))  # pragma: no cover
                        error = True  # pragma: no cover

    if error:
        exit(1)  # pragma: no cover


def _generate_mapcache_config(gene, options):
    from tilecloud_chain.mapcache_config_template import mapcache_config_template

    _validate_generate_mapcache_config(gene)

    config = jinja2_template(mapcache_config_template,
            layers=gene.layers,
            grids=gene.grids,
            mapcache=gene.config['mapcache'])

    f = open(gene.config['mapcache']['config_file'], 'w')
    f.write(config)
    f.close()


def _validate_generate_openlayers(gene):
    error = False
    error = gene.validate(gene.config, 'config', 'openlayers', attribute_type=dict, default={}) or error
    error = gene.validate(gene.config['openlayers'], 'openlayers', 'srs',
        attribute_type=str, default='EPSG:21781') or error
    error = gene.validate(gene.config['openlayers'], 'openlayers', 'center_x',
        attribute_type=float, default=600000) or error
    error = gene.validate(gene.config['openlayers'], 'openlayers', 'center_y',
        attribute_type=float, default=200000) or error
    if error:
        exit(1)  # pragma: no cover


def _generate_openlayers(gene, options):
    from tilecloud_chain.openlayers_html import openlayers_html
    from tilecloud_chain.openlayers_js import openlayers_js
    from tilecloud_chain.openlayers import openlayers

    _validate_generate_openlayers(gene)

    cache = gene.caches[options.cache]

    js = jinja2_template(openlayers_js,
            srs=gene.config['openlayers']['srs'],
            center_x=gene.config['openlayers']['center_x'],
            center_y=gene.config['openlayers']['center_y'],
            http_url=cache['http_url'] % cache,
            layers=[{
                'name': name,
                'grid': layer['type'] == 'mapnik' and layer['output_format'] == 'grid',
                'resolution': layer['resolution'] if
                        layer['type'] == 'mapnik' and layer['output_format'] == 'grid' else None,
            } for name, layer in gene.layers.items() if layer['grid_ref']['srs'] == gene.config['openlayers']['srs']])

    _send(openlayers_html, '/index.html', cache)
    _send(js, '/wmts.js', cache)
    _send(openlayers, '/OpenLayers.js', cache)
