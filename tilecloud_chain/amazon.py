# -*- coding: utf-8 -*-

import os
import sys
import logging
import boto
import re
import socket
import subprocess
from six import PY3
from os import path, environ
from time import sleep
from threading import Thread
from boto import sns
from datetime import timedelta
from subprocess import Popen, PIPE
from argparse import ArgumentParser
from six.moves import reduce

from tilecloud_chain import TileGeneration, add_comon_options, quote


logger = logging.getLogger(__name__)


def _get_path():
    directory = path.dirname(sys.argv[0])
    if len(directory) != 0:  # pragma: no cover
        directory += '/'
    return directory


def main():
    parser = ArgumentParser(
        description='Used to generate the tiles from Amazon EC2, '
        'and get the SQS queue status',
        prog=sys.argv[0]
    )
    add_comon_options(parser)
    parser.add_argument(
        '--deploy-config', default=None, dest="deploy_config", metavar="FILE",
        help='path to the deploy configuration file'
    )
    parser.add_argument(
        '--status', default=False, action="store_true",
        help='display the SQS queue status and exit'
    )
    parser.add_argument(
        '--disable-geodata', default=True, action="store_false", dest="geodata",
        help='disable geodata synchronisation'
    )
    parser.add_argument(
        '--disable-code', default=True, action="store_false", dest="deploy_code",
        help='disable deploy application code'
    )
    parser.add_argument(
        '--disable-database', default=True, action="store_false", dest="deploy_database",
        help='disable deploy database'
    )
    parser.add_argument(
        '--disable-fillqueue', default=True, action="store_false", dest="fill_queue",
        help='disable queue filling'
    )
    parser.add_argument(
        '--disable-tilesgen', default=True, action="store_false", dest="tiles_gen",
        help='disable tile generation'
    )
    parser.add_argument(
        '--host', default=None,
        help='The host used to generate tiles'
    )
    parser.add_argument(
        '--shutdown', default=False, action="store_true",
        help='Shut done the remote host after the task.'
    )
    parser.add_argument(
        '--wait', default=False, action="store_true",
        help='Wait that all the tasks will finish.'
    )
    parser.add_argument(
        '--local', default=False, action="store_true",
        help='Run the generation locally'
    )

    options = parser.parse_args()
    gene = TileGeneration(options.config, options, layer_name=options.layer)

    if options.status:  # pragma: no cover
        status(options, gene)
        sys.exit(0)

    if 'ec2' not in gene.config:  # pragma: no cover
        print("EC2 not configured")
        sys.exit(1)

    if options.deploy_config is None:
        options.deploy_config = gene.config['ec2']['deploy_config']
    if options.geodata:
        options.geodata = not gene.config['ec2']['disable_geodata']
    if options.deploy_code:
        options.deploy_code = not gene.config['ec2']['disable_code']
    if options.deploy_database:
        options.deploy_database = not gene.config['ec2']['disable_database']
    if options.fill_queue:  # pragma: no cover
        options.fill_queue = not gene.config['ec2']['disable_fillqueue']
    if options.tiles_gen:  # pragma: no cover
        options.tiles_gen = not gene.config['ec2']['disable_tilesgen']

    # start aws
    if not options.host:
        # TODO not implemented yet
        host = aws_start(gene.config['ec2']['host_type'])  # pragma: no cover
    else:
        host = options.host

    if not options.local and options.geodata and 'geodata_folder' in gene.config['ec2']:  # pragma: no cover
        print("==== Sync geodata ====")
        ssh_options = ''
        if 'ssh_options' in gene.config['ec2']:  # pragma: no cover
            ssh_options = gene.config['ec2']['ssh_options']
        # sync geodata
        run_local([
            'rsync', '--delete', '-e', 'ssh ' + ssh_options,
            '-r', gene.config['ec2']['geodata_folder'],
            host + ':' + gene.config['ec2']['geodata_folder']
        ])

    if options.deploy_code and not options.local:
        print("==== Sync and build code ====")

        cmd = ['rsync', '--delete', ]
        if 'ssh_options' in gene.config['ec2']:  # pragma: no cover
            cmd += ['-e', 'ssh ' + gene.config['ec2']['ssh_options']]
            ssh_options = gene.config['ec2']['ssh_options']

        project_dir = gene.config['ec2']['code_folder']
        cmd += ['-r', '.', host + ':' + project_dir]
        run_local(cmd)

        for cmd in gene.config['ec2']['build_cmds']:
            run(options, cmd % environ, host, project_dir, gene)
        if 'apache_content' in gene.config['ec2'] and 'apache_config' in gene.config['ec2']:
            run(
                options,
                'echo {0!s} > {1!s}'.format(
                    gene.config['ec2']['apache_content'],
                    gene.config['ec2']['apache_config']
                ), host, project_dir, gene
            )
        run(options, 'sudo apache2ctl graceful', host, project_dir, gene)

    # deploy
    if options.deploy_database and not options.local:
        _deploy(gene, host)

    if options.deploy_code or options.deploy_database \
            or options.geodata and not options.local:
        # TODO not implemented yet
        create_snapshot(host, gene)

    if options.time:
        arguments = _get_arguments(options)
        arguments.extend(['--role', 'local'])
        arguments.extend(['--time', str(options.time)])

        project_dir = None if options.local else gene.config['ec2']['code_folder']
        processes = []
        for i in range(gene.config['ec2']['number_process']):
            processes.append(
                run_remote_process(
                    "{0!s}generate_tiles {1!s}".format(
                        _get_path(),
                        ' '.join([str(a) for a in arguments])
                    ), host, project_dir, gene
                )
            )

        tiles_size = []
        times = []
        for p in processes:
            results = p.communicate()
            if results[1] != '':  # pragma: no cover
                logger.debug('ERROR: {0!s}'.format(results[1]))
            if PY3:
                results = [r.decode('utf-8') for r in results]
            results = (re.sub(u'\n[^\n]*\r', u'\n', results[0]), )
            results = (re.sub(u'^[^\n]*\r', u'', results[0]), )
            for r in results[0].split('\n'):
                if r.startswith('time: '):
                    times.append(int(r.replace('time: ', '')))
                elif r.startswith('size: '):
                    tiles_size.append(int(r.replace('size: ', '')))

        if len(times) == 0:  # pragma: no cover
            logger.error("Not enough data")
            sys.exit(1)
        mean_time = reduce(
            lambda x, y: x + y,
            [timedelta(microseconds=int(r)) for r in times],
            timedelta()
        ) / len(times) ** 2
        mean_time_ms = mean_time.seconds * 1000 + mean_time.microseconds / 1000.0

        mean_size = reduce(lambda x, y: x + y, [int(r) for r in tiles_size], 0) / len(tiles_size)
        mean_size_kb = mean_size / 1024.0

        print('==== Time results ====')
        print('A tile is generated in: {0:0.3f} [ms]'.format(mean_time_ms))
        print('Then mean generated tile size: {0:0.3f} [kb]'.format((mean_size_kb)))
        print('''config:
    cost:
        tileonly_generation_time: {0:0.3f}
        tile_generation_time: {1:0.3f}
        metatile_generation_time: 0
        tile_size: {2:0.3f}'''.format(mean_time_ms, mean_time_ms, mean_size_kb))

        if options.shutdown:  # pragma: no cover
            run(options, 'sudo shutdown 0', host, project_dir, gene)
        sys.exit(0)

    if options.fill_queue and not options.local:  # pragma: no cover
        print("==== Till queue ====")
        # TODO test
        arguments = _get_arguments(options)
        arguments.extend(['--role', 'master', '--quiet'])

        project_dir = gene.config['ec2']['code_folder']
        run_remote_process(
            options,
            "{0!s}generate_tiles {1!s}".format(
                _get_path(),
                ' '.join([str(a) for a in arguments])
            ), host, project_dir, gene
        )
        sleep(5)
        attributes = gene.get_sqs_queue().get_attributes()
        print(
            "\rTiles to generate: {0!s}/{1!s}".format(
                attributes['ApproximateNumberOfMessages'],
                attributes['ApproximateNumberOfMessagesNotVisible']
            )
        )

    if options.tiles_gen:  # pragma: no cover
        print("==== Generate tiles ====")

        if options.wait and not options.local:
            print("")

            class Status(Thread):
                def run(self):  # pragma: no cover
                    while True:
                        attributes = gene.get_sqs_queue().get_attributes()
                        print(
                            "\rTiles to generate/generating: {0!s}/{1!s}".format(
                                attributes['ApproximateNumberOfMessages'],
                                attributes['ApproximateNumberOfMessagesNotVisible']
                            )
                        )

                        sleep(1)
            status_thread = Status()
            status_thread.setDaemon(True)
            status_thread.start()

        arguments = _get_arguments(options)
        arguments.extend(['--quiet'])
        if not options.local:
            arguments.extend(['--role', 'slave'])

        project_dir = None if options.local else gene.config['ec2']['code_folder']
        threads = []
        for i in range(gene.config['ec2']['number_process']):
            if options.local:
                threads.append(run_local_process(
                    "{0!s}generate_tiles --local-process-number {1:d} {2!s}".format(
                        _get_path(),
                        i, ' '.join([str(a) for a in arguments])
                    )
                ))
            else:
                run_remote_process(
                    "{0!s}generate_tiles {1!s}".format(
                        _get_path(),
                        ' '.join([str(a) for a in arguments])
                    ), host, project_dir, gene
                )

        print('Tile generation started')

        if options.shutdown:
            run(options, 'sudo shutdown 0')

        if options.wait and options.local:
            while len(threads) > 0:
                threads = [t for t in threads if t.is_alive()]
                sleep(1)

        if 'sns' in gene.config:
            if 'region' in gene.config['sns']:
                connection = sns.connect_to_region(gene.config['sns']['region'])
            else:
                connection = boto.connect_sns()
            connection.publish(
                gene.config['sns']['topic'],
                """The tile generation is finish
Host: {host!s}
Command: {cmd!s}""".format(**
                {
                    'host': socket.getfqdn(),
                    'cmd': ' '.join([quote(arg) for arg in sys.argv])
                }),
                "Tile generation controller"
            )


