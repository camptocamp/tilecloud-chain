# -*- coding: utf-8 -*-

import os
import shutil

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
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')
        f.close()

    @classmethod
    def tearDownClass(self):
        os.remove('/tmp/expired')

    @log_capture('tilecloud_chain', level=30)
    @attr(expire_tiles=True)
    @attr(general=True)
    def test_expire_tiles(self, l):
        GEOM = (
            'MULTIPOLYGON((('
            '537956.742292376 151362.137871755,'
            '537957.826834588 151467.196630838,'
            '537958.911357866 151572.253567258,'
            '537959.995862209 151677.30868105,'
            '538065.385383791 151676.221647663,'
            '538064.302719542 151571.166514771,'
            '538169.694100363 151570.08130827,'
            '538168.61325734 151465.024333684,'
            '538274.006497397 151463.940954131,'
            '538272.927475664 151358.882137846,'
            '538167.532395446 151359.965536437,'
            '538062.137334338 151361.05078107,'
            '537956.742292376 151362.137871755)))'
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
