# -*- coding: utf-8 -*-

import os

from nose.plugins.attrib import attr

from testfixtures import log_capture
from tilecloud_chain import controller
from tilecloud_chain.tests import CompareCase


class TestConfig(CompareCase):
    def setUp(self):  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    @log_capture("tilecloud_chain")
    @attr(general=True)
    def test_int_grid(self, log_capture):
        self.run_cmd(
            cmd=".build/venv/bin/generate_controller -c tilegeneration/test-int-grid.yaml --dump-config",
            main_func=controller.main,
        )
        log_capture.check(
            (
                "tilecloud_chain",
                "INFO",
                "Execute SQL: SELECT ST_AsBinary(geom) FROM "
                "(SELECT the_geom AS geom FROM tests.point) AS g.",
            ),
        )
