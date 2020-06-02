# -*- coding: utf-8 -*-

import logging
import os
import re
import shutil
import sys
import traceback
from io import StringIO
from logging import config

from unittest2 import TestCase

DIFF = 200
log = logging.getLogger("tests")

config.dictConfig({"version": 1, "loggers": {"pykwalify": {"level": "WARN"}}})


class CompareCase(TestCase):
    def assert_result_equals(self, result, expected, regex=False):
        expected = expected.split("\n")
        result = re.sub("\n[^\n]*\r", "\n", result)
        result = re.sub("^[^\n]*\r", "", result)
        result = result.split("\n")
        for n, test in enumerate(zip(expected, result)):
            if test[0] != "PASS...":
                try:
                    if regex:
                        self.assertRegexpMatches(test[1].strip(), "^{}$".format(test[0].strip()))
                    else:
                        self.assertEqual(test[0].strip(), test[1].strip())
                except AssertionError as e:
                    for i in range(max(0, n - DIFF), min(len(result), n + DIFF + 1)):
                        if i == n:
                            print("> {} {}".format(i, result[i]))
                            log.info("> {} {}".format(i, result[i]))
                        else:
                            print("  {} {}".format(i, result[i]))
                            log.info("  {} {}".format(i, result[i]))
                    raise e
        self.assertEqual(len(expected), len(result), repr(result))

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
            self.assertEqual(err, "")
        if isinstance(out, bytes):
            out = out.decode("utf-8")
        else:
            out = str(out)
        self.assert_result_equals(result=out, **kargs)

    def assert_cmd_exit_equals(self, cmd, main_func, expected):
        sys.argv = re.sub(" +", " ", cmd).split(" ")
        try:
            main_func()
            assert "exit() not called."
        except SystemExit as e:
            self.assertEqual(str(e), expected)

    def assert_main_equals(self, cmd, main_func, expected=None, **kargs):
        if expected:
            for expect in expected:
                if os.path.exists(expect[0]):
                    os.remove(expect[0])
        if type(cmd) == list:
            sys.argv = cmd
        else:
            sys.argv = re.sub(" +", " ", cmd).split(" ")
        try:
            main_func()
        # except SystemExit as e:
        #     assert e.code in (None, 0)
        except SystemExit:
            pass
        except Exception:
            assert False, traceback.format_exc()

        if expected:
            for expect in expected:
                with open(expect[0], "r") as f:
                    self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_main_except_equals(self, cmd, main_func, expected, **kargs):
        sys.argv = cmd.split(" ")
        try:
            main_func()
            assert "exit() not called."
        except Exception:
            pass
        if expected:
            for expect in expected:
                with open(expect[0], "r") as f:
                    self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_yaml_equals(self, result, expected):
        import yaml

        expected = yaml.dump(yaml.safe_load(expected), width=120)
        result = yaml.dump(yaml.safe_load(result), width=120)
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

    def assert_tiles_generated_deleted(self, directory, tiles_pattern, tiles, expected="", **kargs):
        self.assert_cmd_equals(expected=expected, **kargs)
        count = 0
        for path, dirs, files in os.walk(directory):
            if len(files) != 0:
                log.info((path, files))
                print((path, files))
                count += len(files)

        self.assertEqual(count, len(tiles))
        for tile in tiles:
            log.info(directory + tiles_pattern % tile)
            print(directory + tiles_pattern % tile)
            self.assertTrue(os.path.exists(directory + tiles_pattern % tile))

    def assert_files_generated(self, **kargs):
        self.assert_tiles_generated(tiles_pattern="%s", **kargs)
