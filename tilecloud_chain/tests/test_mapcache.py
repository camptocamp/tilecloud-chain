import os
import threading
import time

from pyramid.testing import DummyRequest
import pytest

from tilecloud_chain import internal_mapcache, server
from tilecloud_chain.server import PyramidView
from tilecloud_chain.tests import CompareCase


class TestMapcache(CompareCase):
    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))

    @pytest.mark.skip(reason="Don't test mapcache")
    def test_internal(self):
        assert threading.active_count() == 1, ", ".join([str(t) for t in threading.enumerate()])

        self._do_test("test-internal-mapcache.yaml")

        internal_mapcache.stop(server.tilegeneration)
        time.sleep(0.1)
        assert threading.active_count() == 1, ", ".join([str(t) for t in threading.enumerate()])

    @pytest.mark.skip(reason="Don't test mapcache")
    def test_external(self):
        self._do_test("test-external-mapcache.yaml")

        assert threading.active_count() == 1, ", ".join([str(t) for t in threading.enumerate()])

    def _do_test(self, config):
        server.pyramid_server = None
        server.tilegeneration = None
        request = DummyRequest()
        request.registry.settings = {
            "tilegeneration_configfile": "tilegeneration/" + config,
        }
        request.params = {
            "Service": "WMTS",
            "Version": "1.0.0",
            "Request": "GetTile",
            "Format": "image/png",
            "Layer": "point",
            "Style": "default",
            "TileMatrixSet": "swissgrid_5",
            "TileMatrix": "4",
            "TileRow": "11",
            "TileCol": "14",
        }
        serve = PyramidView(request)
        serve()
        self.assertEqual(request.response.headers["Content-Type"], "image/png")
        self.assertEqual(request.response.headers["Cache-Control"], "max-age=28800")

        request.params["TileRow"] = "16"
        serve()
        self.assertEqual(request.response.headers["Content-Type"], "image/png")
        self.assertEqual(request.response.headers["Cache-Control"], "max-age=28800")

        # request on mapserver:
        # GET /mapserv?VERSION=1.1.1&REQUEST=GetMap&SERVICE=WMS&STYLES=&
        #     BBOX=429600.000000%2c328880.000000%2c441120.000000%2c340400.000000&WIDTH=2304&HEIGHT=2304&
        #     FORMAT=image%2fpng&SRS=EPSG%3a21781&LAYERS=point&TRANSPARENT=TRUE&DATE=2012&DIM_DATE=2012
