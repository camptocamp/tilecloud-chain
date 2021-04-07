# -*- coding: utf-8 -*-

import os

from testfixtures import LogCapture

from tilecloud_chain import controller, generate
from tilecloud_chain.tests import CompareCase


class TestError(CompareCase):
    def setUp(self):  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    def test_resolution(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_resolutions.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                ("tilecloud_chain", "ERROR", "The resolution 0.1 * resolution_scale 5 is not an integer."),
            )
            log_capture.check(
                ("tilecloud_chain", "ERROR", "The resolution 0.1 * resolution_scale 5 is not an integer."),
            )

    def test_mapnik_grid_meta(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_mapnik_grid_meta.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    "The layer 'b' is of type Mapnik/Grid, that can't support matatiles.",
                )
            )

    def test_exists(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_exists.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_exists.yaml' is invalid.
 - /: 'caches' is a required property
 - /: 'grids' is a required property
 - /: 'layers' is a required property""",
                ),
            )

    def test_type(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -v -c tilegeneration/wrong_type.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_type.yaml' is invalid.
 - grids.swissgrid!: 'bbox' is a required property
 - grids.swissgrid!: 'resolutions' is a required property
 - grids.swissgrid!: 'srs' is a required property
 - grids.swissgrid_1.bbox.0: 'a' is not of type 'number'
 - grids.swissgrid_1.bbox.1: 'b' is not of type 'number'
 - grids.swissgrid_1.bbox.2: 'c' is not of type 'number'
 - grids.swissgrid_1.resolution_scale: 5.5 is not of type 'integer'
 - grids.swissgrid_1.srs: ['EPSG:21781'] is not of type 'string'
 - grids.swissgrid_2.srs: {} is not of type 'string'
 - grids.swissgrid_3.srs: 'epsg:21781' does not match '^EPSG:[0-9]+$'
 - grids.swissgrid_3: 'bbox' is a required property
 - grids.swissgrid_3: 'resolutions' is a required property
 - grids.swissgrid_4.srs: 'epsg21781' does not match '^EPSG:[0-9]+$'
 - grids.swissgrid_4: 'bbox' is a required property
 - grids.swissgrid_4: 'resolutions' is a required property
 - grids.swissgrid_5: 'bbox' is a required property
 - grids.swissgrid_5: 'resolutions' is a required property
 - grids.swissgrid_5: 'srs' is a required property
 - grids.swissgrid_6: None is not of type 'object'
 - grids: 'swissgrid!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$'
 - layers.hi!.dimensions.0.default: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!.dimensions.0.generate.0: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!.dimensions.0.name: 'DATE!' does not match '^(?!(?i)(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\\\\-~\\\\.]+$'
 - layers.hi!.dimensions.0.values.0: '2005!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!.dimensions.0.values.1: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!.dimensions.0.values.2: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!.dimensions.1.default: 1 is not of type 'string'
 - layers.hi!.dimensions.1.generate.0: 1 is not of type 'string'
 - layers.hi!.dimensions.1.values.0: 1 is not of type 'string'
 - layers.hi!.wmts_style: 'yo!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$'
 - layers.hi!: 'extension' is a required property
 - layers.hi!: 'grid' is a required property
 - layers.hi!: 'layers' is a required property
 - layers.hi!: 'mime_type' is a required property
 - layers.hi!: 'url' is a required property
 - layers: 'hi!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$'""",  # noqa
                )
            )

    def test_zoom_errors(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_tiles -c tilegeneration/test-nosns.yaml -l point --zoom 4,10",
                main_func=generate.main,
            )
            log_capture.check_present(
                (
                    "tilecloud_chain",
                    "INFO",
                    "Execute SQL: SELECT ST_AsBinary(geom) FROM (SELECT the_geom AS geom "
                    "FROM tests.point) AS g.",
                ),
                (
                    "tilecloud_chain",
                    "WARNING",
                    "zoom 10 is greater than the maximum zoom 4 of grid swissgrid_5 of layer point, ignored.",
                ),
                (
                    "tilecloud_chain",
                    "WARNING",
                    "zoom 4 corresponds to resolution 5 "
                    "is smaller than the 'min_resolution_seed' 10 of layer point, ignored.",
                ),
            )

    def test_wrong_srs_auth(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_srs_auth.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_srs_auth.yaml' is invalid.
 - grids.swissgrid_01.srs: 'toto:21781' does not match '^EPSG:[0-9]+$'""",  # noqa
                )
            )

    def test_wrong_srs_id(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_srs_id.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_srs_id.yaml' is invalid.
 - grids.swissgrid_01.srs: 'EPSG:21781a' does not match '^EPSG:[0-9]+$'""",  # noqa
                )
            )

    def test_wrong_srs(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_srs.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_srs.yaml' is invalid.
 - grids.swissgrid_01.srs: 'EPSG21781' does not match '^EPSG:[0-9]+$'""",
                )
            )

    def test_wrong_map(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_map.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_map.yaml' is invalid.
 - /: 'caches' is a required property
 - /: 'grids' is a required property
 - layers.test.empty_tile_detection: 'test' is not of type 'object'
 - layers.test: 'extension' is a required property
 - layers.test: 'grid' is a required property
 - layers.test: 'layers' is a required property
 - layers.test: 'mime_type' is a required property
 - layers.test: 'url' is a required property
 - layers.test: 'wmts_style' is a required property""",
                )
            )

    def test_wrong_sequence(self):
        with LogCapture("tilecloud_chain") as log_capture:
            self.run_cmd(
                cmd=".build/venv/bin/generate_controller -c tilegeneration/wrong_sequence.yaml",
                main_func=controller.main,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file 'tilegeneration/wrong_sequence.yaml' is invalid.
 - /: 'caches' is a required property
 - /: 'layers' is a required property
 - grids.test.resolutions: 'test' is not of type 'array'
 - grids.test: 'bbox' is a required property
 - grids.test: 'srs' is a required property""",
                )
            )
