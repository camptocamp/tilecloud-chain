# -*- coding: utf-8 -*-

import logging
from subprocess import Popen, PIPE
from unittest import TestCase

log = logging.getLogger(__name__)


class CompareCase(TestCase):

    def assert_result_equals(self, content, value):
        log.info(content)
# log.info(value)
        for test in zip(value.split('\n'),
                unicode(content.decode('utf-8')).split('\n')):
# log.info(test[0])
# log.info(test[1])
            if test[0] != 'PASS...':
                self.assertEquals(test[0].strip(), test[1].strip())

    def assert_cmd_equals(self, cmd, result):
        self.assert_result_equals(Popen(cmd.split(' '), stdout=PIPE).communicate()[0], result)
