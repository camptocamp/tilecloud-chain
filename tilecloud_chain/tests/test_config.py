# -*- coding: utf-8 -*-

import os

from testfixtures import log_capture

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller


class TestConfig(CompareCase):
    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    @log_capture('tilecloud_chain')
    @attr(int_grid=True)
    @attr(general=True)
    def test_int_grid(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_controller -c tilegeneration/test-int-grid.yaml --dump-config',
            main_func=controller.main)
        l.check(
            (
                'tilecloud_chain', 'INFO',
                'Execute SQL: SELECT ST_AsBinary(geom) FROM '
                '(SELECT the_geom AS geom FROM tests.point) AS g.'
            ),
        )
