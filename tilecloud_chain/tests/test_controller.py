import os
import shutil
from pathlib import Path

import pytest
import pytest_check
import yaml
from PIL import Image

from tilecloud_chain import TileGeneration, controller
from tilecloud_chain.tests import CompareCase


class TestController(CompareCase):
    def setUp(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        os.chdir(os.path.dirname(__file__))
        if os.path.exists("/tmp/tiles"):
            shutil.rmtree("/tmp/tiles")

    @classmethod
    def tearDownClass(cls):  # noqa
        os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if os.path.exists("/tmp/tiles"):
            shutil.rmtree("/tmp/tiles")

    @pytest.mark.asyncio
    async def test_capabilities(self) -> None:
        gene = TileGeneration(Path("tilegeneration/test-fix.yaml"), configure_logging=False)
        config = gene.get_config(Path("tilegeneration/test-fix.yaml"))
        self.assert_result_equals(
            await controller.get_wmts_capabilities(gene, config.config["generation"]["default_cache"]),
            r"""<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0"
    xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification>
    <ows:Title>Some title</ows:Title>
    <ows:Abstract>Some abstract</ows:Abstract>
    <ows:Keywords>
        <ows:Keyword>some</ows:Keyword>
        <ows:Keyword>keywords</ows:Keyword>
    </ows:Keywords>
    <ows:ServiceType>OGC WMTS</ows:ServiceType>
    <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
    <ows:Fees>None</ows:Fees>
    <ows:AccessConstraint>None</ows:AccessConstraint>
  </ows:ServiceIdentification>
  <ows:ServiceProvider>
    <ows:ProviderName>The provider name</ows:ProviderName>
    <ows:ProviderSite>The provider URL</ows:ProviderSite>
    <ows:ServiceContact>
      <ows:IndividualName>The contact name</ows:IndividualName>
      <ows:PositionName>The position name</ows:PositionName>
      <ows:ContactInfo>
        <ows:Phone>
          <ows:Voice>\+41 11 222 33 44</ows:Voice>
          <ows:Facsimile>\+41 11 222 33 44</ows:Facsimile>
        </ows:Phone>
        <ows:Address>
          <ows:DeliveryPoint>Address delivery</ows:DeliveryPoint>
          <ows:City>Berne</ows:City>
          <ows:AdministrativeArea>BE</ows:AdministrativeArea>
          <ows:PostalCode>3000</ows:PostalCode>
          <ows:Country>Switzerland</ows:Country>
          <ows:ElectronicMailAddress>info@example.com</ows:ElectronicMailAddress>
        </ows:Address>
      </ows:ContactInfo>
    </ows:ServiceContact>
  </ows:ServiceProvider>
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
                   template="http://wmts1/tiles/1.0.0/all/default/"""
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
                   template="http://wmts1/tiles/1.0.0/line/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid_drop/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_hash/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_hash_no_meta/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_px_buffer/default/"""
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
                   template="http://wmts1/tiles/1.0.0/polygon/default/"""
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
                   template="http://wmts1/tiles/1.0.0/polygon2/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_01</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_01</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>3571.4285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>1875</MatrixWidth>
        <MatrixHeight>1250</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>0_2</ows:Identifier>
        <ScaleDenominator>714.28571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>9375</MatrixWidth>
        <MatrixHeight>6250</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>0_1</ows:Identifier>
        <ScaleDenominator>357.14285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>18750</MatrixWidth>
        <MatrixHeight>12500</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_025</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0_25</ows:Identifier>
        <ScaleDenominator>892.85714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>7500</MatrixWidth>
        <MatrixHeight>5000</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_2_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>2_5</ows:Identifier>
        <ScaleDenominator>8928.5714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>750</MatrixWidth>
        <MatrixHeight>500</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.42857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.142857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>""",
            True,
        )

    MULTIHOST_CAPABILITIES = (
        r"""<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0"
    xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
  <ows:ServiceIdentification>
    <ows:Title>Some title</ows:Title>
    <ows:Abstract>Some abstract</ows:Abstract>
    <ows:Keywords>
        <ows:Keyword>some</ows:Keyword>
        <ows:Keyword>keywords</ows:Keyword>
    </ows:Keywords>
    <ows:ServiceType>OGC WMTS</ows:ServiceType>
    <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
    <ows:Fees>None</ows:Fees>
    <ows:AccessConstraint>None</ows:AccessConstraint>
  </ows:ServiceIdentification>
  <ows:ServiceProvider>
    <ows:ProviderName>The provider name</ows:ProviderName>
    <ows:ProviderSite>The provider URL</ows:ProviderSite>
    <ows:ServiceContact>
      <ows:IndividualName>The contact name</ows:IndividualName>
      <ows:PositionName>The position name</ows:PositionName>
      <ows:ContactInfo>
        <ows:Phone>
          <ows:Voice>\+41 11 222 33 44</ows:Voice>
          <ows:Facsimile>\+41 11 222 33 44</ows:Facsimile>
        </ows:Phone>
        <ows:Address>
          <ows:DeliveryPoint>Address delivery</ows:DeliveryPoint>
          <ows:City>Berne</ows:City>
          <ows:AdministrativeArea>BE</ows:AdministrativeArea>
          <ows:PostalCode>3000</ows:PostalCode>
          <ows:Country>Switzerland</ows:Country>
          <ows:ElectronicMailAddress>info@example.com</ows:ElectronicMailAddress>
        </ows:Address>
      </ows:ContactInfo>
    </ows:ServiceContact>
  </ows:ServiceProvider>
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
                   template="http://wmts1/tiles/1.0.0/all/default/"""
        r"""{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/all/default/"""
        r"""{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/all/default/"""
        r"""{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
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
                   template="http://wmts1/tiles/1.0.0/line/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/line/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/line/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik_grid/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik_grid/default/"""
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
                   template="http://wmts1/tiles/1.0.0/mapnik_grid_drop/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/mapnik_grid_drop/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.json" />
      <ResourceURL format="application/utfgrid" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/mapnik_grid_drop/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_hash/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_hash/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_hash/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_hash_no_meta/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_hash_no_meta/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_hash_no_meta/default/"""
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
                   template="http://wmts1/tiles/1.0.0/point_px_buffer/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/point_px_buffer/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/point_px_buffer/default/"""
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
                   template="http://wmts1/tiles/1.0.0/polygon/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/polygon/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/polygon/default/"""
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
                   template="http://wmts1/tiles/1.0.0/polygon2/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts2/tiles/1.0.0/polygon2/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <ResourceURL format="image/png" resourceType="tile"
                   template="http://wmts3/tiles/1.0.0/polygon2/default/"""
        """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_01</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_01</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>3571.4285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>1875</MatrixWidth>
        <MatrixHeight>1250</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>0_2</ows:Identifier>
        <ScaleDenominator>714.28571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>9375</MatrixWidth>
        <MatrixHeight>6250</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>0_1</ows:Identifier>
        <ScaleDenominator>357.14285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>18750</MatrixWidth>
        <MatrixHeight>12500</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_025</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0_25</ows:Identifier>
        <ScaleDenominator>892.85714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>7500</MatrixWidth>
        <MatrixHeight>5000</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_2_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>2_5</ows:Identifier>
        <ScaleDenominator>8928.5714285[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>750</MatrixWidth>
        <MatrixHeight>500</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_5</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.42857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.142857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>"""
    )

    @pytest.mark.asyncio
    async def test_multi_host_capabilities(self) -> None:
        gene = TileGeneration(Path("tilegeneration/test-fix.yaml"), configure_logging=False)
        self.assert_result_equals(
            await controller.get_wmts_capabilities(gene, "multi_host"), self.MULTIHOST_CAPABILITIES, True
        )

    @pytest.mark.asyncio
    async def test_capabilities_slash(self) -> None:
        gene = TileGeneration(Path("tilegeneration/test-capabilities.yaml"), configure_logging=False)
        config = gene.get_config(Path("tilegeneration/test-capabilities.yaml"))
        self.assert_result_equals(
            await controller.get_wmts_capabilities(gene, config.config["generation"]["default_cache"]),
            r"""<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0"
    xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
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
                   template="http://wmts1/tiles/1.0.0/no_dim/default/"""
            """{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
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
                   template="http://wmts1/tiles/1.0.0/one/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
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
                   template="http://wmts1/tiles/1.0.0/two/default/"""
            """{DATE}/{LEVEL}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>""",
            True,
        )

    @pytest.mark.asyncio
    async def test_multi_url_capabilities(self) -> None:
        gene = TileGeneration(Path("tilegeneration/test-fix.yaml"), configure_logging=False)
        self.assert_result_equals(
            await controller.get_wmts_capabilities(gene, "multi_url"), self.MULTIHOST_CAPABILITIES, True
        )

    CONFIG = """
caches:
  local:
    folder: /tmp/tiles
    http_url: http://wmts1/tiles/
    type: filesystem
    wmtscapabilities_file: 1.0.0/WMTSCapabilities.xml
  mbtiles:
    folder: /tmp/tiles/mbtiles
    http_url: http://wmts1/tiles/
    type: mbtiles
  multi_host:
    folder: /tmp/tiles
    hosts:
    - wmts1
    - wmts2
    - wmts3
    http_url: http://%(host)s/tiles/
    type: filesystem
  multi_url:
    folder: /tmp/tiles
    http_urls:
    - http://wmts1/tiles/
    - http://wmts2/tiles/
    - http://wmts3/tiles/
    type: filesystem
  s3:
    bucket: tiles
    cache_control: public, max-age=14400
    folder: tiles
    host: s3-eu-west-1.amazonaws.com
    http_url: https://%(host)s/%(bucket)s/%(folder)s/
    type: s3
cost:
  cloudfront: {}
  request_per_layers: 10000000
  s3: {}
  sqs: {}
generation:
  default_cache: local
  default_layers:
  - line
  - polygon
  error_file: error.list
  maxconsecutive_errors: 2
grids:
  swissgrid_01:
    bbox:
    - 420000
    - 30000
    - 900000
    - 350000
    matrix_identifier: resolution
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel
      +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 10
    resolutions:
    - 1
    - 0.2
    - 0.1
    srs: EPSG:21781
    tile_size: 256
  swissgrid_025:
    bbox:
    - 420000
    - 30000
    - 900000
    - 350000
    matrix_identifier: resolution
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel
      +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 4
    resolutions:
    - 0.25
    srs: EPSG:21781
    tile_size: 256
  swissgrid_2_5:
    bbox:
    - 420000
    - 30000
    - 900000
    - 350000
    matrix_identifier: resolution
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel
      +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 2
    resolutions:
    - 2.5
    srs: EPSG:21781
    tile_size: 256
  swissgrid_5:
    bbox:
    - 420000
    - 30000
    - 900000
    - 350000
    proj4_literal: +proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=600000 +y_0=200000 +ellps=bessel
      +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs
    resolution_scale: 1
    resolutions:
    - 100
    - 50
    - 20
    - 10
    - 5
    srs: EPSG:21781
    tile_size: 256
layers:
  all:
    bbox:
    - 550000.0
    - 170000.0
    - 560000.0
    - 180000.0
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    extension: png
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: point,line,polygon
    meta: false
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  line:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_metatile_detection:
      hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
      size: 20743
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.line
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache
    layers: line
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    params:
      PARAM: value
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  mapnik:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    data_buffer: 128
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.polygon
    grids: [swissgrid_5]
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    output_format: png
    type: mapnik
    wmts_style: default
  mapnik_grid:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    data_buffer: 128
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    extension: json
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.polygon
    grids: [swissgrid_5]
    layers_fields:
      line:
      - name
      point:
      - name
      polygon:
      - name
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 128
    meta_size: 8
    mime_type: application/utfgrid
    output_format: grid
    resolution: 16
    type: mapnik
    wmts_style: default
  mapnik_grid_drop:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    data_buffer: 128
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    drop_empty_utfgrid: true
    extension: json
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.polygon
    grids: [swissgrid_5]
    layers_fields:
      point:
      - name
    mapfile: mapfile/test.mapnik
    meta: false
    meta_buffer: 0
    meta_size: 8
    mime_type: application/utfgrid
    output_format: grid
    resolution: 16
    type: mapnik
    wmts_style: default
  point:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.point
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: point
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    min_resolution_seed: 10
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  point_hash:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_metatile_detection:
      hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
      size: 20743
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.point
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: point
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    min_resolution_seed: 10
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  point_hash_no_meta:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: point
    meta: false
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  point_px_buffer:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_metatile_detection:
      hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
      size: 20743
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.point
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: point
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    px_buffer: 100
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  polygon:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_metatile_detection:
      hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
      size: 20743
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.polygon
    grids: [swissgrid_5]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: polygon
    meta: false
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
  polygon2:
    cost:
      metatile_generation_time: 30
      tile_generation_time: 30
      tile_size: 20
      tileonly_generation_time: 60
    dimensions:
    - default: '2012'
      generate:
      - '2012'
      name: DATE
      values:
      - '2005'
      - '2010'
      - '2012'
    empty_metatile_detection:
      hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
      size: 20743
    empty_tile_detection:
      hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
      size: 334
    extension: png
    geoms:
    - connection: user=postgresql password=postgresql dbname=tests host=db
      sql: the_geom AS geom FROM tests.polygon
    grids: [swissgrid_01]
    headers:
      Cache-Control: no-cache, no-store
      Pragma: no-cache
    layers: polygon
    meta: true
    meta_buffer: 128
    meta_size: 8
    mime_type: image/png
    type: wms
    url: http://mapserver:8080/
    wmts_style: default
metadata:
  abstract: Some abstract
  access_constraints: None
  fees: None
  keywords:
  - some
  - keywords
  title: Some title
openlayers:
  center_x: 600000
  center_y: 200000
  srs: EPSG:21781
provider:
  contact:
    info:
      address:
        area: BE
        city: Berne
        country: Switzerland
        delivery: Address delivery
        email: info@example.com
        postal_code: 3000
      phone:
        fax: +41 11 222 33 44
        voice: +41 11 222 33 44
    name: The contact name
    position: The position name
  name: The provider name
  url: The provider URL
sns:
  region: eu-west-1
  topic: arn:aws:sns:eu-west-1:your-account-id:tilecloud
sqs:
  queue: sqs_point
    """

    def test_config(self) -> None:
        self.assert_cmd_yaml_equals(
            cmd=".build/venv/bin/generate-controller --dump-config -c tilegeneration/test-fix.yaml",
            main_func=controller.main,
            expected=self.CONFIG,
        )

    def test_config_line(self) -> None:
        self.assert_cmd_yaml_equals(
            cmd=".build/venv/bin/generate-controller -l line --dump-config -c tilegeneration/test-fix.yaml",
            main_func=controller.main,
            expected=self.CONFIG,
        )

    def test_quote(self) -> None:
        from tilecloud_chain import quote

        assert quote("abc") == "abc"
        assert quote("a b c") == "'a b c'"
        assert quote("'a b c'") == "\"'a b c'\""
        assert quote('"a b c"') == "'\"a b c\"'"
        assert quote("a\" b' c") == "'a\" b\\' c'"
        assert quote("a'bc") == '"a\'bc"'
        assert quote("a'b\"c") == "'a\\'b\"c'"
        assert quote('ab"c') == "'ab\"c'"
        assert quote("") == "''"

    def test_generate_legend_images(self) -> None:
        self.assert_tiles_generated(
            cmd=".build/venv/bin/generate-controler -c tilegeneration/test-legends.yaml --generate-legend-images",
            main_func=controller.main,
            directory="/tmp/tiles/1.0.0/",
            tiles_pattern="%s/default/%s",
            tiles=[
                ("point", "legend.yaml"),
                ("point", "legend-5.png"),
                ("line", "legend.yaml"),
                ("line", "legend-5.png"),
                ("line", "legend-50.png"),
                ("polygon", "legend.yaml"),
                ("polygon", "legend-5.png"),
                ("all", "legend.yaml"),
                ("all", "legend-5.png"),
                ("all", "legend-50.png"),
            ],
        )

        im = Image.open("/tmp/tiles/1.0.0/point/default/legend-5.png")
        assert im.size == (64, 20)
        im = Image.open("/tmp/tiles/1.0.0/line/default/legend-5.png")
        assert im.size == (71, 35)
        im = Image.open("/tmp/tiles/1.0.0/line/default/legend-50.png")
        assert im.size == (71, 35)
        im = Image.open("/tmp/tiles/1.0.0/polygon/default/legend-5.png")
        assert im.size == (81, 23)
        im = Image.open("/tmp/tiles/1.0.0/all/default/legend-5.png")
        assert im.size == (81, 78)
        im = Image.open("/tmp/tiles/1.0.0/all/default/legend-50.png")
        assert im.size == (81, 78)

        for layer, result in (
            (
                "point",
                {
                    "metadata": [
                        {
                            "height": 20,
                            "mime_type": "image/png",
                            "path": "1.0.0/point/default/legend-5.png",
                            "width": 64,
                        },
                    ]
                },
            ),
            (
                "line",
                {
                    "metadata": [
                        {
                            "height": 35,
                            "mime_type": "image/png",
                            "min_resolution": 15.811388300841893,
                            "path": "1.0.0/line/default/legend-5.png",
                            "width": 71,
                        },
                        {
                            "height": 35,
                            "max_resolution": 15.811388300841893,
                            "mime_type": "image/png",
                            "path": "1.0.0/line/default/legend-50.png",
                            "width": 71,
                        },
                    ]
                },
            ),
            (
                "polygon",
                {
                    "metadata": [
                        {
                            "height": 23,
                            "mime_type": "image/png",
                            "path": "1.0.0/polygon/default/legend-5.png",
                            "width": 81,
                        },
                    ]
                },
            ),
            (
                "all",
                {
                    "metadata": [
                        {
                            "height": 78,
                            "mime_type": "image/png",
                            "min_resolution": 15.811388300841893,
                            "path": "1.0.0/all/default/legend-5.png",
                            "width": 81,
                        },
                        {
                            "height": 78,
                            "max_resolution": 15.811388300841893,
                            "mime_type": "image/png",
                            "path": "1.0.0/all/default/legend-50.png",
                            "width": 81,
                        },
                    ]
                },
            ),
        ):
            with pytest_check.check:
                # Check that legend files were created
                assert os.path.exists(f"/tmp/tiles/1.0.0/{layer}/default/legend.yaml")
                with open(f"/tmp/tiles/1.0.0/{layer}/default/legend.yaml", encoding="utf-8") as legend_file:
                    legend_metadata = yaml.safe_load(legend_file)
                    assert legend_metadata == result

    @pytest.mark.asyncio
    async def test_legends(self) -> None:
        self.assert_tiles_generated(
            cmd=".build/venv/bin/generate-controler -c tilegeneration/test-legends.yaml --legends",
            main_func=controller.main,
            directory="/tmp/tiles/1.0.0/",
            tiles_pattern="%s/default/legend%i.png",
            tiles=[("point", 0), ("line", 0), ("line", 2), ("polygon", 0), ("all", 0), ("all", 2)],
        )

        gene = TileGeneration(Path("tilegeneration/test-legends.yaml"), configure_logging=False)
        config = gene.get_config(Path("tilegeneration/test-legends.yaml"))
        self.assert_result_equals(
            await controller.get_wmts_capabilities(gene, config.config["generation"]["default_cache"]),
            r"""<\?xml version="1.0" encoding="UTF-8"\?>
<Capabilities version="1.0.0"
    xmlns="http://www.opengis.net/wmts/1.0"
    xmlns:ows="http://www.opengis.net/ows/1.1"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:gml="http://www.opengis.net/gml"
    xsi:schemaLocation="http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd">
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
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/all/default/legend0.png" """
            """width="[0-9]*" height="[0-9]*" minScaleDenominator="112938.48786[0-9]*" />
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/all/default/legend2.png" """
            """width="[0-9]*" height="[0-9]*" maxScaleDenominator="112938.48786[0-9]*" />
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
                   template="http://wmts1/tiles/1.0.0/all/default/"""
            r"""{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>line</ows:Title>
      <ows:Identifier>line</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/line/default/legend0.png" """
            r"""width="[0-9]*" height="[0-9]*" minScaleDenominator="112938.48786[0-9]*" />
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/line/default/legend2.png" """
            r"""width="[0-9]*" height="[0-9]*" maxScaleDenominator="112938.48786[0-9]*" />
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
                   template="http://wmts1/tiles/1.0.0/line/default/"""
            r"""{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>point</ows:Title>
      <ows:Identifier>point</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/point/default/legend0.png" """
            """width="[0-9]*" height="[0-9]*" />
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
                   template="http://wmts1/tiles/1.0.0/point/default/"""
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
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/polygon/default/legend0.png" """
            """width="[0-9]*" height="[0-9]*" />
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
                   template="http://wmts1/tiles/1.0.0/polygon/default/"""
            """{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>357142.85714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>178571.42857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>71428.571428[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>35714.285714[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>17857.142857[0-9]*</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>""",
            True,
        )
