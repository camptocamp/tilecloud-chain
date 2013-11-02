# -*- coding: utf-8 -*-

import os
import shutil

from testfixtures import log_capture
from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import copy_


class TestGenerate(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(__file__))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')
        os.makedirs('/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/')
        f = open('/tmp/tiles/src/1.0.0/point_hash/default/21781/0/0/0.png', 'w')
        f.write('test image')
        f.close()

    @classmethod
    def tearDownClass(self):
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @attr(copy=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_copy(self, l):
        for d in ('-d', '-q', '-v'):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_copy %s -c tilegeneration/test-copy.yaml src dst' % d,
                main_func=copy_.main,
                regex=True,
                expected="""The tile copy of layer 'point_hash' is finish
Nb copyed tiles: 1
Total time: 0:00:[0-9][0-9]
Total size: 10 o
Time per tiles: [0-9]+ ms
Size per tile: 10 o

""" if d != '-q' else '',
                empty_err=True)
        l.check(
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty'),
            ('tilecloud_chain', 'ERROR', 'The tile: not defined is empty')
        )
        f = open('/tmp/tiles/dst/1.0.0/point_hash/default/21781/0/0/0.png', 'r')
        self.assertEquals(f.read(), 'test image')
        f.close()
