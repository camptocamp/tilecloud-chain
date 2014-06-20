# -*- coding: utf-8 -*-

import os

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase

from tilecloud_chain import cost


class TestCost(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(self):
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    ZOOM_SUMMARY = """
%(tiles)s tiles in zoom %(zoom)s.
Time to generate: %(time)s [d h:mm:ss]
S3 PUT: %(s3)s [$]
EC2 usage: %(ec2)s [$]
ESB usage: %(esb)s [$]"""
# SQS usage: %(sqs)s [$]"""

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
ESB storage: %(esb)s [$/month]
"""
# CloudFront: %(cloudfront)s [$/month]

    @attr(cost_point=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_point(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l point',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '2 meta tiles in zoom 2.',
                '2 meta tiles in zoom 3.',
                self.ZOOM_SUMMARY % {
                    'tiles': '6',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '6',
                    'zoom': '1',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '6',
                    'zoom': '2',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '6',
                    'zoom': '3',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.LAYER_SUMMARY % {
                    'tiles': '24',
                    'time': '0:00:00',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_point_count=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_point_count(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l point --cost-algo count',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                '',
                '1 meta tiles in zoom 0.',
                '1 meta tiles in zoom 1.',
                '6 meta tiles in zoom 2.',
                '2 meta tiles in zoom 3.',
                self.ZOOM_SUMMARY % {
                    'tiles': '64',
                    'zoom': '0',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '64',
                    'zoom': '1',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '339',
                    'zoom': '2',
                    'time': '0:00:10',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '112',
                    'zoom': '3',
                    'time': '0:00:03',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.LAYER_SUMMARY % {
                    'tiles': '579',
                    'time': '0:00:17',
                    'cost': '0.01'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_line=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_line(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l line',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '4 meta tiles in zoom 2.',
                '8 meta tiles in zoom 3.',
                '14 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '11',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '19',
                    'zoom': '1',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '43',
                    'zoom': '2',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '84',
                    'zoom': '3',
                    'time': '0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '164',
                    'zoom': '4',
                    'time': '0:00:05',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '321',
                    'time': '0:00:10',
                    'cost': '0.01'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_line_count=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_line_count(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l line --cost-algo count',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '1 meta tiles in zoom 0.',
                '1 meta tiles in zoom 1.',
                '6 meta tiles in zoom 2.',
                '10 meta tiles in zoom 3.',
                '21 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '64',
                    'zoom': '0',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '64',
                    'zoom': '1',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '383',
                    'zoom': '2',
                    'time': '0:00:11',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '493',
                    'zoom': '3',
                    'time': '0:00:15',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '600',
                    'zoom': '4',
                    'time': '0:00:18',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '1604',
                    'time': '0:00:49',
                    'cost': '0.03'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_polygon=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_polygon(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l polygon',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '13',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '35',
                    'zoom': '1',
                    'time': '0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '167',
                    'zoom': '2',
                    'time': '0:00:10',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '601',
                    'zoom': '3',
                    'time': '0:00:36',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.01',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2268',
                    'zoom': '4',
                    'time': '0:02:16',
                    's3': '0.02',
                    'ec2': '0.01',
                    'esb': '0.02',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3084',
                    'time': '0:03:05',
                    'cost': '0.07'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_polygon_count=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_polygon_count(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml '
                '-l polygon --cost-algo count',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '12',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '35',
                    'zoom': '1',
                    'time': '0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '165',
                    'zoom': '2',
                    'time': '0:00:09',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '609',
                    'zoom': '3',
                    'time': '0:00:36',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.01',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2240',
                    'zoom': '4',
                    'time': '0:02:14',
                    's3': '0.02',
                    'ec2': '0.01',
                    'esb': '0.02',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3061',
                    'time': '0:03:03',
                    'cost': '0.06'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_default=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_default(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml',
            main_func=cost.main,
            expected='\n'.join([
                '',
                '===== line =====',
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                '2 meta tiles in zoom 0.',
                '2 meta tiles in zoom 1.',
                '4 meta tiles in zoom 2.',
                '8 meta tiles in zoom 3.',
                '14 meta tiles in zoom 4.',
                self.ZOOM_SUMMARY % {
                    'tiles': '11',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '19',
                    'zoom': '1',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '43',
                    'zoom': '2',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '84',
                    'zoom': '3',
                    'time': '0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '164',
                    'zoom': '4',
                    'time': '0:00:05',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '321',
                    'time': '0:00:10',
                    'cost': '0.01'
                },
                '',
                '===== polygon =====',
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '13',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '35',
                    'zoom': '1',
                    'time': '0:00:02',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '167',
                    'zoom': '2',
                    'time': '0:00:10',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '601',
                    'zoom': '3',
                    'time': '0:00:36',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.01',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2268',
                    'zoom': '4',
                    'time': '0:02:16',
                    's3': '0.02',
                    'ec2': '0.01',
                    'esb': '0.02',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '3084',
                    'time': '0:03:05',
                    'cost': '0.07'
                },
                self.GLOBAL_SUMMARY % {
                    'tiles': '3405',
                    'time': '0:03:15',
                    'cost': '0.07'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '55.78',
                    # 'cloudfront': '54.78',
                    'esb': '11.00',
                }]))

    @attr(cost_polygon2=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_polygon2(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l polygon2',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                '',
                '925 meta tiles in zoom 0.',
                '21310 meta tiles in zoom 1.',
                '84341 meta tiles in zoom 2.',
                self.ZOOM_SUMMARY % {
                    'tiles': '54534',
                    'zoom': '0',
                    'time': '0:27:43',
                    's3': '0.55',
                    'ec2': '0.08',
                    'esb': '0.23',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '1340772',
                    'zoom': '1',
                    'time': '11:21:02',
                    's3': '13.41',
                    'ec2': '1.93',
                    'esb': '5.68',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '5351829',
                    'zoom': '2',
                    'time': '1 21:18:05',
                    's3': '53.52',
                    'ec2': '7.70',
                    'esb': '22.65',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '6747135',
                    'time': '2 9:06:51',
                    'cost': '105.74'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.02',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_nometa=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_nometa(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l all',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '2', 'zoom': '0', 'time': '0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '4', 'zoom': '1', 'time': '0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '10', 'zoom': '2', 'time': '0:00:00', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '27', 'zoom': '3', 'time': '0:00:01', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '84', 'zoom': '4', 'time': '0:00:05', 's3': '0.00',
                    'ec2': '0.00', 'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '127',
                    'time': '0:00:07',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_layer_bbox=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_layer_bbox(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l all --cost-algo count',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '0',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '2',
                    'zoom': '1',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '9',
                    'zoom': '2',
                    'time': '0:00:00',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '25',
                    'zoom': '3',
                    'time': '0:00:01',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.ZOOM_SUMMARY % {
                    'tiles': '81',
                    'zoom': '4',
                    'time': '0:00:04',
                    'time': '0:00:04',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                self.LAYER_SUMMARY % {
                    'tiles': '119',
                    'time': '0:00:07',
                    'cost': '0.00'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_no_geom=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_no_geom(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test-fix.yaml -l point --no-geom',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                '',
                '11 meta tiles in zoom 0.',
                '28 meta tiles in zoom 1.',
                '123 meta tiles in zoom 2.',
                '427 meta tiles in zoom 3.',
                self.ZOOM_SUMMARY % {
                    'tiles': '312',
                    'zoom': '0',
                    'time': '0:00:09',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '1090',
                    'zoom': '1',
                    'time': '0:00:33',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.00',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '6237',
                    'zoom': '2',
                    'time': '0:03:10',
                    's3': '0.06',
                    'ec2': '0.01',
                    'esb': '0.03',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '24190',
                    'zoom': '3',
                    'time': '0:12:18',
                    's3': '0.24',
                    'ec2': '0.03',
                    'esb': '0.10',
                    # 'sqs': '0.00'
                },
                'SQS usage: 0.00 [$]',
                self.LAYER_SUMMARY % {
                    'tiles': '31829',
                    'time': '0:16:12',
                    'cost': '0.50'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    # 'cloudfront': '31.89',
                    'esb': '11.00',
                }]))

    @attr(cost_sqs_nometa=True)
    @attr(cost=True)
    @attr(general=True)
    def test_cost_sqs_nometa(self):
        self.assert_cmd_equals(
            cmd='./buildout/bin/generate_cost -c tilegeneration/test.yaml -l point_hash_no_meta',
            main_func=cost.main,
            expected='\n'.join([
                'Calculate zoom 0.',
                'Calculate zoom 1.',
                'Calculate zoom 2.',
                'Calculate zoom 3.',
                'Calculate zoom 4.',
                '',
                self.ZOOM_SUMMARY % {
                    'tiles': '279',
                    'zoom': '0',
                    'time': '0:00:16',
                    's3': '0.00',
                    'ec2': '0.00',
                    'esb': '0.00',
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '1026',
                    'zoom': '1',
                    'time': '0:01:01',
                    's3': '0.01',
                    'ec2': '0.00',
                    'esb': '0.01',
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '6079',
                    'zoom': '2',
                    'time': '0:06:04',
                    's3': '0.06',
                    'ec2': '0.02',
                    'esb': '0.05',
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '23876',
                    'zoom': '3',
                    'time': '0:23:52',
                    's3': '0.24',
                    'ec2': '0.07',
                    'esb': '0.20',
                },
                'SQS usage: 0.00 [$]',
                self.ZOOM_SUMMARY % {
                    'tiles': '94626',
                    'zoom': '4',
                    'time': '1:34:37',
                    's3': '0.95',
                    'ec2': '0.27',
                    'esb': '0.79',
                },
                'SQS usage: 0.00 [$]',
                self.LAYER_SUMMARY % {
                    'tiles': '125886',
                    'time': '2:05:53',
                    'cost': '2.67'
                },
                self.FINAL_SUMMARY % {
                    'storage': '0.00',
                    'get': '32.89',
                    'esb': '11.00',
                }]))
