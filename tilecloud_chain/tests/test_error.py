# -*- coding: utf-8 -*-

from testfixtures import log_capture

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller


class TestError(CompareCase):

    @log_capture()
    def test_resolution(self, l):
        self.run_cmd(
            './buildout/bin/generate_controller -c tilegeneration/wrong_resolutions.yaml',
            controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The reolution 0.1 * resolution_scale 5 is not an integer."),
            ('tilecloud_chain.tests', 'INFO', ''),
            ('tilecloud_chain.tests', 'INFO', ''),
        )

    @log_capture()
    def test_mapnik_grid_meta(self, l):
        self.run_cmd(
            './buildout/bin/generate_controller -c tilegeneration/wrong_mapnik_grid_meta.yaml',
            controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The layer 'b' is of type Mapnik/Grid, that can't support matatiles."),
            ('tilecloud_chain.tests', 'INFO', ''),
            ('tilecloud_chain.tests', 'INFO', ''),
        )

    @log_capture()
    def test_exists(self, l):
        self.run_cmd(
            './buildout/bin/generate_controller -c tilegeneration/wrong_exists.yaml',
            controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The attribute 'grids' is required in the object config."),
            ('tilecloud_chain.tests', 'INFO', ''),
            ('tilecloud_chain.tests', 'INFO', ''),
        )

    @log_capture()
    def test_type(self, l):
        self.run_cmd(
            './buildout/bin/generate_controller -v -c tilegeneration/wrong_type.yaml',
            controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The attribute 'resolutions' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'resolution_scale' of the object grid[swissgrid_2] "
                "is not a <type 'int'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' of the object grid[swissgrid_2] "
                "has an element who is not a <type 'float'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' of the object grid[swissgrid_2] is not a <type 'str'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' of the object grid[swissgrid_1] is not an array."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' of the object grid[swissgrid_1] is not a <type 'str'>."),
            ('tilecloud_chain.tests', 'INFO', ''),
            ('tilecloud_chain.tests', 'INFO', ''),
        )
