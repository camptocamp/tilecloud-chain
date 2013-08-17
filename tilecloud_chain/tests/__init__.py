# -*- coding: utf-8 -*-

import logging
import sys
import os
import re
import shutil
from cStringIO import StringIO
from unittest2 import TestCase

log = logging.getLogger("tests")


class CompareCase(TestCase):

    def assert_result_equals(self, result, expected, regex=False):
        expected = expected.split('\n')
        result = unicode(result.decode('utf-8'))
        result = re.sub(u'\n[^\n]*\r', u'\n', result)
        result = re.sub(u'^[^\n]*\r', u'', result)
        result = result.split('\n')
        for n, test in enumerate(zip(expected, result)):
            if test[0] != 'PASS...':
                try:
                    if regex:
                        self.assertRegexpMatches(test[1].strip(), '^%s$' % test[0].strip())
                    else:
                        self.assertEquals(test[0].strip(), test[1].strip())
                except AssertionError as e:
                    for i in range(max(0, n - 10), min(len(result), n + 11)):
                        if i == n:
                            log.info("> %i %s" % (i, result[i]))
                        else:
                            log.info("  %i %s" % (i, result[i]))
                    raise e
        self.assertEquals(len(expected), len(result))

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
        self.assert_result_equals(result=out, **kargs)

    def assert_cmd_exit_equals(self, cmd, main_func, expected):
        sys.argv = re.sub(' +', ' ', cmd).split(' ')
        try:
            main_func()
            assert("exit() not called.")
        except SystemExit as e:
            self.assertEquals(e.message, expected)

    def assert_main_equals(self, cmd, main_func, expected=None, **kargs):
        if expected:
            for expect in expected:
                if os.path.exists(expect[0]):
                    os.remove(expect[0])
        if type(cmd) == list:
            sys.argv = cmd
        else:
            sys.argv = re.sub(' +', ' ', cmd).split(' ')
        try:
            main_func()
        except SystemExit:
            pass
        if expected:
            for expect in expected:
                f = open(expect[0], 'r')
                self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_main_except_equals(self, cmd, main_func, expected, **kargs):
        sys.argv = cmd.split(' ')
        try:
            main_func()
            assert("exit() not called.")
        except:
            pass
        if expected:
            for expect in expected:
                f = open(expect[0], 'r')
                self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_yaml_equals(self, result, expected):
        import yaml
        expected = yaml.dump(yaml.load(expected), width=120)
        result = yaml.dump(yaml.load(result), width=120)
        self.assert_result_equals(result=result, expected=expected)

    def assert_cmd_yaml_equals(self, cmd, main_func, **kargs):
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        self.assert_main_equals(cmd, main_func, [])
        sys.stdout = old_stdout
        self.assert_yaml_equals(result=mystdout.getvalue(), **kargs)

    def assert_tiles_generated(self, directory, **kargs):
        if os.path.exists(directory):
            shutil.rmtree(directory)

        self.assert_tiles_generated_deleted(directory=directory, **kargs)

    def assert_tiles_generated_deleted(self, directory, tiles_pattern, tiles, expected='', **kargs):
        self.assert_cmd_equals(expected=expected, **kargs)
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
