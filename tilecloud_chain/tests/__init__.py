# -*- coding: utf-8 -*-

import logging
import sys
from cStringIO import StringIO
from unittest import TestCase

log = logging.getLogger(__name__)


class CompareCase(TestCase):

    def assert_result_equals(self, content, value):
        log.info(content)
        for n, test in enumerate(zip(value.split('\n'),
                unicode(content.decode('utf-8')).split('\n'))):
            if test[0] != 'PASS...':
                try:
                    self.assertEquals(test[0].strip(), test[1].strip())
                except AssertionError as e:
                    log.info(n)
                    raise e

    def assert_cmd_equals(self, cmd, main_func, result):
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        self.assert_main_equals(cmd, main_func, [])
        sys.stdout = old_stdout
        self.assert_result_equals(mystdout.getvalue(), result)

    def assert_main_equals(self, cmd, main_func, results):
        sys.argv = cmd.split(' ')
        try:
            main_func()
            self.fail("Main function don't call exit.")  # pragma: no cover
        except SystemExit:
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
