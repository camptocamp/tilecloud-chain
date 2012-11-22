# -*- coding: utf-8 -*-

from tilecloud_chain.tests import CompareCase

from tilecloud_chain import controller


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
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l point',
            controller.main,
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
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l point --cost-algo count',
            controller.main,
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '1 meta tiles in zoom 0.',
                '1 meta tiles in zoom 1.',
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

    def test_cost_line(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l line',
            controller.main,
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '4 meta tiles in zoom 2.',
                '6 meta tiles in zoom 3.',
                '11 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '5',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '9',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '22',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '44',
                    'zoom': '3',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '93',
                    'zoom': '4',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '173',
                    'time': '0 0:00:05',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_line_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l line --cost-algo count',
            controller.main,
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '1 meta tiles in zoom 0.',
                '1 meta tiles in zoom 1.',
                '4 meta tiles in zoom 2.',
                '6 meta tiles in zoom 3.',
                '13 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '6',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '11',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '27',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '53',
                    'zoom': '3',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '110',
                    'zoom': '4',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '207',
                    'time': '0 0:00:06',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_polygon(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l polygon',
            controller.main,
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '2 meta tiles in zoom 0.',
                '3 meta tiles in zoom 1.',
                '7 meta tiles in zoom 2.',
                '17 meta tiles in zoom 3.',
                '49 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '12',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '34',
                    'zoom': '1',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '164',
                    'zoom': '2',
                    'time': '0 0:00:05',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '595',
                    'zoom': '3',
                    'time': '0 0:00:18',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2265',
                    'zoom': '4',
                    'time': '0 0:01:09',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3070',
                    'time': '0 0:01:34',
                    'cost': '0.05'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_polygon_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l polygon --cost-algo count',
            controller.main,
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '1 meta tiles in zoom 0.',
                '1 meta tiles in zoom 1.',
                '6 meta tiles in zoom 2.',
                '12 meta tiles in zoom 3.',
                '48 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '12',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '35',
                    'zoom': '1',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '165',
                    'zoom': '2',
                    'time': '0 0:00:05',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '609',
                    'zoom': '3',
                    'time': '0 0:00:18',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2240',
                    'zoom': '4',
                    'time': '0 0:01:08',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3061',
                    'time': '0 0:01:33',
                    'cost': '0.05'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_default(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml',
            controller.main,
            '\n'.join([
                '',
                '===== line =====',
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '4 meta tiles in zoom 2.',
                '6 meta tiles in zoom 3.',
                '11 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '5',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '9',
                    'zoom': '1',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '22',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '44',
                    'zoom': '3',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '93',
                    'zoom': '4',
                    'time': '0 0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '173',
                    'time': '0 0:00:05',
                    'cost': '0.00'
                },
                '',
                '===== polygon =====',
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '2 meta tiles in zoom 0.',
                '3 meta tiles in zoom 1.',
                '7 meta tiles in zoom 2.',
                '17 meta tiles in zoom 3.',
                '49 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '12',
                    'zoom': '0',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '34',
                    'zoom': '1',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '164',
                    'zoom': '2',
                    'time': '0 0:00:05',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '595',
                    'zoom': '3',
                    'time': '0 0:00:18',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2265',
                    'zoom': '4',
                    'time': '0 0:01:09',
                    's3': '0.02',
                    'ec2': '0.00',
                    'esb': '0.01',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3070',
                    'time': '0 0:01:34',
                    'cost': '0.05'
                },
                self.GLOBAL_SUMMARY % {
                    'tiles': '3243',
                    'time': '0 0:01:40',
                    'cost': '0.05'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '55.78',
                    'cloudfront': '54.78',
                    'esb': '11.00',
                }]))

    def test_cost_polygon2(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l polygon2',
            controller.main,
            '\n'.join([
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '912 meta tiles in zoom 0.',
                '21358 meta tiles in zoom 1.',
                '84725 meta tiles in zoom 2.',
                self.ZOOM_SUMMARY % {
                    'tiles': '54337',
                    'zoom': '0',
                    'time': '0 0:27:37',
                    's3': '0.54',
                    'ec2': '0.08',
                    'esb': '0.23',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '1347131',
                    'zoom': '1',
                    'time': '0 11:24:14',
                    's3': '13.47',
                    'ec2': '1.94',
                    'esb': '5.70',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '5382881',
                    'zoom': '2',
                    'time': '1 21:33:48',
                    's3': '53.83',
                    'ec2': '7.75',
                    'esb': '22.78',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '6784349',
                    'time': '2 9:25:40',
                    'cost': '106.32'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.02',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_nometa(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l all',
            controller.main,
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                self.ZOOM_SUMMARY % {'tiles': '2', 'zoom': '0', 'time': '0 0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00', 'sqs': '0.00'},
                self.ZOOM_SUMMARY % {'tiles': '4', 'zoom': '1', 'time': '0 0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00', 'sqs': '0.00'},
                self.ZOOM_SUMMARY % {'tiles': '10', 'zoom': '2', 'time': '0 0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00', 'sqs': '0.00'},
                self.ZOOM_SUMMARY % {'tiles': '26', 'zoom': '3', 'time': '0 0:00:01', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00', 'sqs': '0.00'},
                self.ZOOM_SUMMARY % {'tiles': '81', 'zoom': '4', 'time': '0 0:00:04', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00', 'sqs': '0.00'},
                self.LAYER_SUMMARY % {
                    'tiles': '123',
                    'time': '0 0:00:07',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_layer_bbox(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l all --cost-algo count',
            controller.main,
            '\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
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
                    'tiles': '9',
                    'zoom': '2',
                    'time': '0 0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '25',
                    'zoom': '3',
                    'time': '0 0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '81',
                    'zoom': '4',
                    'time': '0 0:00:04',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '119',
                    'time': '0 0:00:07',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    def test_cost_no_geom(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilegeneration/test.yaml -l point --no-geom',
            controller.main,
            '\n'.join([
                'Calculate zoom 4.',
                'Calculate zoom 3.',
                'Calculate zoom 2.',
                'Calculate zoom 1.',
                'Calculate zoom 0.',
                '',
                '9 meta tiles in zoom 0.',
                '25 meta tiles in zoom 1.',
                '116 meta tiles in zoom 2.',
                '414 meta tiles in zoom 3.',
                '1560 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '273',
                    'zoom': '0',
                    'time': '0 0:00:08',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '1014',
                    'zoom': '1',
                    'time': '0 0:00:31',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '6048',
                    'zoom': '2',
                    'time': '0 0:03:04',
                    's3': '0.06',
                    'ec2': '0.01',
                    'esb': '0.03',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '23814',
                    'zoom': '3',
                    'time': '0 0:12:06',
                    's3': '0.24',
                    'ec2': '0.03',
                    'esb': '0.10',
                    'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '94501',
                    'zoom': '4',
                    'time': '0 0:48:01',
                    's3': '0.95',
                    'ec2': '0.14',
                    'esb': '0.40',
                    'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '125650',
                    'time': '0 1:03:53',
                    'cost': '1.97'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'cloudfront': '31.89',
                    'esb': '11.00',
                }]))
