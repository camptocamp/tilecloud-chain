# -*- coding: utf-8 -*-

import os

import psycopg2
from testfixtures import log_capture
from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import expiretiles


class TestExpireTiles(CompareCase):

    @classmethod
    def setUpClass(cls):
        f = open('/tmp/expired', 'w')
        f.write('18/135900/92720\n')
        f.write('18/135900/92721\n')
        f.write('18/135900/92722\n')
        f.write('18/135901/92721\n')
        f.write('18/135901/92722\n')
        f.write('18/135902/92722\n')
        f.close()

        f = open('/tmp/expired-empty', 'w')
        f.close()

    @classmethod
    def tearDownClass(self):
        os.remove('/tmp/expired')
        os.remove('/tmp/expired-empty')

    @log_capture('tilecloud_chain', level=30)
    @attr(expire_tiles=True)
    @attr(general=True)
    def test_expire_tiles(self, l):
        GEOM = (
            'MULTIPOLYGON((('
            '537956.702147466 151362.192371583,'
            '537957.786689681 151467.251130455,'
            '537958.871212961 151572.30806667,'
            '537959.955717307 151677.363180256,'
            '538065.345238682 151676.276146866,'
            '538064.26257443 151571.22101418,'
            '538169.653955045 151570.135807676,'
            '538168.573112019 151465.078833297,'
            '538273.96635187 151463.995453742,'
            '538272.887330133 151358.936637663,'
            '538167.492250122 151360.020036253,'
            '538062.09718922 151361.105280892,'
            '537956.702147466 151362.192371583)))'
        )

        self.assert_cmd_equals(
            cmd=[
                './buildout/bin/import_expiretiles',
                '--create', '--delete', '--srid', '21781',
                '/tmp/expired',
                'user=postgres password=postgres dbname=tests host=localhost',
                'expired', 'the_geom',
            ],
            main_func=expiretiles.main,
            expected='''Import successful
'''
        )
        connection = psycopg2.connect('user=postgres password=postgres dbname=tests host=localhost')
        cursor = connection.cursor()
        cursor.execute('SELECT ST_AsText(the_geom) FROM expired')
        geoms = [str(r[0]) for r in cursor.fetchall()]
        self.assertEqual(len(geoms), 1)
        self.assertEqual(geoms[0], GEOM)

        self.assert_cmd_equals(
            cmd=[
                './buildout/bin/import_expiretiles',
                '--create', '--delete', '--srid', '21781',
                '/tmp/expired',
                'user=postgres password=postgres dbname=tests host=localhost',
                'expired', 'the_geom',
            ],
            main_func=expiretiles.main,
            expected='''Import successful
'''
        )
        connection = psycopg2.connect('user=postgres password=postgres dbname=tests host=localhost')
        cursor = connection.cursor()
        cursor.execute('SELECT ST_AsText(the_geom) FROM expired')
        geoms = [str(r[0]) for r in cursor.fetchall()]
        self.assertEqual(len(geoms), 1)
        self.assertEqual(geoms[0], GEOM)

        self.assert_cmd_equals(
            cmd=[
                './buildout/bin/import_expiretiles',
                '--simplify', '1000', '--create', '--delete',
                '/tmp/expired',
                'user=postgres password=postgres dbname=tests host=localhost',
                'expired2',
            ],
            main_func=expiretiles.main,
            expected='''Import successful
'''
        )
        connection = psycopg2.connect('user=postgres password=postgres dbname=tests host=localhost')
        cursor = connection.cursor()
        cursor.execute('SELECT ST_AsText(geom) FROM expired2')
        geoms = [str(r[0]) for r in cursor.fetchall()]
        self.assertEqual(len(geoms), 1)
        self.assertEqual(
            geoms[0],
            'MULTIPOLYGON((('
            '738075.945018921 5862567.19460037,'
            '738075.945018921 5862720.06865692,'
            '738075.945018921 5862872.94271347,'
            '738075.945018921 5863025.81677002,'
            '738228.819075469 5863025.81677002,'
            '738228.819075469 5862872.94271347,'
            '738381.693132021 5862872.94271347,'
            '738381.693132021 5862720.06865692,'
            '738534.567188568 5862720.06865692,'
            '738534.567188568 5862567.19460037,'
            '738381.693132021 5862567.19460037,'
            '738228.819075469 5862567.19460037,'
            '738075.945018921 5862567.19460037)))'
        )

        l.check()

    @log_capture('tilecloud_chain', level=30)
    @attr(expire_tiles=True)
    @attr(expire_tiles_empty=True)
    @attr(general=True)
    def test_expire_tiles_empty(self, l):
        self.assert_cmd_equals(
            cmd=[
                './buildout/bin/import_expiretiles',
                '--create', '--delete', '--srid', '21781',
                '/tmp/expired-empty',
                'user=postgres password=postgres dbname=tests host=localhost',
                'expired', 'the_geom',
            ],
            main_func=expiretiles.main,
            expected='''No coords found
'''
        )
        connection = psycopg2.connect('user=postgres password=postgres dbname=tests host=localhost')
        cursor = connection.cursor()
        cursor.execute('SELECT the_geom FROM expired')
        geoms = cursor.fetchall()
        self.assertEqual(len(geoms), 0)
