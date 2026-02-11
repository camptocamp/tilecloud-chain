import os
import shutil
from anyio import Path

import pytest
import yaml
from fastapi import HTTPException
from testfixtures import LogCapture

from tilecloud_chain import DatedConfig, generate, server
from tilecloud_chain.tests import CompareCase

_CAPABILITIES = (
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
                   template="http://wmts1/tiles/wmts/1.0.0/point_hash/default/{DATE}/"""
    r"""{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_5</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



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


class TestServe(CompareCase):
    def setUp(self) -> None:
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):
        os.chdir(Path(__file__).parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")

    @classmethod
    def tearDownClass(cls):
        os.chdir(Path(__file__).parent.parent.parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")

    @pytest.mark.asyncio
    async def test_serve_kvp(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-nosns.yaml "
                "--layer=point_hash --zoom 1",
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/%s",
                tiles=[
                    ("point_hash/default/2012/swissgrid_5/1/11/14.png"),
                    ("point_hash/default/2012/swissgrid_5/1/15/8.png"),
                ],
                regex=True,
                expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
  Nb generated metatiles: 1
  Nb metatiles dropped: 0
  Nb generated tiles: 64
  Nb tiles dropped: 62
  Nb tiles stored: 2
  Nb tiles in error: 0
  Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
  Total size: [89][0-9][0-9] o
  Time per tile: [0-9]+ ms
  Size per tile: 4[0-9][0-9] o

  """,
            )

            server._PYRAMID_SERVER = None
            server._TILEGENERATION = None
            with Path("tilegeneration/test-nosns.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-nosns.yaml").stat().st_mtime,
                    filename="tilegeneration/test-nosns.yaml",
                )
            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetTile",
                "Format": "image/png",
                "Layer": "point_hash",
                "Style": "default",
                "TileMatrixSet": "swissgrid_5",
                "TileMatrix": "1",
                "TileRow": "11",
                "TileCol": "14",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TileRow"] = "12"
            response = await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 204

            params["TileRow"] = "11"
            params["Service"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Service"] = "WMTS"
            params["Request"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Request"] = "GetTile"
            params["Version"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Version"] = "1.0.0"
            params["Format"] = "image/jpeg"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Format"] = "image/png"
            params["Layer"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Layer"] = "point_hash"
            params["Style"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Style"] = "default"
            params["TileMatrixSet"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["TileMatrixSet"] = "swissgrid_5"
            del params["Service"]
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                regex=True,
                expected=r"""<\?xml version="1.0" encoding="UTF-8"\?>
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
        <ows:Title>point_webp</ows:Title>
        <ows:Identifier>point_webp</ows:Identifier>
        <Style isDefault="true">
          <ows:Identifier>default</ows:Identifier>
        </Style>
        <Format>image/webp</Format>
        <Dimension>
          <ows:Identifier>DATE</ows:Identifier>
          <Default>2012</Default>
          <Value>2005</Value>
          <Value>2010</Value>
          <Value>2012</Value>
        </Dimension>
        <ResourceURL format="image/webp" resourceType="tile"
                     template="http://wmts1/tiles/wmts/1.0.0/point_webp/default/{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.webp" />
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
            )

            log_capture.check()

    @pytest.mark.asyncio
    async def test_mbtiles_rest(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-serve.yaml"
                " --layer=point_hash --zoom 1",
                main_func=generate.main,
                directory="/tmp/tiles/mbtiles/",
                tiles_pattern="1.0.0/%s",
                tiles=[("point_hash/default/2012/swissgrid_5.png.mbtiles")],
                regex=True,
                expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
  Nb generated metatiles: 1
  Nb metatiles dropped: 0
  Nb generated tiles: 64
  Nb tiles dropped: 62
  Nb tiles stored: 2
  Nb tiles in error: 0
  Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
  Total size: [89][0-9][0-9] o
  Time per tile: [0-9]+ ms
  Size per tile: 4[0-9][0-9] o

  """,
            )

            server._PYRAMID_SERVER = None
            server._TILEGENERATION = None
            with Path("tilegeneration/test-serve.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                    file="tilegeneration/test-serve.yaml",
                )
            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetTile",
                "Format": "image/png",
                "Layer": "point_hash",
                "Style": "default",
                "TileMatrixSet": "swissgrid_5",
                "TileMatrix": "1",
                "TileRow": "11",
                "TileCol": "14",
                "Date": "2012",
            }

            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TileRow"] = "12"
            response = await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 204
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TileRow"] = "11"
            params["Version"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Version"] = "1.0.0"
            params["Format"] = "image/jpeg"
            params["TileCol"] = "14"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Format"] = "image/png"
            params["TileCol"] = "14"
            params["Layer"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Layer"] = "point_hash"
            params["Style"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Style"] = "default"
            params["TileMatrixSet"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetTile",
                "Format": "image/png",
                "Layer": "point_hash",
                "Style": "default",
                "TileMatrixSet": "swissgrid_5",
                "TileMatrix": "1",
                "TileRow": "11",
                "TileCol": "14",
            }
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )

            log_capture.check()

    @pytest.mark.skip(reason="Don't test bsddb")
    @pytest.mark.asyncio
    async def test_bsddb_rest(self):
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-bsddb.yaml"
                " --layer=point_hash --zoom=1",
                main_func=generate.main,
                directory="/tmp/tiles/bsddb/",
                tiles_pattern="1.0.0/%s",
                tiles=[("point_hash/default/2012/swissgrid_5.png.bsddb")],
                regex=True,
                expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
  Nb generated metatiles: 1
  Nb metatiles dropped: 0
  Nb generated tiles: 64
  Nb tiles dropped: 62
  Nb tiles stored: 2
  Nb tiles in error: 0
  Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
  Total size: [89][0-9][0-9] o
  Time per tile: [0-9]+ ms
  Size per tile: 4[0-9][0-9] o

  """,
            )

            server._PYRAMID_SERVER = None
            server._TILEGENERATION = None

            with Path("tilegeneration/test-bsddb.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-bsddb.yaml").stat().st_mtime,
                    filename="tilegeneration/test-bsddb.yaml",
                )
            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetTile",
                "Format": "image/png",
                "Layer": "point_hash",
                "Style": "default",
                "Date": "2012",
                "TileMatrixSet": "swissgrid_5",
                "TileMatrix": "1",
                "TileRow": "11",
                "TileCol": "14",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TileRow"] = "12"
            response = await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 204

            params["TileRow"] = "11"
            params["Version"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Version"] = "1.0.0"
            params["Format"] = "image/jpeg"
            params["TileCol"] = "14"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Format"] = "image/png"
            params["TileCol"] = "14"
            params["Layer"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Layer"] = "point_hash"
            params["Style"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params["Style"] = "default"
            params["TileMatrixSet"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetTile",
                "Format": "image/png",
                "Layer": "point_hash",
                "Style": "default",
                "TileMatrixSet": "swissgrid_5",
                "TileMatrix": "1",
                "TileRow": "11",
                "TileCol": "14",
            }
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 400

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )

            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )

            log_capture.check()

    @pytest.mark.asyncio
    async def test_serve_gfi(self) -> None:
        server._PYRAMID_SERVER = None
        server._TILEGENERATION = None

        with Path("tilegeneration/test-serve.yaml").open() as f:
            config = DatedConfig(
                config=yaml.safe_load(f),
                mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                filename="tilegeneration/test-serve.yaml",
            )
        params = {
            "Service": "WMTS",
            "Version": "1.0.0",
            "Request": "GetFeatureInfo",
            "Format": "image/png",
            "Info_Format": "application/vnd.ogc.gml",
            "Layer": "point_hash",
            "Query_Layer": "point_hash",
            "Style": "default",
            "TileMatrixSet": "swissgrid_5",
            "TileMatrix": "1",
            "TileRow": "11",
            "TileCol": "14",
            "I": "114",
            "J": "111",
        }
        response = await server.server.serve(params, config, "localhost", None)
        self.assert_result_equals(
            response.body.decode("utf-8"),
            """<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""",
        )

        server._PYRAMID_SERVER = None
        server._TILEGENERATION = None

        with Path("tilegeneration/test-serve.yaml").open() as f:
            config = DatedConfig(
                config=yaml.safe_load(f),
                mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                filename="tilegeneration/test-serve.yaml",
            )
        params = {
            "Service": "WMTS",
            "Version": "1.0.0",
            "Request": "GetFeatureInfo",
            "Format": "image/png",
            "Info_Format": "application/vnd.ogc.gml",
            "Layer": "point_hash",
            "Query_Layer": "point_hash",
            "Style": "default",
            "Date": "2012",
            "TileMatrixSet": "swissgrid_5",
            "TileMatrix": "1",
            "TileRow": "14",
            "TileCol": "11",
            "I": "114",
            "J": "111",
        }
        response = await server.server.serve(params, config, "localhost", None)
        self.assert_result_equals(
            response.body.decode("utf-8"),
            """<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""",
        )

    @pytest.mark.asyncio
    async def test_wsgi(self) -> None:
        self.assert_tiles_generated(
            cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-serve.yaml --layer=point_hash --zoom 1",
            main_func=generate.main,
            directory="/tmp/tiles/mbtiles/",
            tiles_pattern="1.0.0/%s",
            tiles=[("point_hash/default/2012/swissgrid_5.png.mbtiles")],
            regex=True,
            expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 64
Nb tiles dropped: 62
Nb tiles stored: 2
Nb tiles in error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tile: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
        )

        server._PYRAMID_SERVER = None
        server._TILEGENERATION = None

        global code, headers  # noqa: PLW0603
        code = None
        headers = None

        def start_response(p_code, p_headers):
            global code, headers  # noqa: PLW0603
            code = p_code
            headers = {}
            for key, value in p_headers:
                headers[key] = value

        result = await server.server.serve(
            await server._TILEGENERATION.get_main_config(),
            "tilegeneration/test-serve.yaml",
            {
                "QUERY_STRING": "&".join(
                    [
                        "{}={}".format(*item)
                        for item in {
                            "Service": "WMTS",
                            "Version": "1.0.0",
                            "Request": "GetFeatureInfo",
                            "Format": "image/png",
                            "Info_Format": "application/vnd.ogc.gml",
                            "Layer": "point_hash",
                            "Query_Layer": "point_hash",
                            "Style": "default",
                            "TileMatrixSet": "swissgrid_5",
                            "TileMatrix": "1",
                            "TileRow": "11",
                            "TileCol": "14",
                            "I": "114",
                            "J": "111",
                        }.items()
                    ],
                ),
            },
            start_response,
        )
        assert code == "200 OK"
        self.assert_result_equals(
            result[0].decode("utf-8"),
            """<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""",
        )

        result = await server.server.serve(
            await server._TILEGENERATION.get_main_config(),
            "tilegeneration/test-serve.yaml",
            {
                "QUERY_STRING": "",
                "PATH_INFO": "/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/14/11/114/111.xml",
            },
            start_response,
        )
        self.assert_result_equals(
            result[0].decode("utf-8"),
            """<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""",
        )

        await server.server.serve(
            await server._TILEGENERATION.get_main_config(),
            "tilegeneration/test-serve.yaml",
            {"QUERY_STRING": "", "PATH_INFO": "/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/11/12.png"},
            start_response,
        )
        assert code == "204 No Content"

        await server.server.serve(
            await server._TILEGENERATION.get_main_config(),
            "tilegeneration/test-serve.yaml",
            {"QUERY_STRING": "", "PATH_INFO": "/wmts/1.0.0/point_hash/default/2012/swissgrid_5/1/11/14.png"},
            start_response,
        )
        assert code == "200 OK"
        assert headers["Cache-Control"] == "max-age=28800"

        result = await server.server.serve(
            await server._TILEGENERATION.get_main_config(),
            "tilegeneration/test-serve.yaml",
            {"QUERY_STRING": "", "PATH_INFO": "/wmts/1.0.0/WMTSCapabilities.xml"},
            start_response,
        )
        assert code == "200 OK"
        self.assert_result_equals(
            result[0].decode("utf-8"),
            _CAPABILITIES,
            regex=True,
        )

    @pytest.mark.asyncio
    async def test_ondemend_wmtscapabilities(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            server._PYRAMID_SERVER = None
            server._TILEGENERATION = None

            with Path("tilegeneration/test-serve-wmtscapabilities.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-serve-wmtscapabilities.yaml").stat().st_mtime,
                    filename="tilegeneration/test-serve-wmtscapabilities.yaml",
                )
            params = {
                "Service": "WMTS",
                "Version": "1.0.0",
                "Request": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )
            log_capture.check()
