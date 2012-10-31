# -*- coding: utf-8 -*-

import logging
import sys
import os
import shutil
from cStringIO import StringIO
from unittest2 import TestCase

log = logging.getLogger(__name__)


class CompareCase(TestCase):

    def assert_result_equals(self, content, value, regexp=False):
        content = unicode(content.decode('utf-8')).split('\n')
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

    def assert_cmd_equals(self, cmd, main_func, result, regexp=False, empty_err=False):
        out, err = self.run_cmd(cmd, main_func)
        if empty_err:
            self.assertEquals(err, '')  # pragma: no cover
        self.assert_result_equals(out, result, regexp)

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

    def assert_tiles_generated(self, cmd, main_func, directory, tiles_pattern, tiles):
        if os.path.exists(directory):
            shutil.rmtree(directory)

        self.assert_main_equals(cmd, main_func, [])
        count = 0
        for path, dirs, files in os.walk(directory):
            if len(files) != 0:
                log.info((path, files))
                count += len(files)
        self.assertEquals(count, len(tiles))
        for tile in tiles:
            log.info(directory + tiles_pattern % tile)
            self.assertTrue(os.path.exists(directory + tiles_pattern % tile))

    def assert_files_generated(self, cmd, main_func, directory, files):
        self.assert_tiles_generated(cmd, main_func, directory, '%s', files)