def _deploy(gene, host):
    print("==== Deploy database ====")
    deploy_cmd = 'deploy'
    if 'deploy_user' in gene.config['ec2']:
        deploy_cmd = 'sudo -u {0!s} deploy'.format(gene.config['ec2']['deploy_user'])
        index = host.find('@')
        if index >= 0:  # pragma: no cover
            host = host[index + 1:]
    run_local(
        '{0!s} --remote --components=[databases] {1!s} {2!s}'.format(deploy_cmd, gene.options.deploy_config, host)
    )


def _get_arguments(options):
    arguments = [
        "--config", options.config,
    ]
    if options.cache is not None:
        arguments.extend(["--cache", options.cache])
    if options.layer is not None:
        arguments.extend(["--layer", options.layer])
    if options.near is not None:
        arguments.append("--near")
        arguments.extend(options.near)
    elif options.bbox is not None:
        arguments.append("--bbox")
        arguments.extend(options.bbox)
    if options.zoom is not None:
        arguments.extend(["--zoom", ','.join([str(z) for z in options.zoom])])
    if options.test is not None:
        arguments.extend(["--test", str(options.test)])
    if not options.geom:
        arguments.append("--no-geom")
    return arguments


def create_snapshot(host, gene):
    pass  # TODO


def aws_start(host_type):  # pragma: no cover
    pass  # TODO


