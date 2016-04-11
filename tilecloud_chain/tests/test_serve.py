# -*- coding: utf-8 -*-

import os
import shutil

from six import PY3
from testfixtures import log_capture
from nose.plugins.attrib import attr
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPNoContent, HTTPBadRequest

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import generate, controller
from tilecloud_chain.server import PyramidView, app_factory


CAPABILITIES = """<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0" xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:gml="http://www.opengis.net/gml"
              xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification> </ows:ServiceIdentification>
  <ows:ServiceProvider> </ows:ServiceProvider>
  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>KVP</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
                <ows:Value>KVP</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>
  <!-- <ServiceMetadataURL xlink:href="" /> -->
  <Contents>

    <Layer>
      <ows:Title>point_hash</ows:Title>
      <ows:Identifier>point_hash</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <InfoFormat></InfoFormat>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point_hash/default/{DATE}/""" \
    """{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.42857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.142857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

  </Contents>
</Capabilities>"""


class TestServe(CompareCase):

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @attr(serve_kvp=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_serve_kvp(self, l):
        self.assert_tiles_generated(
            cmd='.build/venv/bin/generate_tiles -d -c tilegeneration/test-nosns.yaml '
                '-l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5/1/11/14.png'),
                ('point_hash/default/2012/swissgrid_5/1/15/8.png'),
            ],
            regex=True,
            expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='.build/venv/bin/generate_controller --capabilities -c tilegeneration/test-nosns.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5/1/11/14.png'),
                ('point_hash/default/2012/swissgrid_5/1/15/8.png'),
            ],
        )

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-nosns.yaml',
        }
        request.params = {
            'Service': 'WMTS',
            'Version': '1.0.0',
            'Request': 'GetTile',
            'Format': 'image/png',
            'Layer': 'point_hash',
            'Style': 'default',
            'TileMatrixSet': 'swissgrid_5',
            'TileMatrix': '1',
            'TileRow': '11',
            'TileCol': '14',
        }
        serve = PyramidView(request)
        serve()
        self.assertEqual(request.response.headers['Content-Type'], 'image/png')
        self.assertEqual(request.response.headers['Cache-Control'], 'max-age=28800')

        request.params['TileRow'] = '12'
        self.assertRaises(HTTPNoContent, serve)

        request.params['TileRow'] = '11'
        request.params['Service'] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Service'] = 'WMTS'
        request.params['Request'] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Request'] = 'GetTile'
        request.params['Version'] = '0.9'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Version'] = '1.0.0'
        request.params['Format'] = 'image/jpeg'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Format'] = 'image/png'
        request.params['Layer'] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Layer'] = 'point_hash'
        request.params['Style'] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['Style'] = 'default'
        request.params['TileMatrixSet'] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.params['TileMatrixSet'] = 'swissgrid_5'
        del request.params['Service']
        self.assertRaises(HTTPBadRequest, serve)

        request.params = {
            'Service': 'WMTS',
            'Version': '1.0.0',
            'Request': 'GetCapabilities',
        }
        PyramidView(request)()
        self.assertEqual(request.response.headers['Content-Type'], 'application/xml')
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            regex=True,
            expected=u"""<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0" xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
              xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:gml="http://www.opengis.net/gml"
              xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification> </ows:ServiceIdentification>
  <ows:ServiceProvider> </ows:ServiceProvider>
  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>KVP</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://wmts1/tiles/wmts/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
                <ows:Value>KVP</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>
  <!-- <ServiceMetadataURL xlink:href="" /> -->
  <Contents>

    <Layer>
      <ows:Title>all</ows:Title>
      <ows:Identifier>all</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/all/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>line</ows:Title>
      <ows:Identifier>line</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/line/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>mapnik</ows:Title>
      <ows:Identifier>mapnik</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/mapnik/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>mapnik_grid</ows:Title>
      <ows:Identifier>mapnik_grid</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>application/utfgrid</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/mapnik_grid/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>mapnik_grid_drop</ows:Title>
      <ows:Identifier>mapnik_grid_drop</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>application/utfgrid</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/mapnik_grid_drop/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point</ows:Title>
      <ows:Identifier>point</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point_error</ows:Title>
      <ows:Identifier>point_error</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point_error/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point_hash</ows:Title>
      <ows:Identifier>point_hash</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point_hash/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point_hash_no_meta</ows:Title>
      <ows:Identifier>point_hash_no_meta</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point_hash_no_meta/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point_px_buffer</ows:Title>
      <ows:Identifier>point_px_buffer</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/point_px_buffer/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>polygon</ows:Title>
      <ows:Identifier>polygon</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/polygon/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>polygon2</ows:Title>
      <ows:Identifier>polygon2</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2005</Value>
        <Value>2010</Value>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts1/tiles/wmts/1.0.0/polygon2/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_01</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_01</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>3571.4285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>1875</MatrixWidth>
        <MatrixHeight>1250</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>0_2</ows:Identifier>
        <ScaleDenominator>714.28571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>9375</MatrixWidth>
        <MatrixHeight>6250</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>0_1</ows:Identifier>
        <ScaleDenominator>357.14285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>18750</MatrixWidth>
        <MatrixHeight>12500</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

    <TileMatrixSet>
      <ows:Identifier>swissgrid_025</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0_25</ows:Identifier>
        <ScaleDenominator>892.85714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>7500</MatrixWidth>
        <MatrixHeight>5000</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

    <TileMatrixSet>
      <ows:Identifier>swissgrid_2_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>2_5</ows:Identifier>
        <ScaleDenominator>8928.5714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>750</MatrixWidth>
        <MatrixHeight>500</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

    <TileMatrixSet>
      <ows:Identifier>swissgrid_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.42857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.142857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

  </Contents>
</Capabilities>"""
        )

        l.check()

    @attr(mbtiles_rest=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_mbtiles_rest(self, l):
        self.assert_tiles_generated(
            cmd='.build/venv/bin/generate_tiles -d -c tilegeneration/test-serve.yaml'
                ' -l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ],
            regex=True,
            expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='.build/venv/bin/generate_controller -d --capabilities -c tilegeneration/test-serve.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ],
        )

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-serve.yaml',
        }
        request.matchdict = {
            'path': [
                'wmts', '1.0.0', 'point_hash', 'default', '2012', 'swissgrid_5', '1', '11', '14.png'
            ]
        }
        serve = PyramidView(request)
        serve()
        self.assertEqual(request.response.headers['Content-Type'], 'image/png')
        self.assertEqual(request.response.headers['Cache-Control'], 'max-age=28800')

        request.matchdict['path'][7] = '12'
        self.assertRaises(HTTPNoContent, serve)

        request.matchdict['path'][7] = '11'
        request.matchdict['path'][1] = '0.9'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][1] = '1.0.0'
        request.matchdict['path'][8] = '14.jpeg'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][8] = '14.png'
        request.matchdict['path'][2] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][2] = 'point_hash'
        request.matchdict['path'][3] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][3] = 'default'
        request.matchdict['path'][5] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            'wmts', 'point_hash', 'default', 'swissgrid_5', '1', '14', '11.png'
        ]
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            'wmts', '1.0.0', 'WMTSCapabilities.xml'
        ]
        PyramidView(request)()
        self.assertEqual(request.response.headers['Content-Type'], 'application/xml')
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            CAPABILITIES,
            regex=True,
        )

        request.matchdict['path'] = [
            'static', '1.0.0', 'WMTSCapabilities.xml'
        ]
        PyramidView(request)()
        self.assertEqual(request.response.headers['Content-Type'], 'application/xml')
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            CAPABILITIES,
            regex=True,
        )

        l.check()

    @attr(bsddb_rest=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_bsddb_rest(self, l):
        self.assert_tiles_generated(
            cmd='.build/venv/bin/generate_tiles -d -c tilegeneration/test-bsddb.yaml'
                ' -l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/bsddb/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5.png.bsddb')
            ],
            regex=True,
            expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='.build/venv/bin/generate_controller --capabilities -c tilegeneration/test-bsddb.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/bsddb/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5.png.bsddb')
            ],
        )

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-bsddb.yaml',
        }
        request.matchdict = {
            'path': [
                'wmts', '1.0.0', 'point_hash', 'default', '2012', 'swissgrid_5', '1', '11', '14.png'
            ]
        }
        serve = PyramidView(request)
        serve()
        self.assertEqual(request.response.headers['Content-Type'], 'image/png')
        self.assertEqual(request.response.headers['Cache-Control'], 'max-age=28800')

        request.matchdict['path'][7] = '12'
        self.assertRaises(HTTPNoContent, serve)

        request.matchdict['path'][7] = '11'
        request.matchdict['path'][1] = '0.9'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][1] = '1.0.0'
        request.matchdict['path'][8] = '14.jpeg'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][8] = '14.png'
        request.matchdict['path'][2] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][2] = 'point_hash'
        request.matchdict['path'][3] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][3] = 'default'
        request.matchdict['path'][5] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            'wmts', 'point_hash', 'default', 'swissgrid_5', '1', '14', '11.png'
        ]
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            'wmts', '1.0.0', 'WMTSCapabilities.xml'
        ]
        PyramidView(request)()
        self.assertEqual(request.response.headers['Content-Type'], 'application/xml')
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            CAPABILITIES,
            regex=True,
        )

        request.matchdict['path'] = [
            'static', '1.0.0', 'WMTSCapabilities.xml'
        ]
        PyramidView(request)()
        self.assertEqual(request.response.headers['Content-Type'], 'application/xml')
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            CAPABILITIES,
            regex=True,
        )

        l.check()

    @attr(serve_gfi=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_serve_gfi(self, l):
        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-serve.yaml',
        }
        request.params = {
            'Service': 'WMTS',
            'Version': '1.0.0',
            'Request': 'GetFeatureInfo',
            'Format': 'image/png',
            'Info_Format': 'application/vnd.ogc.gml',
            'Layer': 'point_hash',
            'Query_Layer': 'point_hash',
            'Style': 'default',
            'TileMatrixSet': 'swissgrid_5',
            'TileMatrix': '1',
            'TileRow': '11',
            'TileCol': '14',
            'I': '114',
            'J': '111',
        }
        serve = PyramidView(request)
        serve()
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            u"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""")

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-serve.yaml',
        }
        request.matchdict = {
            'path': [
                'wmts', '1.0.0', 'point_hash', 'default', '2012', 'swissgrid_5', '1', '11', '14', '114', '111.xml'
            ]
        }
        request.params = {
            'Service': 'WMTS',
            'Version': '1.0.0',
            'Request': 'GetFeatureInfo',
            'Format': 'image/png',
            'Info_Format': 'application/vnd.ogc.gml',
            'Layer': 'point_hash',
            'Query_Layer': 'point_hash',
            'Style': 'default',
            'TileMatrixSet': 'swissgrid_5',
            'TileMatrix': '1',
            'TileRow': '14',
            'TileCol': '11',
            'I': '114',
            'J': '111',
        }
        serve = PyramidView(request)
        serve()
        self.assert_result_equals(
            request.response.body.decode('utf-8') if PY3 else request.response.body,
            u"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""")

    @attr(wsgi=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_wsgi(self, l):
        self.assert_tiles_generated(
            cmd='.build/venv/bin/generate_tiles -d -c tilegeneration/test-serve.yaml '
                '-l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ],
            regex=True,
            expected="""The tile generation of layer 'point_hash' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tiles: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='.build/venv/bin/generate_controller --capabilities -c tilegeneration/test-serve.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ],
        )

        serve = app_factory({}, configfile='tilegeneration/test-serve.yaml')

        global code, headers
        code = None
        headers = None

        def start_response(p_code, p_headers):
            global code, headers
            code = p_code
            headers = {}
            for key, value in p_headers:
                headers[key] = value
        result = serve({
            'QUERY_STRING': '&'.join(['%s=%s' % item for item in {
                'Service': 'WMTS',
                'Version': '1.0.0',
                'Request': 'GetFeatureInfo',
                'Format': 'image/png',
                'Info_Format': 'application/vnd.ogc.gml',
                'Layer': 'point_hash',
                'Query_Layer': 'point_hash',
                'Style': 'default',
                'TileMatrixSet': 'swissgrid_5',
                'TileMatrix': '1',
                'TileRow': '11',
                'TileCol': '14',
                'I': '114',
                'J': '111',
            }.items()])
        }, start_response)
        self.assertEqual(code, '200 OK')
        self.assert_result_equals(
            result[0].decode("utf-8") if PY3 else result[0],
            u"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""")

        result = serve({
            'QUERY_STRING': '',
            'PATH_INFO': '/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/14/11/114/111.xml'
        }, start_response)
        self.assert_result_equals(
            result[0].decode("utf-8") if PY3 else result[0],
            u"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""")

        result = serve({
            'QUERY_STRING': '',
            'PATH_INFO': '/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/11/12.png'
        }, start_response)
        self.assertEqual(code, '204 No Content')

        result = serve({
            'QUERY_STRING': '',
            'PATH_INFO': '/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/11/14.png'
        }, start_response)
        self.assertEqual(code, '200 OK')
        self.assertEqual(headers['Cache-Control'], 'max-age=28800')

        result = serve({
            'QUERY_STRING': '',
            'PATH_INFO': '/wmts/1.0.0/WMTSCapabilities.xml'
        }, start_response)
        self.assertEqual(code, '200 OK')
        self.assert_result_equals(
            result[0].decode("utf-8") if PY3 else result[0],
            CAPABILITIES,
            regex=True,
        )
