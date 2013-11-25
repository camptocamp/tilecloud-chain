# -*- coding: utf-8 -*-

import os
import shutil
from subprocess import Popen, PIPE

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import amazon, TileGeneration


class TestMultihost(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    @attr(geodata=True)
    def test_geodata(self):
        directory = os.getenv("HOME") + "/tilecloud_chain/tests/tilegeneration/hooks/"
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

        self.assert_files_generated(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml --disable-code '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            main_func=amazon.main,
            directory=directory,
            tiles=os.listdir('tilecloud_chain/tests/tilegeneration/hooks'),
            expected="""==== Sync geodata ====
"""
        )

    @attr(none=True)
    @attr(multihost=True)
    def test_none(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--disable-geodata --disable-code --disable-database --disable-fillqueue --disable-tilesgen '
            '--host localhost',
            main_func=amazon.main,
            expected='')

    @attr(code=True)
    @attr(multihost=True)
    def test_code(self):
        if os.path.exists('/tmp/tests/test.conf'):
            os.remove('/tmp/tests/test.conf')
        if os.path.exists('/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/post-restore-code'):
            os.remove(
                '/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/'
                'post-restore-code'
            )

        out, err = self.run_cmd(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--disable-geodata --disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            main_func=amazon.main)
        self.assertEquals(out, '==== Sync and build code ====\n')
        self.assertEquals(err, '')
        f = open('/tmp/tests/test/tilecloud_chain/tests/tilegeneration/hooks/post-restore-database', 'r')
        self.assert_result_equals(f.read(), "echo SUCCESS\n")
        f = open('/tmp/tests/test.conf', 'r')
        self.assert_result_equals(f.read(), 'test file\n')

        os.remove('/tmp/tests/test.conf')
        try:
            shutil.rmtree('/tmp/tests/test')
        except:
            pass

    @attr(database=True)
    @attr(multihost=True)
    def test_database(self):
        out, err = self.run_cmd(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--disable-geodata --disable-code --disable-fillqueue --disable-tilesgen --host localhost',
            main_func=amazon.main)
        self.assertEquals(out, '==== Deploy database ====\n')
        self.assertEquals(err, '')
        self.assert_result_equals(Popen([
            'sudo', '-u', 'postgres', 'psql', '-d', 'tests-deploy', '-c', 'SELECT * FROM test'
        ], stdout=PIPE).communicate()[0], """   name
-----------
 referance
(1 row)

""")

    @attr(time_multihost=True)
    @attr(multihost=True)
    def test_time_multihost(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--time 2 -l polygon --host localhost --disable-geodata --disable-database --cache local',
            main_func=amazon.main,
            expected="""==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Then mean generated tile size: 0.826 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.826
""", regex=True)

        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '--time 1 -l polygon --host localhost --disable-geodata --disable-database '
            '--bbox 598000 198000 600000 200000 --zoom 4 --test 3',
            main_func=amazon.main,
            expected="""==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Then mean generated tile size: 1.144 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 1.144
""", regex=True)

    @attr(time_near=True)
    @attr(multihost=True)
    def test_time_near(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '-l point --time 50 --near 550000 180000 --zoom 3 --host localhost '
            '--disable-geodata --disable-database',
            main_func=amazon.main,
            expected="""==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Then mean generated tile size: 0.326 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.326
""", regex=True)

    @attr(time_no_geom=True)
    @attr(multihost=True)
    def test_time_no_geom(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_amazon -c tilecloud_chain/tests/tilegeneration/test.yaml '
            '-l point --time 1 --no-geom --bbox 550000 180000 555000 185000 --zoom 3 --host localhost '
            '--disable-geodata --disable-database',
            main_func=amazon.main,
            expected="""==== Sync and build code ====
==== Time results ====
A tile is generated in: [0-9\.]* \[ms\]
Then mean generated tile size: 0.326 \[kb\]
config:
    cost:
        tileonly_generation_time: [0-9\.]*
        tile_generation_time: [0-9\.]*
        metatile_generation_time: 0
        tile_size: 0.326
""", regex=True)

    @attr(near=True)
    @attr(multihost=True)
    def test_near(self):
        class Opt:
            zoom = '3'
            test = 196
            near = [600000.0, 200000.0]
            quiet = False
            verbose = False
            debug = False
            time = None
        gene = TileGeneration('tilecloud_chain/tests/tilegeneration/test.yaml', Opt(), 'point')
        self.assertEquals(gene.geoms[3].bounds, (583840.0, 173360.0, 624800.0, 214320.0))
