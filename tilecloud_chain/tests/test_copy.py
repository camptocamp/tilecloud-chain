# -*- coding: utf-8 -*-

import os
import shutil

from testfixtures import log_capture
from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import copy_


class TestGenerate(CompareCase):
    def setUp(self):  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')
        os.makedirs('/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/')

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_copy(self, l):
        with open('/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png', 'w') as f:
            f.write('test image')

        for d in ('-d', '-q', '-v'):
            self.assert_cmd_equals(
                cmd='.build/venv/bin/generate_copy {0!s} -c tilegeneration/test-copy.yaml src dst'.format(d),
                main_func=copy_.main,
                regex=True,
                expected="""The tile copy of layer 'point_hash' is finish
Nb copy tiles: 1
Nb errored tiles: 0
Nb dropped tiles: 0
Total time: 0:00:[0-9][0-9]
Total size: 10 o
Time per tile: [0-9]+ ms
Size per tile: 10 o

""" if d != '-q' else '',
                empty_err=True)
        l.check(
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty')
        )
        with open('/tmp/tiles/dst/1.0.0/point_hash/default/21781/0/0/0.png', 'r') as f:
            self.assertEqual(f.read(), 'test image')

    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_process(self, l):
        import subprocess
        for d in ('-vd', '-q', '-v', ''):
            subprocess.call([
                'wget',
                'http://localhost/mapserv?STYLES=default&SERVICE=WMS&FORMAT=\
image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&VERSION=1.1.1&BBOX=\
%28560800.0%2C+158000.0%2C+573600.0%2C+170800.0%29&LAYERS=point&SRS=epsg%3A21781',
                '-O',
                '/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png',
            ])
            statinfo = os.stat(
                '/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png',
            )
            self.assertEqual(statinfo.st_size, 755)

            self.assert_cmd_equals(
                cmd='.build/venv/bin/generate_process {0!s} -c tilegeneration/test-copy.yaml --cache src optipng'.format(d),
                main_func=copy_.process,
                regex=True,
                expected="""The tile process of layer 'point_hash' is finish
Nb process tiles: 1
Nb errored tiles: 0
Nb dropped tiles: 0
Total time: 0:00:[0-9][0-9]
Total size: 103 o
Time per tile: [0-9]+ ms
Size per tile: 103 o

""" if d != '-q' else '',
                empty_err=True)
            statinfo = os.stat(
                '/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png',
            )
            self.assertEqual(statinfo.st_size, 103)
        l.check(
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty')
        )
