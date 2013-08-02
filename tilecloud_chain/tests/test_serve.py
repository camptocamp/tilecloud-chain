# -*- coding: utf-8 -*-

import os
import shutil

from testfixtures import log_capture
from nose.plugins.attrib import attr
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPNoContent, HTTPBadRequest

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import generate, controller
from tilecloud_chain.views.serve import Serve


class TestServe(CompareCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(__file__))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @classmethod
    def tearDownClass(self):
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists('/tmp/tiles'):
            shutil.rmtree('/tmp/tiles')

    @attr(serve_kvp=True)
    @attr(serve=True)
    @attr(general=True)
    @log_capture('tilecloud_chain', level=30)
    def test_serve_kvp(self, l):
        self.assert_tiles_generated(
            cmd='./buildout/bin/generate_tiles -d -c tilegeneration/test-nosns.yaml '
                '-l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5/1/11/14.png'),
                ('point_hash/default/2012/swissgrid_5/1/15/8.png'),
            ]
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-nosns.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5/1/11/14.png'),
                ('point_hash/default/2012/swissgrid_5/1/15/8.png'),
            ]
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
            'TileRow': '14',
            'TileCol': '11',
        }
        serve = Serve(request)
        serve()
# tilecloud bug
#        self.assertEquals(request.response.content_type, 'image/png')

        request.params['TileRow'] = '15'
        self.assertRaises(HTTPNoContent, serve)

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
        Serve(request)()
        self.assertEquals(request.response.content_type, 'application/xml')
        self.assert_result_equals(
            request.response.body, u"""<?xml version="1.0" encoding="UTF-8"?>
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
          <ows:Get xlink:href="http://taurus/tiles/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://taurus/tiles">
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
          <ows:Get xlink:href="http://taurus/tiles">
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
                   template="http://taurus/tiles/1.0.0/point_hash_no_meta/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

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
                   template="http://taurus/tiles/1.0.0/all/default/"""
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
                   template="http://taurus/tiles/1.0.0/point_hash/default/"""
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
                   template="http://taurus/tiles/1.0.0/polygon/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
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
                   template="http://taurus/tiles/1.0.0/point/default/"""
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
                   template="http://taurus/tiles/1.0.0/point_px_buffer/default/"""
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
                   template="http://taurus/tiles/1.0.0/mapnik_grid/default/"""
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
                   template="http://taurus/tiles/1.0.0/mapnik_grid_drop/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
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
                   template="http://taurus/tiles/1.0.0/line/default/"""
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
                   template="http://taurus/tiles/1.0.0/polygon2/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_01</TileMatrixSet>
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
                   template="http://taurus/tiles/1.0.0/point_error/default/"""
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
                   template="http://taurus/tiles/1.0.0/mapnik/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_01</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>3571.42857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>1875</MatrixWidth>
        <MatrixHeight>1250</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>0_2</ows:Identifier>
        <ScaleDenominator>714.285714286</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>9375</MatrixWidth>
        <MatrixHeight>6250</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>0_1</ows:Identifier>
        <ScaleDenominator>357.142857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>18750</MatrixWidth>
        <MatrixHeight>12500</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

    <TileMatrixSet>
      <ows:Identifier>swissgrid_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.428571</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.5714286</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.2857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.1428571</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

    <TileMatrixSet>
      <ows:Identifier>swissgrid_025</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:epsg::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0_25</ows:Identifier>
        <ScaleDenominator>892.857142857</ScaleDenominator>
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
        <ScaleDenominator>8928.57142857</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>750</MatrixWidth>
        <MatrixHeight>500</MatrixHeight>
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
            cmd='./buildout/bin/generate_tiles -d -c tilegeneration/test-serve.yaml'
                ' -l point_hash --zoom 1',
            main_func=generate.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ]
        )
        # use delete to don't delete the repository
        self.assert_tiles_generated_deleted(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-serve.yaml',
            main_func=controller.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern='1.0.0/%s',
            tiles=[
                ('WMTSCapabilities.xml'),
                ('point_hash/default/2012/swissgrid_5.png.mbtiles')
            ]
        )

        request = DummyRequest()
        request.registry.settings = {
            'tilegeneration_configfile': 'tilegeneration/test-serve.yaml',
        }
        request.matchdict = {
            'path': [
                '1.0.0', 'point_hash', 'default', '2012', 'swissgrid_5', '1', '14', '11.png'
            ]
        }
        serve = Serve(request)
        serve()
        self.assertEquals(request.response.content_type, 'image/png')

        request.matchdict['path'][6] = '15'
        self.assertRaises(HTTPNoContent, serve)

        request.matchdict['path'][6] = '14'
        request.matchdict['path'][0] = '0.9'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][0] = '1.0.0'
        request.matchdict['path'][7] = '14.jpeg'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][7] = '14.png'
        request.matchdict['path'][1] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][1] = 'point_hash'
        request.matchdict['path'][2] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'][2] = 'default'
        request.matchdict['path'][4] = 'test'
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            'point_hash', 'default', 'swissgrid_5', '1', '14', '11.png'
        ]
        self.assertRaises(HTTPBadRequest, serve)

        request.matchdict['path'] = [
            '1.0.0', 'WMTSCapabilities.xml'
        ]
        Serve(request)()
        self.assertEquals(request.response.content_type, 'application/xml')
        self.assert_result_equals(
            request.response.body,
            """<?xml version="1.0" encoding="UTF-8"?>
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
          <ows:Get xlink:href="http://taurus/tiles/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://taurus/tiles">
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
          <ows:Get xlink:href="http://taurus/tiles">
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
                   template="http://taurus/tiles/1.0.0/point_hash/default/{DATE}/"""
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
        <ScaleDenominator>357142.857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.428571</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.5714286</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.2857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>

      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.1428571</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

  </Contents>
</Capabilities>""")

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
            'TileRow': '14',
            'TileCol': '11',
            'I': '114',
            'J': '111',
        }
        serve = Serve(request)
        serve()
        self.assert_result_equals(
            request.response.body, u"""<?xml version="1.0" encoding="UTF-8"?>

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
                '1.0.0', 'point_hash', 'default', '2012', 'swissgrid_5', '1', '14', '11', '114', '111.xml'
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
        serve = Serve(request)
        serve()
        self.assert_result_equals(
            request.response.body, u"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""")
