from nose.plugins.attrib import attr
import os
from testfixtures import log_capture
from tilecloud_chain import server
from tilecloud_chain.tests import CompareCase
from tilecloud_chain.server import PyramidView
from pyramid.testing import DummyRequest


class TestMapcache(CompareCase):
    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @attr(general=True, mapcache=True)
    @log_capture('tilecloud_chain', level=30)
    def test_internal(self, l):
        self._do_test("test-internal-mapcache.yaml")

    @attr(general=True, mapcache=True)
    @log_capture('tilecloud_chain', level=30)
    def test_external(self, l):
        self._do_test("test-external-mapcache.yaml")

    def _do_test(self, config):
        server.pyramid_server = None
        server.tilegeneration = None
        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/' + config,
        }
        request.params = {
            'Service': 'WMTS',
            'Version': '1.0.0',
            'Request': 'GetTile',
            'Format': 'image/png',
            'Layer': 'point',
            'Style': 'default',
            'TileMatrixSet': 'swissgrid_5',
            'TileMatrix': '4',
            'TileRow': '11',
            'TileCol': '14',
        }
        serve = PyramidView(request)
        serve()
        self.assertEqual(request.response.headers['Content-Type'], 'image/png')
        self.assertEqual(request.response.headers['Cache-Control'], 'max-age=28800')

        request.params['TileRow'] = '16'
        serve()
        self.assertEqual(request.response.headers['Content-Type'], 'image/png')
        self.assertEqual(request.response.headers['Cache-Control'], 'max-age=28800')
        # request on mapserver:
        # GET /mapserv?VERSION=1.1.1&REQUEST=GetMap&SERVICE=WMS&STYLES=&
        #     BBOX=429600.000000%2c328880.000000%2c441120.000000%2c340400.000000&WIDTH=2304&HEIGHT=2304&
        #     FORMAT=image%2fpng&SRS=EPSG%3a21781&LAYERS=point&TRANSPARENT=TRUE&DATE=2012&DIM_DATE=2012
