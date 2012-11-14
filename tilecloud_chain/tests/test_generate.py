# -*- coding: utf-8 -*-

import os
import shutil
from itertools import product

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import generate


class TestGenerate(CompareCase):

    @classmethod
    def tearDownClass(self):
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    def test_hash(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml',
            generate.main,
            """Tile: 4/0/0:+8/+8
    empty_metatile_detection:
        size: 20743
        hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
Tile: 4/0/0:+8/+8
    empty_metatile_detection:
        size: 20743
        hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8""")

    def test_hash_mapnik(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml -l mapnik',
            generate.main,
            """Tile: 4/0/0:+8/+8
    empty_metatile_detection:
        size: 16375
        hash: b1087dd40c5d54e70c1824355a7dec802224c7f5
Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8""")

    def test_hash_mapnik_grid(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml -l all',
            generate.main,
            """Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8""")

    def test_test_all(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('line', 0, 7, 4), ('polygon', 0, 5, 4)
            ]
        )

    def test_zoom(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point --zoom 1',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('point', 1, 11, 14), ('point', 1, 15, 8)
        ])

    def test_bbox(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l polygon -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png',
            list(product((5, 6, 7), (4, 5, 6, 7)))
        )

        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l polygon -z 0'
            ' -b 550000,170000,560000,180000',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png', [
                (6, 5), (7, 5)
            ]
        )

        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l all -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/all/default/2012/swissgrid_5/0/%i/%i.png', [
                (6, 5), (7, 5)
            ]
        )

    def test_hash_generation(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/point_hash/default/2012/swissgrid_5/0/%i/%i.png', [
                (5, 7), (7, 4)
        ])

    def test_mapnik(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l mapnik -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/mapnik/default/2012/swissgrid_5/0/%i/%i.png',
            list(product((5, 6, 7), (4, 5, 6, 7)))
        )

    def test_mapnik_grid(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l mapnik_grid -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/mapnik_grid/default/2012/swissgrid_5/0/%i/%i.json',
            list(product((5, 6, 7), (4, 5, 6, 7)))
        )
        f = open('/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/5/5.json', 'r')
        self.assert_result_equals(f.read(), '{"keys": ["", "1"], "data": {"1": {"name": "polygon1"}}, "grid": '
            '["                ", "                ", "                ", "                ", "                "'
            ', "                ", "                ", "                ", "                ", "                "'
            ', "                ", "                ", "                ", "                ", "!!!!!!!!!!!!!!!!", '
            '"!!!!!!!!!!!!!!!!"]}')
        f = open('/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/6/5.json', 'r')
        self.assert_result_equals(f.read(), '{"keys": ["1"], "data": {"1": {"name": "polygon1"}}, "grid": '
            '["                ", "                ", "                ", "                ", "                ", '
            '"                ", "                ", "                ", "                ", "                ", '
            '"                ", "                ", "                ", "                ", "                ", '
            '"                "]}')

    def test_not_authorised_user(self):
        self.assert_cmd_exit_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test-authorised.yaml',
            generate.main,
            """not authorised, authorised user is: www-data.""")

    def test_time(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --time 2 -l polygon',
            generate.main,
            """size: 776
size: 860
size: 860
size: 768
time: [0-9]*
size: 854
size: 854""", True, False)

    def test_time_layer_bbox(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --time 2 -l all',
            generate.main,
            """size: 854
size: 854
size: 854
size: 854
time: [0-9]*
size: 854
size: 854""", True, False)

#    def test_daemonize(self):
#        self.assert_cmd_equals(
#            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1 --daemonize',
#            generate.main,
#            """Daemonize with pid [0-9]*.""",
#            True)
