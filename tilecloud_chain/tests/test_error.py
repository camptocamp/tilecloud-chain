# -*- coding: utf-8 -*-

from testfixtures import log_capture

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller, generate, TileGeneration


class TestError(CompareCase):

    @log_capture('tilecloud_chain')
    @attr(resolution=True)
    @attr(general=True)
    def test_resolution(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_controller -c tilegeneration/wrong_resolutions.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The resolution 0.1 * resolution_scale 5 is not an integer."),
        )

    @log_capture('tilecloud_chain')
    @attr(mapnik_grid_meta=True)
    @attr(general=True)
    def test_mapnik_grid_meta(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_controller -c tilegeneration/wrong_mapnik_grid_meta.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The layer 'b' is of type Mapnik/Grid, that can't support matatiles."),
        )

    @log_capture('tilecloud_chain')
    @attr(exists=True)
    @attr(general=True)
    def test_exists(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_controller -c tilegeneration/wrong_exists.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The attribute 'grids' is required in the object config."),
        )

    @log_capture('tilecloud_chain')
    @attr(type=True)
    @attr(general=True)
    def test_type(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_controller -v -c tilegeneration/wrong_type.yaml',
            main_func=controller.main)
        l.check(
            ('tilecloud_chain', 'ERROR', "The attribute 'name' of the object grid[swissgrid!] is not a "
                "value 'swissgrid!' don't respect regex '^[a-zA-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'resolutions' is required in the object grid[swissgrid!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' is required in the object grid[swissgrid!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' is required in the object grid[swissgrid!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'resolutions' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' is required in the object grid[swissgrid_3]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'resolution_scale' of the object grid[swissgrid_2] "
                "is not a <type 'int'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' of the object grid[swissgrid_2] "
                "has an element who is not a right float expression: a."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' of the object grid[swissgrid_2] is not a <type 'str'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'bbox' of the object grid[swissgrid_1] is not an array."),
            ('tilecloud_chain', 'ERROR', "The attribute 'srs' of the object grid[swissgrid_1] is not a <type 'str'>."),
            ('tilecloud_chain', 'ERROR', "The attribute 'name' of the object layer[hi!] is not a "
                "value 'hi!' don't respect regex '^[a-zA-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'grid' is required in the object layer[hi!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'type' is required in the object layer[hi!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'extension' is required in the object layer[hi!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'mime_type' is required in the object layer[hi!]."),
            ('tilecloud_chain', 'ERROR', "The attribute 'wmts_style' of the object layer[hi!] is not a "
                "value 'yo!' don't respect regex '^[a-zA-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'name' of the object layer[hi!].dimensions[DATE!] is not a "
                "value 'DATE!' don't respect regex '^[A-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'value' of the object layer[hi!].dimensions[DATE!] is not a "
                "value '2012!' don't respect regex '^[a-zA-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'default' of the object layer[hi!].dimensions[DATE!] is not a "
                "value '2010!' don't respect regex '^[a-zA-Z0-9_]+$'."),
            ('tilecloud_chain', 'ERROR', "The attribute 'name' of the object layer[hi!].dimensions[time] is not a "
                "value 'time' don't respect regex '^[A-Z0-9_]+$'.")
        )

    @log_capture('tilecloud_chain')
    @attr(zoom_errors=True)
    @attr(general=True)
    def test_zoom_errors(self, l):
        self.run_cmd(
            cmd='./buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point --zoom 4,10',
            main_func=generate.main)
        l.check(
            ('tilecloud_chain', 'INFO', 'Execute SQL: SELECT ST_AsBinary(geom) FROM (SELECT the_geom AS geom '
             'FROM tests.point) AS g.'),
            ('tilecloud_chain', 'WARNING', "Warning: zoom 10 is greater than the maximum "
             "zoom 4 of grid swissgrid_5 of layer point, ignored."),
            ('tilecloud_chain', 'WARNING', "Warning: zoom 4 corresponds to resolution 5.0 "
             "is smaller than the 'min_resolution_seed' 10.0 of layer point, ignored."),
        )

    @attr(validate_type=True)
    @attr(general=True)
    def test_validate_type(self):
        class Opt:
            verbose = False
            debug = False
            test = 0
            zoom = None
        gene = TileGeneration('tilegeneration/test.yaml', Opt())
        obj = {'value': 1}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), False)
        self.assertEquals(obj['value'],  1)

        obj = {'value': 1.0}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), True)

        obj = {'value': '1 + 1'}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), False)
        self.assertEquals(obj['value'],  2)

        obj = {'value': '1 * 1.5'}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), False)
        self.assertEquals(obj['value'],  2)

        obj = {'value': 'a'}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), True)

        obj = {'value': {}}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), True)

        obj = {'value': []}
        self.assertEquals(gene.validate(obj, 'object', 'value', int), True)

        obj = {'value': 1}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), False)
        self.assertEquals(obj['value'],  1.0)

        obj = {'value': 1.0}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), False)
        self.assertEquals(obj['value'],  1.0)

        obj = {'value': '1 + 1'}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), False)
        self.assertEquals(obj['value'],  2.0)

        obj = {'value': '1 * 1.5'}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), False)
        self.assertEquals(obj['value'],  1.5)

        obj = {'value': 'a'}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), True)

        obj = {'value': {}}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), True)

        obj = {'value': []}
        self.assertEquals(gene.validate(obj, 'object', 'value', float), True)
