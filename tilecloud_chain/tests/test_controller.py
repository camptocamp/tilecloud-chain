# -*- coding: utf-8 -*-

import os
import shutil

from nose.plugins.attrib import attr

from tilecloud_chain.tests import CompareCase
from tilecloud_chain import controller


class TestController(CompareCase):

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

    @attr(capabilities=True)
    @attr(controller=True)
    @attr(general=True)
    def test_capabilities(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-fix.yaml',
            main_func=controller.main,
            expected=[[
                '/tmp/tiles/1.0.0/WMTSCapabilities.xml',
                u"""<?xml version="1.0" encoding="UTF-8"?>
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
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://taurus/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
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
</Capabilities>"""]])

    MULTIHOST_CAPABILITIES = u"""<?xml version="1.0" encoding="UTF-8"?>
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
          <ows:Get xlink:href="http://wmts1/tiles/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://wmts1/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://wmts2/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://wmts3/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
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
                   template="http://wmts1/tiles/1.0.0/point_hash_no_meta/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_hash_no_meta/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_hash_no_meta/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/all/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/all/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/all/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/point_hash/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_hash/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_hash/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/polygon/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/polygon/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/polygon/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/point/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik_grid/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik_grid/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid_drop/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik_grid_drop/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik_grid_drop/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/line/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/line/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/line/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/polygon2/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/polygon2/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/polygon2/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_01</TileMatrixSet>
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
                   template="http://wmts1/tiles/1.0.0/point_px_buffer/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_px_buffer/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_px_buffer/default/""" \
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
                   template="http://wmts1/tiles/1.0.0/mapnik/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik/default/""" \
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik/default/""" \
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

    @attr(multi_host_capabilities=True)
    @attr(controller=True)
    @attr(general=True)
    def test_multi_host_capabilities(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-fix.yaml '
            '--destination-cache multi_host',
            main_func=controller.main,
            expected=[['/tmp/tiles/1.0.0/WMTSCapabilities.xml', self.MULTIHOST_CAPABILITIES]])

    @attr(capabilities_slash=True)
    @attr(capabilities=True)
    @attr(controller=True)
    @attr(general=True)
    def test_capabilities_slash(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-capabilities.yaml',
            main_func=controller.main,
            expected=[[
                '/tmp/tiles/1.0.0/WMTSCapabilities.xml',
                u"""<?xml version="1.0" encoding="UTF-8"?>
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
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://taurus/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
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
      <ows:Title>no_dim</ows:Title>
      <ows:Identifier>no_dim</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://taurus/tiles/1.0.0/no_dim/default/"""
                """{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>two</ows:Title>
      <ows:Identifier>two</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2012</Value>
      </Dimension>
      <Dimension>
        <ows:Identifier>LEVEL</ows:Identifier>
        <Default>1</Default>
        <Value>1</Value>
        <Value>2</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://taurus/tiles/1.0.0/two/default/"""
                """{DATE}/{LEVEL}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>one</ows:Title>
      <ows:Identifier>one</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
      </Style>
      <Format>image/png</Format>
      <Dimension>
        <ows:Identifier>DATE</ows:Identifier>
        <Default>2012</Default>
        <Value>2012</Value>
      </Dimension>
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://taurus/tiles/1.0.0/one/default/"""
                """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid</ows:Identifier>
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
        <ScaleDenominator>35714.2857143</ScaleDenominator>
        <TopLeftCorner>420000.0 350000.0</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>

    </TileMatrixSet>

  </Contents>
</Capabilities>"""]])

    @attr(multi_url_capabilities=True)
    @attr(controller=True)
    @attr(general=True)
    def test_multi_url_capabilities(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-fix.yaml '
            '--destination-cache multi_url',
            main_func=controller.main,
            expected=[['/tmp/tiles/1.0.0/WMTSCapabilities.xml', self.MULTIHOST_CAPABILITIES]])

    @attr(mapcache=True)
    @attr(controller=True)
    @attr(general=True)
    def test_mapcache(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --mapcache -c tilegeneration/test-fix.yaml',
            main_func=controller.main,
            expected=[['mapcache.xml', u"""<?xml version="1.0" encoding="UTF-8"?>
<mapcache>
    <cache name="default" type="memcache">
       <server>
          <host>localhost</host>
          <port>11211</port>
       </server>
    </cache>


   <grid name="swissgrid_01">
      <size>256 256</size>
      <extent>420000.0 30000.0 900000.0 350000.0</extent>
      <srs>epsg:21781</srs>
      <units>m</units>
      <resolutions>1.0 0.2 0.1 </resolutions>
      <origin>top-left</origin>
   </grid>

   <grid name="swissgrid_5">
      <size>256 256</size>
      <extent>420000.0 30000.0 900000.0 350000.0</extent>
      <srs>epsg:21781</srs>
      <units>m</units>
      <resolutions>100.0 50.0 20.0 10.0 5.0 </resolutions>
      <origin>top-left</origin>
   </grid>

   <grid name="swissgrid_025">
      <size>256 256</size>
      <extent>420000.0 30000.0 900000.0 350000.0</extent>
      <srs>epsg:21781</srs>
      <units>m</units>
      <resolutions>0.25 </resolutions>
      <origin>top-left</origin>
   </grid>

   <grid name="swissgrid_2_5">
      <size>256 256</size>
      <extent>420000.0 30000.0 900000.0 350000.0</extent>
      <srs>epsg:21781</srs>
      <units>m</units>
      <resolutions>2.5 </resolutions>
      <origin>top-left</origin>
   </grid>


   <source name="point_hash_no_meta" type="wms">
      <getmap>
         <params>
            <LAYERS>point</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="all" type="wms">
      <getmap>
         <params>
            <LAYERS>point,line,polygon</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="point_hash" type="wms">
      <getmap>
         <params>
            <LAYERS>point</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="polygon" type="wms">
      <getmap>
         <params>
            <LAYERS>polygon</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="point" type="wms">
      <getmap>
         <params>
            <LAYERS>point</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="line" type="wms">
      <getmap>
         <params>
            <LAYERS>line</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <PARAM>value</PARAM>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Cache-Control>no-cache</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="polygon2" type="wms">
      <getmap>
         <params>
            <LAYERS>polygon</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>

   <source name="point_px_buffer" type="wms">
      <getmap>
         <params>
            <LAYERS>point</LAYERS>
            <TRANSPARENT>TRUE</TRANSPARENT>
            <FORMAT>image/png</FORMAT>
         </params>
      </getmap>
      <http>
         <url>http://localhost/mapserv</url>
         <headers>
            <Pragma>no-cache</Pragma>
            <Cache-Control>no-cache, no-store</Cache-Control>
         </headers>
      </http>
   </source>


   <tileset name="point_hash_no_meta">
      <source>point_hash_no_meta</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="all">
      <source>all</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="point_hash">
      <source>point_hash</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <metatile>8 8</metatile>
      <metabuffer>128</metabuffer>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="polygon">
      <source>polygon</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="point">
      <source>point</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <metatile>8 8</metatile>
      <metabuffer>128</metabuffer>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="line">
      <source>line</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <metatile>8 8</metatile>
      <metabuffer>128</metabuffer>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="polygon2">
      <source>polygon2</source>
      <cache>default</cache>
      <grid>swissgrid_01</grid>
      <metatile>8 8</metatile>
      <metabuffer>128</metabuffer>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>

   <tileset name="point_px_buffer">
      <source>point_px_buffer</source>
      <cache>default</cache>
      <grid>swissgrid_5</grid>
      <metatile>8 8</metatile>
      <metabuffer>128</metabuffer>
      <format>image/png</format>
      <expires>3600</expires> <!-- 1 hour -->
      <auto_expire>13800</auto_expire> <!-- 4 hours -->
      <dimensions>
        <dimension type="values" name="DATE" default="2012">2005,2010,2012</dimension>
      </dimensions>
   </tileset>


   <format name="image/png" type="PNG">
      <compression>fast</compression>
      <colors>256</colors>
   </format>
   <format name="image/jpeg" type="JPEG">
      <quality>90</quality>
      <photometric>rgb</photometric>
   </format>

   <service type="wms" enabled="false"/>
   <service type="wmts" enabled="true"/>
   <service type="tms" enabled="false"/>
   <service type="kml" enabled="false"/>
   <service type="gmaps" enabled="false"/>
   <service type="ve" enabled="false"/>
   <service type="demo" enabled="false"/>

   <default_format>image/jpeg</default_format>
   <errors>report</errors>
   <lock_dir>/tmp</lock_dir>
</mapcache>"""]])

    @attr(apache=True)
    @attr(controller=True)
    @attr(general=True)
    def test_apache(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --apache -c tilegeneration/test-fix.yaml',
            main_func=controller.main,
            expected=[[
                'tiles.conf',
                u"""<Location /tiles>
    ExpiresActive on
    ExpiresDefault "now plus 8 hours"
</Location>

Alias /tiles /tmp/tiles/

RewriteRule ^/tiles/1.0.0/point_hash/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/4/(.*)$ """
                """/mapcache/wmts/1.0.0/point_hash/$1/$2/$3/4/$4 [PT]
RewriteRule ^/tiles/1.0.0/point/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/4/(.*)$ """
                """/mapcache/wmts/1.0.0/point/$1/$2/$3/4/$4 [PT]

MapCacheAlias /mapcache "%s"
""" % (os.path.abspath('mapcache.xml'))]])

        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --apache -c tilegeneration/test-serve.yaml',
            main_func=controller.main,
            expected=[['tiles.conf', u"""
MapCacheAlias /mapcache "%s"
""" % (os.path.abspath('mapcache.xml'))]])

    @attr(apache_s3=True)
    @attr(controller=True)
    @attr(general=True)
    def test_apache_s3(self):
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --cache s3 --apache -c tilegeneration/test-fix.yaml',
            main_func=controller.main,
            expected=[[
                'tiles.conf',
                u"""<Location /tiles>
    ExpiresActive on
    ExpiresDefault "now plus 8 hours"
</Location>

<Proxy http://s3-eu-west-1.amazonaws.com/tiles/tiles/*>
    Order deny,allow
    Allow from all
</Proxy>
ProxyPass /tiles/ http://s3-eu-west-1.amazonaws.com/tiles/tiles/
ProxyPassReverse /tiles/ http://s3-eu-west-1.amazonaws.com/tiles/tiles/

RewriteRule ^/tiles/1.0.0/point_hash/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/4/(.*)$ """
                """/mapcache/wmts/1.0.0/point_hash/$1/$2/$3/4/$4 [PT]
RewriteRule ^/tiles/1.0.0/point/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/([a-zA-Z0-9_]+)/4/(.*)$ """
                """/mapcache/wmts/1.0.0/point/$1/$2/$3/4/$4 [PT]

MapCacheAlias /mapcache "%s"
""" % (os.path.abspath('mapcache.xml'))]])

    CONFIG = u"""apache: {config_file: tiles.conf, expires: 8, location: /tiles}
caches:
  local: {folder: /tmp/tiles, hosts: false, http_url: 'http://taurus/tiles', http_urls: false,
    name: local, type: filesystem, wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml}
  mbtiles: {folder: /tmp/tiles/mbtiles, http_url: 'http://taurus/tiles', name: mbtiles, type: """ \
                """mbtiles, wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml}
  multi_host:
    folder: /tmp/tiles
    hosts: [wmts1, wmts2, wmts3]
    http_url: http://%(host)s/tiles
    name: multi_host
    type: filesystem
    wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml
  multi_url:
    folder: /tmp/tiles
    http_urls: ['http://wmts1/tiles', 'http://wmts2/tiles', 'http://wmts3/tiles']
    name: multi_url
    type: filesystem
    wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml
  s3: {bucket: tiles, folder: tiles, host: s3-eu-west-1.amazonaws.com, """ \
        """http_url: 'https://%(host)s/%(bucket)s/%(folder)s',
    name: s3, region: eu-west-1, type: s3, wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml}
cost:
  cloudfront: {download: 0.12, get: 0.009}
  ec2: {usage: 0.17}
  esb: {io: 260.0, storage: 0.11}
  esb_size: 100
  request_per_layers: 10000000
  s3: {download: 0.12, get: 0.01, put: 0.01, storage: 0.125}
  sqs: {request: 0.01}
ec2:
  apache_config: /tmp/tests/test.conf
  apache_content: test file
  build_cmds:
  - python bootstrap.py --distribute -v 1.7.1
  - ./buildout/bin/buildout
  code_folder: /tmp/tests/test/
  deploy_config: tests/deploy.cfg
  deploy_user: deploy
  disable_code: false
  disable_database: false
  disable_fillqueue: false
  disable_geodata: false
  disable_tilesgen: false
  host_type: m1.medium
  geodata_folder: tilecloud_chain/
  number_process: 1
generation:
  default_cache: local
  default_layers: [line, polygon]
  error_file: error.list
  log_format: '%(levelname)s:%(name)s:%(funcName)s:%(message)s'
  maxconsecutive_errors: 2
grids:
  swissgrid_01: &id004
    bbox: [420000.0, 30000.0, 900000.0, 350000.0]
    matrix_identifier: resolution
    name: swissgrid_01
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000""" \
    u""" +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 10
    resolutions: [1.0, 0.2, 0.1]
    srs: epsg:21781
    tile_size: 256
    unit: m
  swissgrid_025:
    bbox: [420000.0, 30000.0, 900000.0, 350000.0]
    matrix_identifier: resolution
    name: swissgrid_025
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000""" \
        u""" +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 4
    resolutions: [0.25]
    srs: epsg:21781
    tile_size: 256
    unit: m
  swissgrid_2_5:
    bbox: [420000.0, 30000.0, 900000.0, 350000.0]
    matrix_identifier: resolution
    name: swissgrid_2_5
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000""" \
        u""" +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 2
    resolutions: [2.5]
    srs: epsg:21781
    tile_size: 256
    unit: m
  swissgrid_5: &id003
    bbox: [420000.0, 30000.0, 900000.0, 350000.0]
    matrix_identifier: zoom
    name: swissgrid_5
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000""" \
        u""" +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 1
    resolutions: [100.0, 50.0, 20.0, 10.0, 5.0]
    srs: epsg:21781
    tile_size: 256
    unit: m
layer_default:
  connection: user=postgres password=postgres dbname=tests host=localhost
  cost: &id001 {metatile_generation_time: 30.0, tile_generation_time: 30.0, tile_size: 20.0,
    tileonly_generation_time: 60.0}
  dimensions: &id002
  - default: '2012'
    name: DATE
    value: '2012'
    values: ['2005', '2010', '2012']
  extension: png
  grid: swissgrid_5
  meta: true
  meta_buffer: 128
  meta_size: 8
  mime_type: image/png
  type: wms
  wmts_style: default
layers:
  all:
    bbox: [550000.0, 170000.0, 560000.0, 180000.0]
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    extension: png
    generate_salt: false
    geoms: []
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [point, line, polygon]
    meta: false
    meta_buffer: 128
    meta_size: 1
    mime_type: image/png
    name: all
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  line:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_metatile_detection: {hash: 01062bb3b25dcead792d7824f9a7045f0dd92992, size: 20743}
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.line}
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache'}
    layers: [line]
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    name: line
    params: {PARAM: value}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  mapnik:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    data_buffer: 128
    dimensions: *id002
    extension: png
    geoms:
    - {sql: the_geom AS geom FROM tests.polygon}
    grid: swissgrid_5
    grid_ref: *id003
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 128
    meta_size: 1
    mime_type: image/png
    name: mapnik
    output_format: png
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: mapnik
    wmts_style: default
  mapnik_grid:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    data_buffer: 128
    dimensions: *id002
    extension: json
    geoms:
    - {sql: the_geom AS geom FROM tests.polygon}
    grid: swissgrid_5
    grid_ref: *id003
    drop_empty_utfgrid: false
    layers_fields:
      line: [name]
      point: [name]
      polygon: [name]
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 128
    meta_size: 1
    mime_type: application/utfgrid
    name: mapnik_grid
    output_format: grid
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    resolution: 16
    type: mapnik
    wmts_style: default
  mapnik_grid_drop:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    data_buffer: 128
    dimensions: *id002
    extension: json
    geoms:
    - {sql: the_geom AS geom FROM tests.polygon}
    grid: swissgrid_5
    grid_ref: *id003
    drop_empty_utfgrid: true
    layers_fields:
      point: [name]
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 0
    meta_size: 1
    mime_type: application/utfgrid
    name: mapnik_grid_drop
    output_format: grid
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    resolution: 16
    type: mapnik
    wmts_style: default
  point:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.point}
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [point]
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    min_resolution_seed: 10.0
    name: point
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    sqs: {queue: sqs_point, region: eu-west-1}
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  point_hash_no_meta:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms: []
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [point]
    meta: false
    meta_buffer: 128
    meta_size: 1
    mime_type: image/png
    name: point_hash_no_meta
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  point_hash:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_metatile_detection: {hash: 01062bb3b25dcead792d7824f9a7045f0dd92992, size: 20743}
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.point}
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [point]
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    min_resolution_seed: 10.0
    name: point_hash
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  point_px_buffer:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_metatile_detection: {hash: 01062bb3b25dcead792d7824f9a7045f0dd92992, size: 20743}
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.point}
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [point]
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    name: point_px_buffer
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: 100.0
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  polygon:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_metatile_detection: {hash: 01062bb3b25dcead792d7824f9a7045f0dd92992, size: 20743}
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.polygon}
    grid: swissgrid_5
    grid_ref: *id003
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [polygon]
    meta: false
    meta_buffer: 128
    meta_size: 1
    mime_type: image/png
    name: polygon
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
  polygon2:
    connection: user=postgres password=postgres dbname=tests host=localhost
    cost: *id001
    dimensions: *id002
    empty_metatile_detection: {hash: 01062bb3b25dcead792d7824f9a7045f0dd92992, size: 20743}
    empty_tile_detection: {hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8, size: 334}
    extension: png
    generate_salt: false
    geoms:
    - {sql: the_geom AS geom FROM tests.polygon}
    grid: swissgrid_01
    grid_ref: *id004
    headers: {Cache-Control: 'no-cache, no-store', Pragma: no-cache}
    layers: [polygon]
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    name: polygon2
    params: {}
    post_process: false
    pre_hash_post_process: false
    px_buffer: false
    type: wms
    url: http://localhost/mapserv
    wmts_style: default
mapcache: {config_file: mapcache.xml, memcache_host: localhost, memcache_port: 11211, location: /mapcache}
openlayers: {center_x: 600000.0, center_y: 200000.0, srs: 'epsg:21781'}
process: {}
sns: {region: eu-west-1, topic: 'arn:aws:sns:eu-west-1:your-account-id:tilecloud'}"""

    @attr(config=True)
    @attr(controller=True)
    @attr(general=True)
    def test_config(self):
        self.assert_cmd_yaml_equals(
            cmd='./buildout/bin/generate_controller --dump-config -c tilegeneration/test-fix.yaml',
            main_func=controller.main, expected=self.CONFIG)

    @attr(config_line=True)
    @attr(controller=True)
    @attr(general=True)
    def test_config_line(self):
        self.assert_cmd_yaml_equals(
            cmd='./buildout/bin/generate_controller -l line --dump-config -c tilegeneration/test-fix.yaml',
            main_func=controller.main, expected=self.CONFIG)

    @attr(openlayers=True)
    @attr(controller=True)
    @attr(general=True)
    def test_openlayers(self):
        html = u"""<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>OpenLayers test page</title>
    <style>
        html, body, #map {
            width: 100%;
            height: 100%;
            margin: 0;
        }
        #attrs {
            position: absolute;
            zindex: 1000;
            bottom: 1em;
            left: 1em;
        }
    </style>
</head>
<body>
    <div id="map">
        <div id="attrs"></div>
    </div>
    <script src="OpenLayers.js"></script>
    <script src="wmts.js"></script>
</body>
</html>"""
        js = u"""var callback = function(infoLookup) {
    var msg = "";
    if (infoLookup) {
        var info;
        for (var idx in infoLookup) {
            // idx can be used to retrieve layer from map.layers[idx]
            info = infoLookup[idx];
            if (info && info.data) {
                msg += "[" + info.id + "]"
                for (k in info.data) {
                    msg += '<br />' + k + ': ' + info.data[k];
                }
            }
        }
    }
    document.getElementById("attrs").innerHTML = msg;
};

map = new OpenLayers.Map({
    div: "map",
    projection: "epsg:21781",
    controls: [
        new OpenLayers.Control.Navigation(),
        new OpenLayers.Control.Zoom(),
        new OpenLayers.Control.MousePosition(),
        new OpenLayers.Control.LayerSwitcher(),
        new OpenLayers.Control.Permalink(),
        new OpenLayers.Control.UTFGrid({
            callback: callback,
            handlerMode: "hover",
            handlerOptions: {
                'delay': 0,
                'pixelTolerance': 0
            },
            reset: function() {}
        })
    ],
    center: [600000.0, 200000.0],
    zoom: 0
});

var format = new OpenLayers.Format.WMTSCapabilities();
OpenLayers.Request.GET({
    url: "%s",
    success: function(request) {
        var doc = request.responseXML;
        if (!doc || !doc.documentElement) {
            doc = request.responseText;
        }
        var capabilities = format.read(doc);

        map.addLayer(format.createLayer(capabilities, {
            layer: "point_hash_no_meta",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "all",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "point_hash",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "polygon",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "point",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "mapnik_grid",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: false,
            utfgridResolution: 16
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "mapnik_grid_drop",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: false,
            utfgridResolution: 16
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "line",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "polygon2",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "point_px_buffer",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
        map.addLayer(format.createLayer(capabilities, {
            layer: "mapnik",
            maxExtent: [420000.0, 30000.0, 900000.0, 350000.0],
            isBaseLayer: true
        }));
    },
    failure: function() {
        alert("Trouble getting capabilities doc");
        OpenLayers.Console.error.apply(OpenLayers.Console, arguments);
    }
});"""
        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --openlayers -c tilegeneration/test-fix.yaml',
            main_func=controller.main,
            expected=[
                ['/tmp/tiles/index.html', html],
                ['/tmp/tiles/wmts.js', js % 'http://taurus/tiles/1.0.0/WMTSCapabilities.xml']
            ]
        )

        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --openlayers -c tilegeneration/test-fix.yaml --cache multi_host',
            main_func=controller.main,
            expected=[
                ['/tmp/tiles/index.html', html],
                ['/tmp/tiles/wmts.js', js % 'http://wmts1/tiles/1.0.0/WMTSCapabilities.xml']
            ]
        )

        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --openlayers -c tilegeneration/test-fix.yaml --cache multi_url',
            main_func=controller.main,
            expected=[
                ['/tmp/tiles/index.html', html],
                ['/tmp/tiles/wmts.js', js % 'http://wmts1/tiles/1.0.0/WMTSCapabilities.xml']
            ]
        )

    @attr(quote=True)
    @attr(controller=True)
    @attr(general=True)
    def test_quote(self):
        from tilecloud_chain import quote
        self.assertEquals(quote("abc"), "abc")
        self.assertEquals(quote("a b c"), "'a b c'")
        self.assertEquals(quote("'a b c'"), "\"'a b c'\"")
        self.assertEquals(quote('"a b c"'), '\'"a b c"\'')
        self.assertEquals(quote("a\" b' c"), "'a\" b\\' c'")
        self.assertEquals(quote(""), "''")

    @attr(legends=True)
    @attr(controller=True)
    @attr(general=True)
    def test_legends(self):
        self.assert_tiles_generated(
            cmd='./buildout/bin/generate_controler -c tilegeneration/test-legends.yaml --legends',
            main_func=controller.main,
            directory="/tmp/tiles/",
            tiles_pattern='1.0.0/%s/default/legend%i.png',
            tiles=[
                ('point', 0), ('line', 0), ('line', 2), ('polygon', 0), ('all', 0), ('all', 2),
            ]
        )

        self.assert_main_equals(
            cmd='./buildout/bin/generate_controller --capabilities -c tilegeneration/test-legends.yaml',
            main_func=controller.main,
            expected=[[
                '/tmp/tiles/1.0.0/WMTSCapabilities.xml',
                u"""<?xml version="1.0" encoding="UTF-8"?>
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
        </ows:HTTP>
      </ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetTile">
      <ows:DCP>
        <ows:HTTP>
          <ows:Get xlink:href="http://taurus/tiles/">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
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
      <ows:Title>line</ows:Title>
      <ows:Identifier>line</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/line/default/legend0.png" """
                """width="71" height="21" minScaleDenominator="112938.487863" />
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/line/default/legend2.png" """
                """width="71" height="21" maxScaleDenominator="112938.487863" />
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
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>polygon</ows:Title>
      <ows:Identifier>polygon</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/polygon/default/legend0.png" """
                """width="77" height="21" />
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
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>all</ows:Title>
      <ows:Identifier>all</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/all/default/legend0.png" """
                """width="77" height="63" minScaleDenominator="112938.487863" />
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/all/default/legend2.png" """
                """width="77" height="63" maxScaleDenominator="112938.487863" />
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
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point</ows:Title>
      <ows:Identifier>point</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://taurus/tiles/1.0.0/point/default/legend0.png" """
                """width="65" height="21" />
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
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid</ows:Identifier>
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
</Capabilities>"""]])
