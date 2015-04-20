# -*- coding: utf-8 -*-

import os

from testfixtures import log_capture

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller


class TestConfig(CompareCase):
    def setUp(self):  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_int_grid(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/test-int-grid.yaml --dump-config',
            main_func=controller.main)
        l.check(
            (
                'tilecloud_chain', 'INFO',
                'Execute SQL: SELECT ST_AsBinary(geom) FROM '
                '(SELECT the_geom AS geom FROM tests.point) AS g.'
            ),
        )

    def test_format_by_content_type(self):
        from tilecloud_chain import TileGeneration

        TileGeneration("tilegeneration/test_mime_pil.yaml")

        from tilecloud.lib.PIL_ import FORMAT_BY_CONTENT_TYPE
        self.assertEquals("PNG", FORMAT_BY_CONTENT_TYPE["image/png;mode=8bit,grayscale"])
