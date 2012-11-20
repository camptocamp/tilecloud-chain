# -*- coding: utf-8 -*-

import os
import shutil
from subprocess import Popen, PIPE

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller, TileGeneration


class TestMultihost(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir('../..')

    @classmethod
    def tearDownClass(self):
        os.chdir('tilecloud_chain/tests')

    def test_geodata(self):
        directory = os.getenv("HOME") + "/tilecloud_chain/tests/tilegeneration/hooks/"
        if os.path.exists(directory):
            shutil.rmtree(directory)  # pragma: no cover
        os.makedirs(directory)

        self.assert_files_generated(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml --disable-code '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main,
            directory,
            os.listdir('tilecloud_chain/tests/tilegeneration/hooks')
        )

    def test_none(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml --disable-geodata '
            '--disable-code --disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main,
            '')

    def test_code(self):
        if os.path.exists('/tmp/tests/test.conf'):
            os.remove('/tmp/tests/test.conf')  # pragma: no cover
        if os.path.exists('/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/post-restore-code'):
            os.remove('/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/'
                'post-restore-code')  # pragma: no cover

        out, err = self.run_cmd(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml --disable-geodata '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main)
        self.assertEquals(out, '==== Sync and build code ====\n')
        self.assertEquals(err, '')
        f = open('/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/post-restore-database', 'r')
        self.assert_result_equals(f.read(), "echo SUCCESS")
        f = open('/tmp/tests/test.conf', 'r')
        self.assert_result_equals(f.read(), 'test file')

        os.remove('/tmp/tests/test.conf')
        try:
            shutil.rmtree('/tmp/tests/test')
        except:  # pragma: no cover
            pass

    def test_database(self):
        out, err = self.run_cmd(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml --disable-geodata '
            '--disable-code --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main)
        self.assertEquals(out, '==== Deploy database ====\n')
        self.assertEquals(err, '')
        self.assert_result_equals(Popen([
            'sudo', '-u', 'postgres', 'psql', '-d', 'tests-deploy', '-c', 'SELECT * FROM test'
        ], stdout=PIPE).communicate()[0], """   name
-----------
 referance
(1 row)""")

    def test_time(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--time 2 -l polygon --host localhost  --disable-geodata --disable-database',
            controller.main,
            """==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Than mean generated tile size: 0.809 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.809""", True)

        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--time 1 -l polygon --host localhost --disable-geodata --disable-database '
            '--bbox 598000,198000,600000,200000 --zoom 4 --test 3',
            controller.main,
            """==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Than mean generated tile size: 0.780 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.780""", True)

    def test_time_near(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '-l point --time 50 --near 550000,180000 --zoom 4 --host localhost '
            '--disable-geodata --disable-database',
            controller.main,
            """==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Than mean generated tile size: 0.326 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.326""", True)

    def test_time_no_geom(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '-l point --time 1 --no-geom --bbox 550000,180000,555000,185000 --zoom 4 --host localhost '
            '--disable-geodata --disable-database',
            controller.main,
            """==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Than mean generated tile size: 0.326 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.326""", True)

    def test_near(self):
        class Opt:
            zoom = 3
            test = 196
            near = '600000,200000'
            verbose = False
            time = None
        gene = TileGeneration('tilecloud_chain/tests/tilegeneration/test.yaml', Opt(), 'point')
        self.assertEquals(gene.geom.bounds, (583840.0, 173360.0, 624800.0, 214320.0))
