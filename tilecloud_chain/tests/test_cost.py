# -*- coding: utf-8 -*-

from tilecloud_chain.tests import CompareCase


class TestCost(CompareCase):

    ZOOM_SUMMARY = """
%(tiles)s tiles in zoom %(zoom)s.
Time to generate: %(time)s [d h:mm:ss]
S3 PUT: %(s3)s [$]
EC2 usage: %(ec2)s [$]
ESB usage: %(esb)s [$]
SQS usage: %(sqs)s [$]"""

    LAYER_SUMMARY = """
Number of tiles: %(tiles)s
Generation time: %(time)s [d h:mm:ss]
Generation cost: %(cost)s [$]"""

    GLOBAL_SUMMARY = """
===== GLOBAL =====
Total number of tiles: %(tiles)s
Total generation time: %(time)s [d h:mm:ss]
Total generation cost: %(cost)s [$]"""

    FINAL_SUMMARY = """
S3 Storage: %(storage)s [$/month]
S3 get: %(get)s [$/month]
CloudFront: %(cloudfront)s [$/month]
ESB storage: %(esb)s [$/month]"""

    def test_cost_point(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l point',
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '2 meta tiles in zoom 2.',
                '2 meta tiles in zoom 3.',
                '2 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '3',
                    'zoom': '3',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '3',
                    'zoom': '4',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '12',
                    'time': '0 0:00:00',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_point_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l point --cost-algo count',
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '2 meta tiles in zoom 2.',
                '2 meta tiles in zoom 3.',
                '2 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '3',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '4',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '10',
                    'time': '0 0:00:00',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_line(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l line',
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '3 meta tiles in zoom 0.',
                '4 meta tiles in zoom 1.',
                '9 meta tiles in zoom 2.',
                '16 meta tiles in zoom 3.',
                '32 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '13',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '25',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '63',
                    'zoom': '2',
                    'time': '0 0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '129',
                    'zoom': '3',
                    'time': '0 0:00:04',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '272',
                    'zoom': '4',
                    'time': '0 0:00:09',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '502',
                    'time': '0 0:00:16',
                    'cost': '0.01'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_line_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l line --cost-algo count',
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '2 meta tiles in zoom 0.',
                '3 meta tiles in zoom 1.',
                '8 meta tiles in zoom 2.',
                '15 meta tiles in zoom 3.',
                '30 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '13',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '25',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '60',
                    'zoom': '2',
                    'time': '0 0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '119',
                    'zoom': '3',
                    'time': '0 0:00:04',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '235',
                    'zoom': '4',
                    'time': '0 0:00:07',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '452',
                    'time': '0 0:00:15',
                    'cost': '0.01'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_polygon(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l polygon',
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '3 meta tiles in zoom 0.',
                '6 meta tiles in zoom 1.',
                '17 meta tiles in zoom 2.',
                '49 meta tiles in zoom 3.',
                '156 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '34',
                    'zoom': '0',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '106',
                    'zoom': '1',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '551',
                    'zoom': '2',
                    'time': '0 0:00:17',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2058',
                    'zoom': '3',
                    'time': '0 0:01:03',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '7949',
                    'zoom': '4',
                    'time': '0 0:04:03',
                    's3': '0.08',
                    'ec2': '0.01',
                    'esb': '0.03',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '10698',
                    'time': '0 0:05:27',
                    'cost': '0.17'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_polygon_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l polygon --cost-algo count',
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '2 meta tiles in zoom 0.',
                '3 meta tiles in zoom 1.',
                '14 meta tiles in zoom 2.',
                '39 meta tiles in zoom 3.',
                '150 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '33',
                    'zoom': '0',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '105',
                    'zoom': '1',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '550',
                    'zoom': '2',
                    'time': '0 0:00:16',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2079',
                    'zoom': '3',
                    'time': '0 0:01:03',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '7840',
                    'zoom': '4',
                    'time': '0 0:03:59',
                    's3': '0.08',
                    'ec2': '0.01',
                    'esb': '0.03',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '10607',
                    'time': '0 0:05:24',
                    'cost': '0.17'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_default(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml',
            '\n'.join([
                '',
                '===== line =====',
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '3 meta tiles in zoom 0.',
                '4 meta tiles in zoom 1.',
                '9 meta tiles in zoom 2.',
                '16 meta tiles in zoom 3.',
                '32 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '13',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '25',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '63',
                    'zoom': '2',
                    'time': '0 0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '129',
                    'zoom': '3',
                    'time': '0 0:00:04',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '272',
                    'zoom': '4',
                    'time': '0 0:00:09',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '502',
                    'time': '0 0:00:16',
                    'cost': '0.01'
                },                '',
                '===== polygon =====',
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '3 meta tiles in zoom 0.',
                '6 meta tiles in zoom 1.',
                '17 meta tiles in zoom 2.',
                '49 meta tiles in zoom 3.',
                '156 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '34',
                    'zoom': '0',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '106',
                    'zoom': '1',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '551',
                    'zoom': '2',
                    'time': '0 0:00:17',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2058',
                    'zoom': '3',
                    'time': '0 0:01:03',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '7949',
                    'zoom': '4',
                    'time': '0 0:04:03',
                    's3': '0.08',
                    'ec2': '0.01',
                    'esb': '0.03',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '10698',
                    'time': '0 0:05:27',
                    'cost': '0.17'
                },
                self.GLOBAL_SUMMARY % {
                    'tiles': '11200',
                    'time': '0 0:05:44',
                    'cost': '0.18'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '55.78',
                    'cloudfront': '54.78',
                    'esb': '11.00',
                }]))

    def test_cost_polygon2(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l polygon2',
            '\n'.join([
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '3172 meta tiles in zoom 0.',
                '75745 meta tiles in zoom 1.',
                '301215 meta tiles in zoom 2.',
                self.ZOOM_SUMMARY % {
                    'tiles': '193060',
                    'zoom': '0',
                    'time': '0 1:38:06',
                    's3': '1.93',
                    'ec2': '0.28',
                    'esb': '0.82',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '4798310',
                    'zoom': '1',
                    'time': '1 16:37:01',
                    's3': '47.98',
                    'ec2': '6.90',
                    'esb': '20.31',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '19179160',
                    'zoom': '2',
                    'time': '6 18:20:11',
                    's3': '191.79',
                    'ec2': '27.60',
                    'esb': '81.17',
                    'sqs': '0.01'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '24170530',
                    'time': '8 12:35:19',
                    'cost': '378.79'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.06',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))
