# -*- coding: utf-8 -*-

import os

from testfixtures import log_capture

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller, generate


class TestError(CompareCase):
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
    def test_resolution(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_resolutions.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The resolution 0.1 * resolution_scale 5 is not an integer."),
        )

    @log_capture('tilecloud_chain')
    @attr(nopy3=True)
    @attr(general=True)
    def test_mapnik_grid_meta(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_mapnik_grid_meta.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The layer 'b' is of type Mapnik/Grid, that can't support matatiles."),
        )

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_exists(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_exists.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_exists.yaml' in invalid.
 - /: Cannot find required key 'caches'.
 - /: Cannot find required key 'grids'.
 - /: Cannot find required key 'layers'."""),
        )

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_type(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -v -c tilegeneration/wrong_type.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_type.yaml' in invalid.
 - /grids/swissgrid!/name: Value 'swissgrid!' does not match pattern '^[a-zA-Z0-9_\\-~\\.]+$'.
 - /grids/swissgrid!: Cannot find required key 'bbox'.
 - /grids/swissgrid!: Cannot find required key 'resolutions'.
 - /grids/swissgrid!: Cannot find required key 'srs'.
 - /grids/swissgrid_1/srs: Value '{}' does not match pattern '^(?i)epsg:[0-9]+$'.
 - /grids/swissgrid_1/srs: Value '{}' is not of type 'str'.
 - /grids/swissgrid_2/bbox/0: Value 'a' is not of type 'number'.
 - /grids/swissgrid_2/bbox/1: Value 'b' is not of type 'number'.
 - /grids/swissgrid_2/bbox/2: Value 'c' is not of type 'number'.
 - /grids/swissgrid_2/resolution_scale: Value '5.5' is not of type 'int'.
 - /grids/swissgrid_2/srs: Value '['epsg21781']' does not match pattern '^(?i)epsg:[0-9]+$'.
 - /grids/swissgrid_2/srs: Value '['epsg21781']' is not of type 'str'.
 - /grids/swissgrid_3: Cannot find required key 'bbox'.
 - /grids/swissgrid_3: Cannot find required key 'resolutions'.
 - /grids/swissgrid_3: Cannot find required key 'srs'.
 - /layers/hi!: Cannot find required key 'extension'.
 - /layers/hi!: Cannot find required key 'grid'.
 - /layers/hi!: Cannot find required key 'mime_type'."""
        ))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_zoom_errors(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_tiles -c tilegeneration/test-nosns.yaml -l point --zoom 4,10',
            main_func=generate.main)
        l.check(
            ('tilecloud_chain', 'INFO', 'Execute SQL: SELECT ST_AsBinary(geom) FROM (SELECT the_geom AS geom '
             'FROM tests.point) AS g.'),
            ('tilecloud_chain', 'WARNING', "zoom 10 is greater than the maximum "
             "zoom 4 of grid swissgrid_5 of layer point, ignored."),
            ('tilecloud_chain', 'WARNING', "zoom 4 corresponds to resolution 5 "
             "is smaller than the 'min_resolution_seed' 10 of layer point, ignored."),
        )

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_wrong_srs_auth(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_srs_auth.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_srs_auth.yaml' in invalid.
 - /grids/swissgrid_01/srs: Value 'toto:21781' does not match pattern '^(?i)epsg:[0-9]+$'."""  # noqa
        ))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_wrong_srs_id(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_srs_id.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_srs_id.yaml' in invalid.
 - /grids/swissgrid_01/srs: Value 'epsg:21781a' does not match pattern '^(?i)epsg:[0-9]+$'."""  # noqa
        ))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    def test_wrong_srs(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_srs.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_srs.yaml' in invalid.
 - /grids/swissgrid_01/srs: Value 'epsg21781' does not match pattern '^(?i)epsg:[0-9]+$'."""
        ))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    @attr(nopy2=True)
    @attr(nopy3=True)
    def test_wrong_map(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_map.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_map.yaml' in invalid.
 - Value: test is not of a mapping type"""
        ))

    @log_capture('tilecloud_chain')
    @attr(general=True)
    @attr(nopy3=True)
    def test_wrong_sequence(self, l):
        self.run_cmd(
            cmd='.build/venv/bin/generate_controller -c tilegeneration/wrong_sequence.yaml',
            main_func=controller.main)
        l.check((
            'tilecloud_chain', 'ERROR', """The config file 'tilegeneration/wrong_sequence.yaml' in invalid.
 - Value: test is not of a sequence type"""
        ))
