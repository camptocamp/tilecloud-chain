# -*- coding: utf-8 -*-

from tilecloud_chain.tests import CompareCase


class TestController(CompareCase):

    def test_cost_point(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l point',
            """Calculate zoom 3.
Calculate zoom 2.
Calculate zoom 1.
Calculate zoom 0.

1 meta tiles in zoom 0.
1 meta tiles in zoom 1.
2 meta tiles in zoom 2.
2 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 8
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_point_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l point --cost-algo count',
            """Calculate zoom 0.
Calculate zoom 1.
Calculate zoom 2.
Calculate zoom 3.

2 meta tiles in zoom 0.
2 meta tiles in zoom 1.
2 meta tiles in zoom 2.
2 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 8
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_line(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l line',
            """Calculate zoom 3.
Calculate zoom 2.
Calculate zoom 1.
Calculate zoom 0.

1 meta tiles in zoom 0.
1 meta tiles in zoom 1.
2 meta tiles in zoom 2.
3 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

4 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

7 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

13 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 26
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_line_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l line --cost-algo count',
            """Calculate zoom 0.
Calculate zoom 1.
Calculate zoom 2.
Calculate zoom 3.

2 meta tiles in zoom 0.
2 meta tiles in zoom 1.
2 meta tiles in zoom 2.
2 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

3 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

7 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

13 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 25
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_polygon(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l polygon',
            """Calculate zoom 3.
Calculate zoom 2.
Calculate zoom 1.
Calculate zoom 0.

1 meta tiles in zoom 0.
1 meta tiles in zoom 1.
2 meta tiles in zoom 2.
3 meta tiles in zoom 3.

3 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

5 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

13 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

34 tiles in zoom 3.
Time to generate: 0 0:00:01 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 55
Generation time: 0 0:00:01 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_polygon_count(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml -l polygon --cost-algo count',
            """Calculate zoom 0.
Calculate zoom 1.
Calculate zoom 2.
Calculate zoom 3.

2 meta tiles in zoom 0.
2 meta tiles in zoom 1.
2 meta tiles in zoom 2.
2 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

3 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

12 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

33 tiles in zoom 3.
Time to generate: 0 0:00:01 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 50
Generation time: 0 0:00:01 [d h:mm:ss]
Generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 32.89 [$/month]
CloudFront: 31.89 [$/month]
ESB storage: 11.00 [$/month]""")

    def test_cost_default(self):
        self.assert_cmd_equals(
            './buildout/bin/generate_controller --cost -c tilecloud_chain/tests/test.yaml',
            """
===== point =====
Calculate zoom 3.
Calculate zoom 2.
Calculate zoom 1.
Calculate zoom 0.

1 meta tiles in zoom 0.
1 meta tiles in zoom 1.
2 meta tiles in zoom 2.
2 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

2 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 8
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

===== line =====
Calculate zoom 3.
Calculate zoom 2.
Calculate zoom 1.
Calculate zoom 0.

1 meta tiles in zoom 0.
1 meta tiles in zoom 1.
2 meta tiles in zoom 2.
3 meta tiles in zoom 3.

2 tiles in zoom 0.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

4 tiles in zoom 1.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

7 tiles in zoom 2.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

13 tiles in zoom 3.
Time to generate: 0 0:00:00 [d h:mm:ss]
S3 PUT: 0.00 [$]
EC2 usage: 0.00 [$]
ESB usage: 0.00 [$]
SQS usage: 0.00 [$]

Number of tiles: 26
Generation time: 0 0:00:00 [d h:mm:ss]
Generation cost: 0.00 [$]

===== GLOBAL =====
Total number of tiles: 34
Total generation time: 0 0:00:01 [d h:mm:ss]
Total generation cost: 0.00 [$]

S3 Storage: 0.00 [$/month]
S3 get: 55.78 [$/month]
CloudFront: 54.78 [$/month]
ESB storage: 11.00 [$/month]""")
