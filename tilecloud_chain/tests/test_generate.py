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
    def tearDownClass(self):
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @attr(hash=True)
    def test_hash(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml -l point',
            generate.main,
            """Tile: 4/0/0:+8/+8
    empty_metatile_detection:
        size: 20743
        hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")

    @attr(get_bbox=True)
    def test_get_bbox(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --get-bbox 4/4/4 -l point',
            generate.main,
            """Tile bounds: [425120,343600,426400,344880]
""")
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --get-bbox 4/4/4:+1/+1 -l point',
            generate.main,
            """Tile bounds: [425120,343600,426400,344880]
""")
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --get-bbox 4/4/4:+2/+2 -l point',
            generate.main,
            """Tile bounds: [425120,342320,427680,344880]
""")

    @attr(hash_mapnik=True)
    def test_hash_mapnik(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml -l mapnik',
            generate.main,
            """Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")

    @attr(hash_mapnik_grid=True)
    def test_hash_mapnik_grid(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles --get-hash 4/0/0 -c tilegeneration/test.yaml -l all',
            generate.main,
            """Tile: 4/0/0
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""")

    @attr(test_all=True)
    def test_test_all(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('line', 0, 7, 4), ('polygon', 0, 5, 4)
            ]
        )

    @attr(zoom_identifier=True)
    def test_zoom_identifier(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1 -l polygon2 -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png', [
                ('polygon2', '1', 585, 429)
            ]
        )
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1 -l polygon2 -z 1',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png', [
                ('polygon2', '0_2', 2929, 2148)
            ]
        )
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1 -l polygon2 -z 2',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png', [
                ('polygon2', '0_1', 5859, 4296)
            ]
        )

    @attr(mbtile=True)
    def test_mbtile(self):
        from pyramid.testing import DummyRequest
        from pyramid.httpexceptions import HTTPNoContent, HTTPBadRequest
        from tilecloud_chain.views.serve import Serve

        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --cache mbtiles -l point_hash --zoom 1',
            generate.main,
            "/tmp/tiles/mbtiles/",
            '1.0.0/point_hash/default/2012/swissgrid_5.png.mbtiles', [()]
        )

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration': {
                'configfile': 'tilegeneration/test.yaml',
                'cache': 'mbtiles',
                'strict': True,
            }
        }
        request.params = {
            'Service': 'WMTS',
            'Request': 'GetTile',
            'Version': '1.0.0',
            'Format': 'png',
            'Layer': 'point_hash',
            'Style': 'default',
            'TileMatrixSet': 'swissgrid_5',
            'TileMatrix': '1',
            'TileRow': '14',
            'TileCol': '11',
        }
        serve = Serve(request)
        serve.serve()
        self.assertEquals(request.response.content_type, 'image/png')

        request.params['TileRow'] = '15'
        self.assertRaises(HTTPNoContent, serve.serve)

        request.params['Service'] = 'test'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Service'] = 'WMTS'
        request.params['Request'] = 'test'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Request'] = 'GetTile'
        request.params['Version'] = '0.9'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Version'] = '1.0.0'
        request.params['Format'] = 'jpeg'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Format'] = 'png'
        request.params['Layer'] = 'test'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Layer'] = 'point_hash'
        request.params['Style'] = 'test'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Style'] = 'default'
        request.params['TileMatrixSet'] = 'test'
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['TileMatrixSet'] = 'swissgrid_5'
        del request.params['Service']
        self.assertRaises(HTTPBadRequest, serve.serve)

        request.params['Service'] = 'test'
        request.registry.settings['tilegeneration']['strict'] = False
        serve = Serve(request)
        self.assertRaises(HTTPNoContent, serve.serve)

    @attr(zoom=True)
    def test_zoom(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash --zoom 1',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8)
            ]
        )

    @attr(zoom_range=True)
    def test_zoom_range(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash --zoom 1-3',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8),
                ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
            ]
        )

    @attr(no_zoom=True)
    def test_no_zoom(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('point_hash', 0, 5, 7), ('point_hash', 0, 7, 4),
                ('point_hash', 1, 11, 14), ('point_hash', 1, 15, 8),
                ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
            ]
        )

    @attr(py_buffer=True)
    def test_py_buffer(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_px_buffer --zoom 0-2',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/point_px_buffer/default/2012/swissgrid_5/%i/%i/%i.png', [
                (0, 5, 7), (0, 7, 4),
                (1, 11, 14), (1, 15, 8),
                (2, 29, 35), (2, 39, 21),
            ]
        )

    @attr(zoom_list=True)
    def test_zoom_list(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash --zoom 0,2,3',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png', [
                ('point_hash', 0, 5, 7), ('point_hash', 0, 7, 4),
                ('point_hash', 2, 29, 35), ('point_hash', 2, 39, 21),
                ('point_hash', 3, 58, 70), ('point_hash', 3, 78, 42),
            ]
        )

    @attr(layer_bbox=True)
    def test_layer_bbox(self):
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

    @attr(hash_generation=True)
    def test_hash_generation(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/point_hash/default/2012/swissgrid_5/0/%i/%i.png', [
                (5, 7), (7, 4)
            ]
        )

    @attr(mapnik=True)
    def test_mapnik(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l mapnik -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/mapnik/default/2012/swissgrid_5/0/%i/%i.png',
            list(product((5, 6, 7), (4, 5, 6, 7)))
        )

    @attr(mapnik_grid=True)
    def test_mapnik_grid(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l mapnik_grid -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/mapnik_grid/default/2012/swissgrid_5/0/%i/%i.json',
            list(product((5, 6, 7), (4, 5, 6, 7)))
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

    @attr(mapnik_grid_drop=True)
    def test_mapnik_grid_drop(self):
        self.assert_tiles_generated(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l mapnik_grid_drop -z 0',
            generate.main,
            "/tmp/tiles/",
            '1.0.0/mapnik_grid_drop/default/2012/swissgrid_5/0/%i/%i.json',
            ((5, 7), (7, 4))
        )

    @attr(not_authorised_user=True)
    def test_not_authorised_user(self):
        self.assert_cmd_exit_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test-authorised.yaml',
            generate.main,
            """not authorised, authorised user is: www-data.""")

    @log_capture()
    @attr(verbose=True)
    def test_verbose(self, l):
        self.run_cmd(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 2 -v -l polygon',
            generate.main
        )
        self.assert_result_equals(
            str(l),
            """tilecloud_chain INFO
  Execute SQL: SELECT ST_AsBinary\(geom\) FROM \(SELECT the_geom AS geom FROM tests.polygon\) AS g.
tilecloud_chain INFO
  Intersect with geom in 0:00:00.[0-9]*
tilecloud_chain.generate INFO
  0/4/5
tilecloud.store.url DEBUG
  GET http://localhost/mapserv\?STYLES=&SERVICE=WMS&FORMAT=image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&"""
            """VERSION=1.1.1&BBOX=522400.000000%2C196400.000000%2C548000.000000%2C222000.000000&LAYERS=polygon&"""
            """SRS=epsg%3A21781&TRANSPARENT=TRUE
requests.packages.urllib3.connectionpool INFO
  Starting new HTTP connection \(1\): localhost
requests.packages.urllib3.connectionpool DEBUG
  "GET /mapserv\?STYLES=&SERVICE=WMS&FORMAT=image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&VERSION=1.1.1&"""
            """BBOX=522400.000000%2C196400.000000%2C548000.000000%2C222000.000000&LAYERS=polygon&SRS=epsg%3A21781&"""
            """TRANSPARENT=TRUE HTTP/1.1" 200 None
tilecloud_chain INFO
  Get tile from WMS in 0:00:00.[0-9]*
tilecloud_chain INFO
  Store the tile in 0:00:00.[0-9]*
tilecloud_chain INFO
  Intersect with geom in 0:00:00.[0-9]*
tilecloud_chain.generate INFO
  0/4/6
tilecloud.store.url DEBUG
  GET http://localhost/mapserv\?STYLES=&SERVICE=WMS&FORMAT=image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&"""
            """VERSION=1.1.1&BBOX=522400.000000%2C170800.000000%2C548000.000000%2C196400.000000&LAYERS=polygon&"""
            """SRS=epsg%3A21781&TRANSPARENT=TRUE
requests.packages.urllib3.connectionpool DEBUG
  "GET /mapserv\?STYLES=&SERVICE=WMS&FORMAT=image%2Fpng&REQUEST=GetMap&HEIGHT=256&WIDTH=256&VERSION=1.1.1&"""
            """BBOX=522400.000000%2C170800.000000%2C548000.000000%2C196400.000000&LAYERS=polygon&SRS=epsg%3A21781&"""
            """TRANSPARENT=TRUE HTTP/1.1" 200 None
tilecloud_chain INFO
  Get tile from WMS in 0:00:00.[0-9]*
tilecloud_chain INFO
  Store the tile in 0:00:00.[0-9]*
tilecloud_chain.tests INFO

tilecloud_chain.tests INFO
""",
            True
        )

    @attr(time=True)
    def test_time(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml --time 2 -l polygon',
            generate.main,
            """size: 776
size: 860
size: 860
size: 860
time: [0-9]*
size: 860
size: 860
""", True, False)

    @attr(time_layer_bbox=True)
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
size: 854
""", True, False)

#    def test_daemonize(self):
#        self.assert_cmd_equals(
#            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -t 1 --daemonize',
#            generate.main,
#            """Daemonize with pid [0-9]*.""",
#            True)

    def _touch(self, pattern, tiles):
        for tile in tiles:
            path = pattern % tile
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            f = open(path, 'w')
            f.close()

    @attr(delete_meta=True)
    def test_delete_meta(self):
        if os.path.exists('/tmp/tiles/'):  # pragma: no cover
            shutil.rmtree('/tmp/tiles/')
        self._touch(
            '/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
            list(product(range(12), range(16)))
        )
        self.assert_tiles_generated_deleted(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash_no_meta -z 0',
            generate.main,
            '/tmp/tiles/',
            '1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png', [
                (5, 7), (7, 4)
            ]
        )

    @attr(delete_no_meta=True)
    def test_delete_no_meta(self):
        if os.path.exists('/tmp/tiles/'):
            shutil.rmtree('/tmp/tiles/')
        self._touch(
            '/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png',
            list(product(range(12), range(16)))
        )
        self.assert_tiles_generated_deleted(
            './buildout/bin/generate_tiles -c tilegeneration/test.yaml -l point_hash_no_meta -z 0',
            generate.main,
            '/tmp/tiles/',
            '1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png', [
                (5, 7), (7, 4)
            ]
        )
