import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from anyio import Path as AnyioPath
from fastapi import HTTPException
from testfixtures import LogCapture

from tilecloud_chain import DatedConfig, TileGeneration, generate, server
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
          <ows:Get xlink:href="http://wmts1/tiles/1.0.0/WMTSCapabilities.xml">
            <ows:Constraint name="GetEncoding">
              <ows:AllowedValues>
                <ows:Value>REST</ows:Value>
              </ows:AllowedValues>
            </ows:Constraint>
          </ows:Get>
          <ows:Get xlink:href="http://wmts1/tiles/">
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
          <ows:Get xlink:href="http://wmts1/tiles/">
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
                   template="http://wmts1/tiles/1.0.0/point_hash/default/{DATE}/"""
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
    def setup_method(self) -> None:
        self.maxDiff = None

    @classmethod
    def setup_class(cls):
        os.chdir(Path(__file__).parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")

    @classmethod
    def teardown_class(cls):
        os.chdir(Path(__file__).parent.parent.parent)
        if Path("/tmp/tiles").exists():
            shutil.rmtree("/tmp/tiles")

    @pytest.mark.asyncio
    async def test_serve_kvp(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            await self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-nosns.yaml "
                "--layer=point_hash --zoom 1",
                main_func=generate.async_main,
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
            server._TILEGENERATION = TileGeneration(
                config_file=AnyioPath("tilegeneration/test-nosns.yaml"),
                configure_logging=False,
            )
            with Path("tilegeneration/test-nosns.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-nosns.yaml").stat().st_mtime,
                    file=AnyioPath("tilegeneration/test-nosns.yaml"),
                )
            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetTile",
                "FORMAT": "image/png",
                "LAYER": "point_hash",
                "STYLE": "default",
                "TILEMATRIXSET": "swissgrid_5",
                "TILEMATRIX": "1",
                "TILEROW": "11",
                "TILECOL": "14",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TILEROW"] = "12"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 204

            params["TILEROW"] = "11"
            params["SERVICE"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["SERVICE"] = "WMTS"
            params["REQUEST"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["REQUEST"] = "GetTile"
            params["VERSION"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["VERSION"] = "1.0.0"
            params["FORMAT"] = "image/jpeg"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["FORMAT"] = "image/png"
            params["LAYER"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["LAYER"] = "point_hash"
            params["STYLE"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["STYLE"] = "default"
            params["TILEMATRIXSET"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCapabilities",
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
            <ows:Get xlink:href="http://wmts1/tiles/1.0.0/WMTSCapabilities.xml">
              <ows:Constraint name="GetEncoding">
                <ows:AllowedValues>
                  <ows:Value>REST</ows:Value>
                </ows:AllowedValues>
              </ows:Constraint>
            </ows:Get>
            <ows:Get xlink:href="http://wmts1/tiles/">
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
            <ows:Get xlink:href="http://wmts1/tiles/">
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
                    template="http://wmts1/tiles/1.0.0/point_error/default/"""
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
                     template="http://wmts1/tiles/1.0.0/point_webp/default/{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.webp" />
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
            )

            log_capture.check()

    @pytest.mark.asyncio
    async def test_mbtiles_rest(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            await self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-serve.yaml"
                " --layer=point_hash --zoom 1",
                main_func=generate.async_main,
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
            server._TILEGENERATION = TileGeneration(
                config_file=AnyioPath("tilegeneration/test-serve.yaml"),
                configure_logging=False,
            )
            with Path("tilegeneration/test-serve.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                    file=AnyioPath("tilegeneration/test-serve.yaml"),
                )
            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetTile",
                "FORMAT": "image/png",
                "LAYER": "point_hash",
                "STYLE": "default",
                "TILEMATRIXSET": "swissgrid_5",
                "TILEMATRIX": "1",
                "TILEROW": "11",
                "TILECOL": "14",
                "DATE": "2012",
            }

            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TILEROW"] = "12"

            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 204
            assert response.value.headers["Cache-Control"] == "max-age=28800"

            params["TILEROW"] = "11"
            params["VERSION"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["VERSION"] = "1.0.0"
            params["FORMAT"] = "image/jpeg"
            params["TILECOL"] = "14"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["FORMAT"] = "image/png"
            params["TILECOL"] = "14"
            params["LAYER"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["LAYER"] = "point_hash"
            params["STYLE"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["STYLE"] = "default"
            params["TILEMATRIXSET"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCapabilities",
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
            await self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --config=tilegeneration/test-bsddb.yaml"
                " --layer=point_hash --zoom=1",
                main_func=generate.async_main,
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
            server._TILEGENERATION = TileGeneration(
                config_file=AnyioPath("tilegeneration/test-bsddb.yaml"),
                configure_logging=False,
            )

            with Path("tilegeneration/test-bsddb.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-bsddb.yaml").stat().st_mtime,
                    file=AnyioPath("tilegeneration/test-bsddb.yaml"),
                )
            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetTile",
                "FORMAT": "image/png",
                "LAYER": "point_hash",
                "STYLE": "default",
                "DATE": "2012",
                "TILEMATRIXSET": "swissgrid_5",
                "TILEMATRIX": "1",
                "TILEROW": "11",
                "TILECOL": "14",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "image/png"
            assert response.headers["Cache-Control"] == "max-age=28800"

            params["TILEROW"] = "12"
            response = await server.server.serve(params, config, "localhost", None)
            assert response.status_code == 204

            params["TILEROW"] = "11"
            params["VERSION"] = "0.9"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["VERSION"] = "1.0.0"
            params["FORMAT"] = "image/jpeg"
            params["TILECOL"] = "14"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["FORMAT"] = "image/png"
            params["TILECOL"] = "14"
            params["LAYER"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["LAYER"] = "point_hash"
            params["STYLE"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params["STYLE"] = "default"
            params["TILEMATRIXSET"] = "test"
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetTile",
                "FORMAT": "image/png",
                "LAYER": "point_hash",
                "STYLE": "default",
                "TILEMATRIXSET": "swissgrid_5",
                "TILEMATRIX": "1",
                "TILEROW": "11",
                "TILECOL": "14",
            }
            with pytest.raises(HTTPException) as response:
                await server.server.serve(params, config, "localhost", None)
            assert response.value.status_code == 400

            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )

            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCapabilities",
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
        server._TILEGENERATION = TileGeneration(
            config_file=AnyioPath("tilegeneration/test-serve.yaml"),
            configure_logging=False,
        )

        with Path("tilegeneration/test-serve.yaml").open() as f:
            config = DatedConfig(
                config=yaml.safe_load(f),
                mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                file=AnyioPath("tilegeneration/test-serve.yaml"),
            )
        params = {
            "SERVICE": "WMTS",
            "VERSION": "1.0.0",
            "REQUEST": "GetFeatureInfo",
            "FORMAT": "image/png",
            "INFO_FORMAT": "application/vnd.ogc.gml",
            "LAYER": "point_hash",
            "QUERY_LAYER": "point_hash",
            "STYLE": "default",
            "TILEMATRIXSET": "swissgrid_5",
            "TILEMATRIX": "1",
            "TILEROW": "11",
            "TILECOL": "14",
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
        server._TILEGENERATION = TileGeneration(
            config_file=AnyioPath("tilegeneration/test-serve.yaml"),
            configure_logging=False,
        )

        with Path("tilegeneration/test-serve.yaml").open() as f:
            config = DatedConfig(
                config=yaml.safe_load(f),
                mtime=Path("tilegeneration/test-serve.yaml").stat().st_mtime,
                file=AnyioPath("tilegeneration/test-serve.yaml"),
            )
        params = {
            "SERVICE": "WMTS",
            "VERSION": "1.0.0",
            "REQUEST": "GetFeatureInfo",
            "FORMAT": "image/png",
            "INFO_FORMAT": "application/vnd.ogc.gml",
            "LAYER": "point_hash",
            "QUERY_LAYER": "point_hash",
            "STYLE": "default",
            "DATE": "2012",
            "TILEMATRIXSET": "swissgrid_5",
            "TILEMATRIX": "1",
            "TILEROW": "14",
            "TILECOL": "11",
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
    async def test_rest_integration(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tilecloud_chain.server import router

        server._PYRAMID_SERVER = None
        server.server.store_cache = {}
        server._TILEGENERATION = TileGeneration(
            config_file=AnyioPath("tilegeneration/test-serve.yaml"),
            configure_logging=False,
        )

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        async def get_one_side_effect(tile):
            if tile.tilecoord.z == 1 and tile.tilecoord.x == 14 and tile.tilecoord.y == 11:
                t = MagicMock()
                t.data = b"dummy_png"
                t.content_type = "image/png"
                t.error = None
                return t
            return None

        with (
            patch("aiohttp.ClientSession.get") as mock_get,
            patch("tilecloud_chain.IntersectGeometryFilter.filter_tilecoord", return_value=True),
            patch.object(server._TILEGENERATION, "get_store", new_callable=AsyncMock) as mock_get_store,
        ):
            # Mock the store
            mock_store = AsyncMock()
            mock_store.get_one.side_effect = get_one_side_effect
            mock_get_store.return_value = mock_store

            # Mock the response context manager
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = b"""<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
"""
            mock_response.headers = {"Content-Type": "application/xml"}
            mock_get.return_value.__aenter__.return_value = mock_response

            # 1. GetFeatureInfo
            response = client.get(
                "/tiles/1.0.0/point_hash/default/2012/swissgrid_5/1/11/14/114/111.xml",
                params={
                    "Info_Format": "application/vnd.ogc.gml",
                },
            )
            assert response.status_code == 200, response.text
            self.assert_result_equals(
                response.text,
                """<?xml version="1.0" encoding="UTF-8"?>

<msGMLOutput
    xmlns:gml="http://www.opengis.net/gml"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</msGMLOutput>
""",
            )

            # 2. GetTile (204 No Content)
            # Row 12 -> TMS Row 12 (if height 25).
            # We inserted Row 13 (WMTS 11). So WMTS 12 (TMS 12) should be empty.
            response = client.get("/tiles/1.0.0/point_hash/default/2012/swissgrid_5/1/11/12.png")
            assert response.status_code == 204

            # 3. GetTile (200 OK)
            # Row 11 -> TMS Row 13.
            response = client.get("/tiles/1.0.0/point_hash/default/2012/swissgrid_5/1/11/14.png")
            assert response.status_code == 200
            assert response.headers["Cache-Control"] == "max-age=28800"
            assert response.headers["Content-Type"] == "image/png"

            # 4. GetTile with wrong dimensions (empty value)
            response = client.get("/tiles/1.0.0/point_hash/default//swissgrid_5/1/11/14.png")
            assert response.status_code == 400
            assert response.json()["detail"] == (
                "Wrong dimensions for layer 'point_hash': empty value(s) for dimension(s): DATE"
            )

            # 5. GetTile with wrong dimensions (extra value)
            response = client.get("/tiles/1.0.0/point_hash/default/2012/extra/swissgrid_5/1/11/14.png")
            assert response.status_code == 400
            assert response.json()["detail"] == (
                "Wrong dimensions for layer 'point_hash': expected 1 value(s) (DATE); "
                "got 2 value(s) (2012, extra); unexpected value(s): extra"
            )

            # 6. GetCapabilities
            response = client.get("/tiles/1.0.0/WMTSCapabilities.xml")
            assert response.status_code == 200
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.text,
                _CAPABILITIES,
                regex=True,
            )

    @pytest.mark.asyncio
    async def test_ondemend_wmtscapabilities(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            server._PYRAMID_SERVER = None
            server._TILEGENERATION = TileGeneration(
                config_file=AnyioPath("tilegeneration/test-serve-wmtscapabilities.yaml"),
                configure_logging=False,
            )

            with Path("tilegeneration/test-serve-wmtscapabilities.yaml").open() as f:
                config = DatedConfig(
                    config=yaml.safe_load(f),
                    mtime=Path("tilegeneration/test-serve-wmtscapabilities.yaml").stat().st_mtime,
                    file=AnyioPath("tilegeneration/test-serve-wmtscapabilities.yaml"),
                )
            params = {
                "SERVICE": "WMTS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCapabilities",
            }
            response = await server.server.serve(params, config, "localhost", None)
            assert response.headers["Content-Type"] == "application/xml"
            self.assert_result_equals(
                response.body.decode("utf-8"),
                _CAPABILITIES,
                regex=True,
            )
            log_capture.check()
