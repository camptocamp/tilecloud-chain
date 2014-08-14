# -*- coding: utf-8 -*-

import os
import shutil
from itertools import product

from testfixtures import log_capture
from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import generate


class TestGenerate(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(__file__))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @classmethod
    def tearDownClass(self):
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @log_capture('tilecloud_chain', level=30)
    @attr(get_hash=True)
    @attr(generate=True)
    @attr(general=True)
    def test_get_hash(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s --get-hash 4/0/0 -c tilegeneration/test.yaml -l point' % d,
                main_func=generate.main,
                expected="""Tile: 4/0/0:+8/+8
        empty_metatile_detection:
            size: 20743
            hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
    Tile: 4/0/0
        empty_tile_detection:
            size: 334
            hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")

        l.check()

    @attr(get_wrong_hash=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_get_wrong_hash(self, l):
        for d in ('-d', '-q'):
            self.assert_cmd_exit_equals(
                cmd='./buildout/bin/generate_tiles %s --get-hash 0/7/5 -c tilegeneration/test.yaml -l all' % d,
                main_func=generate.main,
                expected="""Error: image is not uniform.""")
        l.check()

    @attr(get_bbox=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_get_bbox(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml --get-bbox 4/4/4 -l point' % d,
                main_func=generate.main,
                expected="""Tile bounds: [425120,343600,426400,344880]
""")
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml --get-bbox 4/4/4:+1/+1 -l point' % d,
                main_func=generate.main,
                expected="""Tile bounds: [425120,343600,426400,344880]
""")
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml --get-bbox 4/4/4:+2/+2 -l point' % d,
                main_func=generate.main,
                expected="""Tile bounds: [425120,342320,427680,344880]
""")
        l.check()

    @attr(hash_mapnik=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_hash_mapnik(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s --get-hash 4/0/0 -c tilegeneration/test.yaml -l mapnik' % d,
                main_func=generate.main,
                expected="""Tile: 4/0/0
        empty_tile_detection:
            size: 334
            hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")
        l.check()

    @attr(hash_mapnik_grid=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_hash_mapnik_grid(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s --get-hash 4/0/0 -c tilegeneration/test.yaml -l all' % d,
                main_func=generate.main,
                expected="""Tile: 4/0/0
        empty_tile_detection:
            size: 334
            hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")
        l.check()

    @attr(test_all=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_test_all(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 1' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('line', 0, 7, 4), ('polygon', 0, 5, 4)
                ],
                regex=True,
                expected="""The tile generation of layer 'line' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 40
Nb tiles dropped: 39
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 733 o
Time per tiles: [0-9]+ ms
Size per tile: 733 o

The tile generation of layer 'polygon' is finish
Nb generated tiles: 1
Nb tiles dropped: 0
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [45][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: [45][0-9][0-9] o

""",
            )
        l.check()

    @attr(test_dimensions=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_test_dimensions(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 1 '
                '--dimensions DATE=2013' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2013/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('line', 0, 7, 4), ('polygon', 0, 5, 4)
                ],
                regex=True,
                expected="""The tile generation of layer 'line' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 40
Nb tiles dropped: 39
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 733 o
Time per tiles: [0-9]+ ms
Size per tile: 733 o

The tile generation of layer 'polygon' is finish
Nb generated tiles: 1
Nb tiles dropped: 0
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [45][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: [45][0-9][0-9] o

""",
            )
        l.check()

    @attr(multigeom=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_multigeom(self, l):
        self.assert_tiles_generated(
            cmd='./buildout/bin/generate_tiles -c tilegeneration/test-multigeom.yaml',
            main_func=generate.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/pp/default/2012/swissgrid_5/%i/%i/%i.png',
            tiles=[
                (0, 5, 4),
                (0, 5, 5),
                (0, 5, 6),
                (0, 5, 7),
                (0, 6, 4),
                (0, 6, 5),
                (0, 6, 6),
                (0, 6, 7),
                (0, 7, 4),
                (0, 7, 5),
                (0, 7, 6),
                (0, 7, 7),
                (1, 11, 8),
                (1, 11, 9),
                (1, 11, 10),
                (1, 11, 11),
                (1, 11, 12),
                (1, 11, 13),
                (1, 11, 14),
                (1, 12, 8),
                (1, 12, 9),
                (1, 12, 10),
                (1, 12, 11),
                (1, 12, 12),
                (1, 12, 13),
                (1, 12, 14),
                (1, 13, 8),
                (1, 13, 9),
                (1, 13, 10),
                (1, 13, 11),
                (1, 13, 12),
                (1, 13, 13),
                (1, 13, 14),
                (1, 14, 8),
                (1, 14, 9),
                (1, 14, 10),
                (1, 14, 11),
                (1, 14, 12),
                (1, 14, 13),
                (1, 14, 14),
                (1, 15, 8),
                (1, 15, 9),
                (1, 15, 10),
                (1, 15, 11),
                (1, 15, 12),
                (1, 15, 13),
                (1, 15, 14),
                (2, 29, 35),
                (2, 39, 21),
                (3, 78, 42),
                (3, 58, 70),
            ],
            regex=True,
            expected="""The tile generation of layer 'pp' is finish
Nb generated tiles: 51
Nb tiles dropped: 0
Nb tiles stored: 51
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [34][0-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: [79][0-9][0-9] o

""",
        )
        l.check()

    @attr(zoom_identifier=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_zoom_identifier(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png',
                tiles=[
                    ('polygon2', '1', 585, 429)
                ],
                regex=True,
                expected="""The tile generation of layer 'polygon2' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 42
Nb tiles dropped: 41
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 389 o
Time per tiles: [0-9]+ ms
Size per tile: 389 o

""",
            )
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 1' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png',
                tiles=[
                    ('polygon2', '0_2', 2929, 2148)
                ],
                regex=True,
                expected="""The tile generation of layer 'polygon2' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 34
Nb tiles dropped: 33
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 517 o
Time per tiles: [0-9]+ ms
Size per tile: 517 o

""",
            )
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 2' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png',
                tiles=[
                    ('polygon2', '0_1', 5859, 4296)
                ],
                regex=True,
                expected="""The tile generation of layer 'polygon2' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 4
Nb tiles dropped: 3
Nb tiles stored: 1
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 676 o
Time per tiles: [0-9]+ ms
Size per tile: 676 o

""",
            )
        l.check()

    @attr(empty_bbox=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_empty_bbox(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml '
                    '-l point_hash --bbox 700000 250000 800000 300000' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s',
                tiles=[
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 0
Nb metatiles dropped: 0
Nb generated tiles: 0
Nb tiles dropped: 0
Nb tiles stored: 0
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 0.0 o
Time per tiles: [0-9]+ ms
Size per tile: -1 o

""",
            )
        # second time for the debug mode
        l.check(
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 0"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 1"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 2"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 3"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 0"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 1"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 2"),
            ('tilecloud_chain', 'WARNING', "bounds empty for zoom 3"),
        )

    @attr(zoom=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_zoom(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash --zoom 1' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8)
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(zoom_range=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_zoom_range(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash --zoom 1-3' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8),
                    ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                    ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 9
Nb metatiles dropped: 4
Nb generated tiles: 320
Nb tiles dropped: 314
Nb tiles stored: 6
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 2.[0-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(no_zoom=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_no_zoom(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('point_hash', 0, 5, 7), ('point_hash', 0, 7, 4),
                    ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8),
                    ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                    ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 10
Nb metatiles dropped: 4
Nb generated tiles: 384
Nb tiles dropped: 376
Nb tiles stored: 8
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 3.[0-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(py_buffer=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_py_buffer(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml '
                    '-l point_px_buffer --zoom 0-2' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/point_px_buffer/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    (0, 5, 7), (0, 7, 4),
                    (1, 11, 14), (1, 15, 8),
                    (2, 29, 35), (2, 39, 21),
                ],
                regex=True,
                expected="""The tile generation of layer 'point_px_buffer' is finish
Nb generated metatiles: 10
Nb metatiles dropped: 4
Nb generated tiles: 384
Nb tiles dropped: 378
Nb tiles stored: 6
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 2.[0-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(zoom_list=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_zoom_list(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash --zoom 0,2,3' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png',
                tiles=[
                    ('point_hash', 0, 5, 7), ('point_hash', 0, 7, 4),
                    ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                    ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 9
Nb metatiles dropped: 4
Nb generated tiles: 320
Nb tiles dropped: 314
Nb tiles stored: 6
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 2.[0-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(layer_bbox=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_layer_bbox(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l polygon -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                regex=True,
                expected="""The tile generation of layer 'polygon' is finish
Nb generated tiles: 12
Nb tiles dropped: 0
Nb tiles stored: 12
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [0-9.]+ Kio
Time per tiles: [0-9.]+ ms
Size per tile: [69][0-9][0-9] o

""",
            )

            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l polygon -z 0'
                ' -b 550000 170000 560000 180000' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (6, 5), (7, 5)
                ],
                regex=True,
                expected="""The tile generation of layer 'polygon' is finish
Nb generated tiles: 2
Nb tiles dropped: 0
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 1.[6-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: [89][0-9][0-9] o

""",
            )

            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l polygon -z 0'
                ' -b 550000.0 170000.0 560000.0 180000.0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (6, 5), (7, 5)
                ],
                regex=True,
                expected="""The tile generation of layer 'polygon' is finish
Nb generated tiles: 2
Nb tiles dropped: 0
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 1.[6-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: [89][0-9][0-9] o

""",
            )

            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l all -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/all/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (6, 5), (7, 5)
                ],
                regex=True,
                expected="""The tile generation of layer 'all' is finish
Nb generated tiles: 2
Nb tiles dropped: 0
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 1.[6-9] Kio
Time per tiles: [0-9]+ ms
Size per tile: [89][0-9][0-9] o

""",
            )
        l.check()

    @attr(hash_generation=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_hash_generation(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/point_hash/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (5, 7), (7, 4)
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 9[0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )
        l.check()

    @attr(mapnik=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_mapnik(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l mapnik -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/mapnik/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                regex=True,
                expected="""The tile generation of layer 'mapnik' is finish
Nb generated tiles: 12
Nb tiles dropped: 0
Nb tiles stored: 12
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 9.7 Kio
Time per tiles: [0-9]+ ms
Size per tile: 824 o

""",
            )
        l.check()

    @attr(mapnik_grid=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_mapnik_grid(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l mapnik_grid -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/mapnik_grid/default/2012/swissgrid_5/0/%i/%i.json',
                tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                regex=True,
                expected="""The tile generation of layer 'mapnik_grid' is finish
Nb generated tiles: 12
Nb tiles dropped: 0
Nb tiles stored: 12
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 4.5 Kio
Time per tiles: [0-9]+ ms
Size per tile: 385 o

""",
            )
            f = open('/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/5/5.json', 'r')
            self.assert_result_equals(
                f.read(), '{"keys": ["", "1"], "data": {"1": {"name": "polygon1"}}, "grid": '
                '["                ", "                ", "                ", "                ", "                "'
                ', "                ", "                ", "                ", "                ", "                "'
                ', "                ", "                ", "                ", "                ", "!!!!!!!!!!!!!!!!", '
                '"!!!!!!!!!!!!!!!!"]}')
            f = open('/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/6/5.json', 'r')
            self.assert_result_equals(
                f.read(), '{"keys": ["1"], "data": {"1": {"name": "polygon1"}}, "grid": '
                '["                ", "                ", "                ", "                ", "                ", '
                '"                ", "                ", "                ", "                ", "                ", '
                '"                ", "                ", "                ", "                ", "                ", '
                '"                "]}')
        l.check()

    @attr(mapnik_grid_drop=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_mapnik_grid_drop(self, l):
        for d in ('-d', ''):
            self.assert_tiles_generated(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l mapnik_grid_drop -z 0' % d,
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern='1.0.0/mapnik_grid_drop/default/2012/swissgrid_5/0/%i/%i.json',
                tiles=((5, 7), (7, 4)),
                regex=True,
                expected="""The tile generation of layer 'mapnik_grid_drop' is finish
Nb generated tiles: 12
Nb tiles dropped: 10
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 768 o
Time per tiles: [0-9]+ ms
Size per tile: 384 o

""",
            )
        l.check()

    @attr(not_authorised_user=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_not_authorised_user(self, l):
        for d in ('-d', '-q'):
            self.assert_cmd_exit_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-authorised.yaml' % d,
                main_func=generate.main,
                expected="""not authorised, authorised user is: www-data.""")
        l.check()

    @attr(verbose=True)
    @attr(generate=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_verbose(self, l):
        for d in ('-d', ''):
            self.run_cmd(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -t 2 -v -l polygon' % d,
                main_func=generate.main
            )
        l.check()

    @attr(time=True)
    @log_capture('tilecloud_chain', level=30)
    def test_time(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml --time 2 -l polygon' % d,
                main_func=generate.main,
                expected="""size: 770
size: 862
size: 862
size: 862
time: [0-9]*
size: 862
size: 862
""",
                regex=True,
                empty_err=True)
        l.check()

    @attr(time_layer_bbox=True)
    @log_capture('tilecloud_chain', level=30)
    def test_time_layer_bbox(self, l):
        for d in ('-d', ''):
            self.assert_cmd_equals(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml --time 2 -l all' % d,
                main_func=generate.main,
                expected="""size: 1010
size: 1010
size: 1010
size: 1010
time: [0-9]*
size: 1010
size: 1010
""",
                regex=True,
                empty_err=True)
        l.check()

#    @attr(daemonize=True)
#    @attr(generate=True)
#    @attr(general=True)
#    @log_capture('tilecloud_chain', level=30)
#    def test_daemonize(self, l):
#        self.assert_cmd_equals(
#            cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test.yaml -t 1 --daemonize' % d,
#            main_func=generate.main,
#            expected="""Daemonize with pid [0-9]*.""",
#            regex=True)
#        l.check()

    def _touch(self, tiles_pattern, tiles):
        for tile in tiles:
            path = tiles_pattern % tile
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            f = open(path, 'w')
            f.close()

    @attr(delete_meta=True)
    @attr(generate=True)
    @attr(general=True)
    def test_delete_meta(self):
        for d in ('-d', ''):
            if os.path.exists('/tmp/tiles/'):
                shutil.rmtree('/tmp/tiles/')
            self._touch(
                tiles_pattern='/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=list(product(range(12), range(16)))
            )
            self.assert_tiles_generated_deleted(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash_no_meta -z 0' % d,
                main_func=generate.main,
                directory='/tmp/tiles/',
                tiles_pattern='1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (5, 7), (7, 4)
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash_no_meta' is finish
Nb generated tiles: 247
Nb tiles dropped: 245
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )

    @attr(delete_no_meta=True)
    @attr(generate=True)
    @attr(general=True)
    def test_delete_no_meta(self):
        for d in ('-d', ''):
            if os.path.exists('/tmp/tiles/'):
                shutil.rmtree('/tmp/tiles/')
            self._touch(
                tiles_pattern='/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=list(product(range(12), range(16)))
            )
            self.assert_tiles_generated_deleted(
                cmd='./buildout/bin/generate_tiles %s -c tilegeneration/test-nosns.yaml -l point_hash_no_meta -z 0' % d,
                main_func=generate.main,
                directory='/tmp/tiles/',
                tiles_pattern='1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
                tiles=[
                    (5, 7), (7, 4)
                ],
                regex=True,
                expected="""The tile generation of layer 'point_hash_no_meta' is finish
Nb generated tiles: 247
Nb tiles dropped: 245
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )

    @attr(error_file=True)
    @attr(generate=True)
    @attr(general=True)
    def test_error_file(self):
        if os.path.exists('error.list'):
            os.remove('error.list')
        self.assert_main_except_equals(
            cmd='./buildout/bin/generate_tiles -q -c tilegeneration/test-nosns.yaml -l point_error',
            main_func=generate.main,
            regex=True,
            expected=[[
                'error.list',
                u"""# \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] Start the layer 'point_error' generation
0/0/0:\+8/\+8 # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: """
                """msWMSLoadGetMapParams\(\): WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. """
                """A layer might be disabled for this request\. Check wms/ows_enable_request settings\.'
0/0/8:\+8/\+8 # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: """
                """msWMSLoadGetMapParams\(\): WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. """
                """A layer might be disabled for this request\. Check wms/ows_enable_request settings\.'
0/8/0:\+8/\+8 # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: """
                """msWMSLoadGetMapParams\(\): WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. """
                """A layer might be disabled for this request\. Check wms/ows_enable_request settings\.'
"""]],
        )

        self.assert_tiles_generated(
            cmd='./buildout/bin/generate_tiles -d -c tilegeneration/test-nosns.yaml -l point_hash'
                ' --tiles error.list',
            main_func=generate.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/point_hash/default/2012/swissgrid_5/%i/%i/%i.png',
            tiles=[
                (0, 5, 7), (0, 7, 4)
            ],
            regex=True,
            expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 3
Nb metatiles dropped: 1
Nb generated tiles: 128
Nb tiles dropped: 126
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )
