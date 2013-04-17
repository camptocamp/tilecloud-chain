# -*- coding: utf-8 -*-

import logging
import sys
import os
import shutil
from cStringIO import StringIO
from unittest2 import TestCase

log = logging.getLogger("tests")


class CompareCase(TestCase):

    def assert_result_equals(self, result, value, regexp=False):
        content = unicode(result.decode('utf-8')).split('\n')
        value = value.split('\n')
        for n, test in enumerate(zip(content, value)):
            if test[0] != 'PASS...':
                try:
                    if regexp:
                        self.assertRegexpMatches(test[0].strip(), test[1].strip())
                    else:
                        self.assertEquals(test[0].strip(), test[1].strip())
                except AssertionError as e:  # pragma: no cover
                    for i in range(max(0, n - 10), min(len(content), n + 11)):
                        if i == n:
                            log.info("> %i %s" % (i, content[i]))
                        else:
                            log.info("  %i %s" % (i, content[i]))
                    raise e
        self.assertEquals(len(value), len(content))

    def run_cmd(self, cmd, main_func):
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        old_stderr = sys.stderr
        sys.stderr = mystderr = StringIO()
        self.assert_main_equals(cmd, main_func, [])
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        log.info(mystdout.getvalue())
        log.info(mystderr.getvalue())
        return mystdout.getvalue(), mystderr.getvalue()

    def assert_cmd_equals(self, cmd, main_func, empty_err=False, **kargs):
        out, err = self.run_cmd(cmd, main_func)
        if empty_err:
            self.assertEquals(err, '')
        self.assert_result_equals(value=out, **kargs)

    def assert_cmd_exit_equals(self, cmd, main_func, result):
        sys.argv = cmd.split(' ')
        try:
            main_func()
            assert("exit() not called.")  # pragma: no cover
        except SystemExit as e:
            self.assertEquals(e.message, result)

    def assert_main_equals(self, cmd, main_func, results):
        sys.argv = cmd.split(' ')
        try:
            main_func()
        except SystemExit:
            pass
        if results:
            for result in results:
                f = open(result[0], 'r')
                self.assert_result_equals(f.read(), result[1])

    def assert_yaml_equals(self, content, value):
        import yaml
        content = yaml.dump(yaml.load(content), width=120)
        value = yaml.dump(yaml.load(value), width=120)
        self.assert_result_equals(content, value)

    def assert_cmd_yaml_equals(self, cmd, main_func, result):
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        self.assert_main_equals(cmd, main_func, [])
        sys.stdout = old_stdout
        self.assert_yaml_equals(mystdout.getvalue(), result)

    def assert_tiles_generated(self, directory, **kargs):
        if os.path.exists(directory):
            shutil.rmtree(directory)

        self.assert_tiles_generated_deleted(directory=directory, **kargs)

    def assert_tiles_generated_deleted(self, directory, tiles, **kargs):
        self.assert_cmd_equals(**kargs)
        count = 0
        for path, dirs, files in os.walk(directory):
            if len(files) != 0:
                log.info((path, files))
                count += len(files)

        self.assertEquals(count, len(tiles))
        for tile in tiles:
            log.info(directory + tiles_pattern % tile)
            self.assertTrue(os.path.exists(directory + tiles_pattern % tile))

    def assert_files_generated(self, **kargs):
        self.assert_tiles_generated(tiles_pattern='%s', **kargs)