def run_local(cmd):
    if type(cmd) != list:
        cmd = cmd.split(' ')

    logger.debug('Run: {0!s}.'.format(' '.join([quote(c) for c in cmd])))
    result = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    if PY3:
        result = [r.decode('utf-8') for r in result]

    if len(result[0]) != 0:   # pragma: no cover
        logger.info(result[0])
    if len(result[1]) != 0:
        logger.error(result[1])
    return result


def run_local_process(cmd):
    if type(cmd) != list:
        cmd = cmd.split(' ')
    logger.debug('Run: {0!s}.'.format(' '.join([quote(c) for c in cmd])))
    task = Run(cmd)
    task.start()
    return task


def run_remote_process(remote_cmd, host, project_dir, gene):
    cmd = ['ssh']
    if 'ssh_options' in gene.config['ec2']:  # pragma: no cover
        cmd.extend(gene.config['ec2']['ssh_options'].split(' '))
    if host is None:  # pragma: no cover
        exit('host option is required.')
    cmd.append(host)
    env = ''
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):  # pragma: no cover
        env = 'export AWS_ACCESS_KEY_ID={access_key!s};export AWS_SECRET_ACCESS_KEY={secret_key!s};'.format(**{
            'access_key': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        })
    cmd.append(
        'cd %(project_dir)s;'
        '%(env)s'
        '%(cmd)s' % {
            'cmd': remote_cmd,
            'env': env,
            'project_dir': project_dir
        }
    )

    logger.debug('Run: {0!s}.'.format(' '.join([quote(c) for c in cmd])))
    return Popen(cmd, stdout=PIPE, stderr=PIPE)


class Run(Thread):
    def __init__(self, cmd):
        Thread.__init__(self)
        if type(cmd) != list:  # pragma: no cover
            cmd = cmd.split(' ')
        self.cmd = cmd

    def run(self):
        subprocess.call(self.cmd)


def run(options, cmd, host, project_dir, gene):
    if options.local:  # pragma: no cover
        if type(cmd) != list:
            cmd = cmd.split(' ')
        subprocess.call(cmd)
    else:
        result = run_remote_process(cmd, host, project_dir, gene).communicate()
        if len(result[0]) != 0:
            logger.info(result[0])
        if len(result[1]) != 0:  # pragma: no cover
            logger.error(result[1])


def run_remote(remote_cmd, host, project_dir, gene):  # pragma: no cover
    result = run_remote_process(remote_cmd, host, project_dir, gene).communicate()
    if len(result[0]) != 0:
        logger.info(result[0])
    if len(result[1]) != 0:
        logger.error(result[1])
    return result


def status(options, gene):  # pragma: no cover
    # get SQS status
    attributes = gene.get_sqs_queue().get_attributes()

    print(
        """Approximate number of tiles to generate: {0!s}
        Approximate number of generating tiles: {1!s}
        Last modification in tile queue: {2!s}""".format(
            attributes['ApproximateNumberOfMessages'],
            attributes['ApproximateNumberOfMessagesNotVisible'],
            attributes['LastModifiedTimestamp']
        )
    )
