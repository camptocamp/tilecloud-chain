import logging
import os
import re
import shutil
import sys
import traceback
from collections.abc import Callable
from io import StringIO
from logging import config
from typing import Any, Union
from unittest import TestCase

import yaml

DIFF = 200
log = logging.getLogger("tests")

config.dictConfig(
    {
        "version": 1,
        "loggers": {
            "default": {"level": "INFO"},
            "tilecloud": {"level": "DEBUG"},
            "tilecloud_chain": {"level": "DEBUG"},
        },
    }
)


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


class CompareCase(TestCase):
    def assert_result_equals(self, result: str, expected: str, regex: bool = False) -> None:
        expected = expected.split("\n")
        result = re.sub("\n[^\n]*\r", "\n", result)
        result = re.sub("^[^\n]*\r", "", result)
        result = result.split("\n")
        for n, test in enumerate(zip(expected, result, strict=False)):
            if test[0] != "PASS...":
                try:
                    if regex:
                        self.assertRegex(test[1].strip(), f"^{test[0].strip()}$")
                    else:
                        self.assertEqual(test[0].strip(), test[1].strip())
                except AssertionError as e:
                    for i in range(max(0, n - DIFF), min(len(result), n + DIFF + 1)):
                        if i == n:
                            print(f"> {i} {result[i]}")
                            log.info(f"> {i} {result[i]}")
                        else:
                            print(f"  {i} {result[i]}")
                            log.info(f"  {i} {result[i]}")
                    raise e
        self.assertEqual(len(expected), len(result), repr(result))

    def run_cmd(self, cmd: list[str] | str, main_func: Callable, get_error: bool = False) -> tuple[str, str]:
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        old_stderr = sys.stderr
        sys.stderr = mystderr = StringIO()
        try:
            self.assert_main_equals(cmd, main_func, [], get_error)
        except AssertionError:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            print(mystdout.getvalue())
            print(mystderr.getvalue())
            raise
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        log.info(mystdout.getvalue())
        log.info(mystderr.getvalue())
        return mystdout.getvalue(), mystderr.getvalue()

    def assert_cmd_equals(
        self, cmd: list[str] | str, main_func: Callable, empty_err: bool = False, **kargs: Any
    ) -> None:
        out, err = self.run_cmd(cmd, main_func)
        if empty_err:
            self.assertEqual(err, "")
        out = out.decode("utf-8") if isinstance(out, bytes) else str(out)
        self.assert_result_equals(result=out, **kargs)

    def assert_cmd_exit_equals(self, cmd: str, main_func: Callable) -> None:
        sys.argv = re.sub(" +", " ", cmd).split(" ")
        try:
            main_func()
            assert "exit() not called."
        except SystemExit:
            pass

    def assert_main_equals(
        self,
        cmd: list[str] | str,
        main_func: Callable,
        expected: list[list[str]] = None,
        get_error: bool = False,
        **kargs: Any,
    ) -> None:
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
            assert get_error is False
        except SystemExit as e:
            if get_error:
                assert e.code not in (None, 0), str(e)
            else:
                assert e.code in (None, 0), str(e)
        except AssertionError:
            raise
        except Exception:
            if not get_error:
                log.exception("Unexpected error")
            assert get_error is True, traceback.format_exc()

        if expected:
            for expect in expected:
                with open(expect[0]) as f:
                    self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_main_except_equals(
        self, cmd: str, main_func: Callable, expected: list[list[str]], get_error: bool = False, **kargs: Any
    ) -> None:
        sys.argv = cmd.split(" ")
        try:
            main_func()
            assert get_error is False
        except SystemExit as e:
            if get_error:
                assert e.code not in (None, 0), str(e)
            else:
                assert e.code in (None, 0), str(e)
        except AssertionError:
            raise
        except Exception:
            raise AssertionError(traceback.format_exc())

        if expected:
            for expect in expected:
                with open(expect[0]) as f:
                    self.assert_result_equals(f.read(), expect[1], **kargs)

    def assert_yaml_equals(self, result: str, expected: str) -> None:
        expected = yaml.dump(
            yaml.safe_load(expected), width=120, default_flow_style=False, Dumper=NoAliasDumper
        )
        result = yaml.dump(yaml.safe_load(result), width=120, default_flow_style=False, Dumper=NoAliasDumper)
        self.assert_result_equals(result=result, expected=expected)

    def assert_cmd_yaml_equals(self, cmd: str, main_func: Callable, **kargs: Any) -> None:
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        self.assert_main_equals(cmd, main_func, [])
        sys.stdout = old_stdout
        self.assert_yaml_equals(result=mystdout.getvalue(), **kargs)

    def assert_tiles_generated(self, directory: str, **kargs: Any) -> None:
        if os.path.exists(directory):
            shutil.rmtree(directory, ignore_errors=True)

        self.assert_tiles_generated_deleted(directory=directory, **kargs)

    def assert_tiles_generated_deleted(
        self, directory: str, tiles_pattern: str, tiles: Any, expected: str = "", **kargs: Any
    ) -> None:
        self.assert_cmd_equals(expected=expected, **kargs)
        count = 0
        for path, _dirs, files in os.walk(directory):
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


class MatchRegex:
    """Assert that a given string meets some expectations."""

    def __init__(self, regex) -> None:
        self._regex = re.compile(regex)

    def __eq__(self, other: str) -> bool:
        return self._regex.match(other) is not None

    def match(self, other: str) -> re.Match:
        return self._regex.match(other)

    def __repr__(self):
        return self._regex.pattern
