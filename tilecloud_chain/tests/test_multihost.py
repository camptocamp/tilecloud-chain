# -*- coding: utf-8 -*-

import os
import shutil
from subprocess import Popen, PIPE

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller


class TestController(CompareCase):

    def test_sync(self):
        directory = os.getenv("HOME") + "/tilecloud_chain/tests/hooks/"
        if os.path.exists(directory):
            shutil.rmtree(directory)  # pragma: no cover
        os.makedirs(directory)

        self.assert_files_generated(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/test.yaml --disable-code '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main,
            directory,
            os.listdir('tilecloud_chain/tests/hooks')
        )

    def test_none(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/test.yaml --disable-sync --disable-code '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main,
            '')

    def test_code(self):
        if os.path.exists('/tmp/tests/test.conf'):
            os.remove('/tmp/tests/test.conf')  # pragma: no cover
        if os.path.exists('/tmp/tests/test/tilecloud_chain/tests/hooks/post-restore-code'):
            os.remove('/tmp/tests/test/tilecloud_chain/tests/hooks/post-restore-code')  # pragma: no cover

        out, err = self.run_cmd(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/test.yaml --disable-sync '
            '--disable-database --disable-fillqueue --disable-tilesgen --host localhost',
            controller.main)
        self.assertEquals(out, '')
        self.assertEquals(err, '')
        f = open('/tmp/tests/test/tilecloud_chain/tests/hooks/post-restore-code', 'r')
        self.assert_result_equals(f.read(), """#!/bin/sh

PROJECT_NAME=$1
CODE_DIR=$2

cd $CODE_DIR

python -S bootstrap.py""")
        f = open('/tmp/tests/test.conf', 'r')
        self.assert_result_equals(f.read(), 'test file')

        os.remove('/tmp/tests/test.conf')
        try:
            shutil.rmtree('/tmp/tests/test')
        except:
            pass

    def test_database(self):
        out, err = self.run_cmd(
            './buildout/bin/generate_controller -c tilecloud_chain/tests/test.yaml --disable-sync --disable-code '
            '--disable-fillqueue --disable-tilesgen --host localhost',
            controller.main)
        self.assertEquals(out, '')
        self.assertEquals(err, '')
        self.assert_result_equals(Popen([
            'sudo', '-u', 'postgres', 'psql', '-d', 'tests-deploy', '-c', 'SELECT * FROM test'
        ], stdout=PIPE).communicate()[0], """   name
-----------
 referance
(1 row)""")
