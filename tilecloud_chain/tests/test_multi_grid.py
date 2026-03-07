import os
from pathlib import Path

import pytest
import pytest_check
import yaml
from anyio import Path as AnyioPath

from tilecloud_chain import TileGeneration, controller, generate
from tilecloud_chain.tests import CompareCase


class TestMultiGrid(CompareCase):
    def setup_method(self) -> None:
        self.maxDiff = None

    @classmethod
    def setup_class(cls) -> None:
        os.chdir(Path(__file__).parent)

    @classmethod
    def teardown_class(cls) -> None:
        os.chdir(Path(__file__).parent.parent.parent)

    @pytest.mark.asyncio
    async def test_generate_all(self) -> None:
        """Test generating tiles for layer 'all'."""
        # This creates and checks tiles for the 'all' layer
        await self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
                "--zoom=0",
            ],
            main_func=generate.async_main,
            directory="/tmp/tiles/",
            tiles_pattern="1.0.0/all/default/2012/%s/%i/%i/%i.png",
            tiles=[
                ("swissgrid_2056", 0, 0, 0),
                ("swissgrid_2056", 0, 1, 0),
                ("swissgrid_2056", 0, 0, 1),
                ("swissgrid_2056", 0, 1, 1),
                ("swissgrid_21781", 0, 0, 0),
                ("swissgrid_21781", 0, 1, 0),
                ("swissgrid_21781", 0, 0, 1),
                ("swissgrid_21781", 0, 1, 1),
            ],
            regex=True,
            expected=r"""The tile generation of layer 'all \(DATE=2012\)' is finish
Nb generated metatiles: 2
Nb metatiles dropped: 0
Nb generated tiles: 8
Nb tiles dropped: 0
Nb tiles stored: 8
Nb tiles in error: 0
Total time: 0:00:[0-9]{2}
Total size: [0-9]\.[0-9] Kio
Time per tile: [0-9]{2} ms
Size per tile: [0-9]{3} o

""",
        )

    @pytest.mark.asyncio
    async def test_generate_one(self) -> None:
        """Test generating tiles for layer 'one' which has only one grid."""
        await self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=one",
                "--zoom=0",
            ],
            main_func=generate.async_main,
            directory="/tmp/tiles/",
            tiles_pattern="1.0.0/one/default/2012/%s/%i/%i/%i.png",
            tiles=[
                ("swissgrid_2056", 0, 0, 0),
                ("swissgrid_2056", 0, 1, 0),
                ("swissgrid_2056", 0, 0, 1),
                ("swissgrid_2056", 0, 1, 1),
            ],
            regex=True,
            expected=r"""The tile generation of layer 'one \(DATE=2012\)' is finish
Nb generated metatiles: 1
Nb metatiles dropped: 0
Nb generated tiles: 4
Nb tiles dropped: 0
Nb tiles stored: 4
Nb tiles in error: 0
Total time: 0:00:[0-9]{2}
Total size: [0-9]\.[0-9] Kio
Time per tile: [0-9]{2} ms
Size per tile: [0-9]{3} o

""",
        )

    @pytest.mark.asyncio
    async def test_generate_all_with_grid(self) -> None:
        """Test generating tiles for layer 'all' with --grid parameter."""
        for grid in ("swissgrid_2056", "swissgrid_21781"):
            with pytest_check.check:
                await self.assert_tiles_generated(
                    cmd=[
                        ".build/venv/bin/generate-tiles",
                        "-d",
                        "--config=tilegeneration/test-multi-grid.yaml",
                        "--layer=all",
                        f"--grid={grid}",
                        "--zoom=0",
                    ],
                    main_func=generate.async_main,
                    directory="/tmp/tiles/",
                    tiles_pattern=f"1.0.0/all/default/2012/{grid}/%i/%i/%i.png",
                    tiles=[
                        (0, 0, 0),
                        (0, 1, 0),
                        (0, 0, 1),
                        (0, 1, 1),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'all \(DATE=2012\)' is finish
        Nb generated metatiles: 1
        Nb metatiles dropped: 0
        Nb generated tiles: 4
        Nb tiles dropped: 0
        Nb tiles stored: 4
        Nb tiles in error: 0
        Total time: 0:00:[0-9]{2}
        Total size: [0-9]\.[0-9] Kio
        Time per tile: [0-9]{2} ms
        Size per tile: [0-9]{3} o

        """,
                )

    @pytest.mark.asyncio
    async def test_get_hash(self) -> None:
        """Test getting hash on layer 'all'."""
        await self.assert_cmd_equals(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--get-hash=4/0/0",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
                "--grid=swissgrid_21781",
            ],
            main_func=generate.async_main,
            expected="""Tile: 4/0/0:+2/+2 config_file=tilegeneration/test-multi-grid.yaml dimension_DATE=2012 grid=swissgrid_21781 host=localhost layer=all
      empty_metatile_detection:
          size: 2367
          hash: 645d394d3f0805f111ab2902dea3f3749c96cd7c
  Tile: 4/0/0 config_file=tilegeneration/test-multi-grid.yaml dimension_DATE=2012 grid=swissgrid_21781 host=localhost layer=all
      empty_tile_detection:
          size: 334
          hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
  """,
        )

    @pytest.mark.asyncio
    async def test_get_bbox_grid(self) -> None:
        """Test getting bbox on layer 'all'."""
        for grid, expected in (
            ("swissgrid_2056", "2420000,1094000,2676000,1350000"),
            ("swissgrid_21781", "420000,94000,676000,350000"),
        ):
            with pytest_check.check:
                await self.assert_cmd_equals(
                    cmd=[
                        ".build/venv/bin/generate-tiles",
                        "-d",
                        "--get-bbox=0/0/0",
                        "--config=tilegeneration/test-multi-grid.yaml",
                        "--layer=all",
                        f"--grid={grid}",
                    ],
                    main_func=generate.async_main,
                    expected=f"""Tile bounds: [{expected}]
        """,
                )

    @pytest.mark.asyncio
    async def test_generate_legend_all(self) -> None:
        """Test generating legend images for layer 'all'."""
        await self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-controller",
                "-d",
                "--legends",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
            ],
            main_func=controller.async_main,
            directory="/tmp/tiles/",
            tiles_pattern="1.0.0/%s/default/%s",
            tiles=[
                ("one", "legend.yaml"),
                ("one", "legend-5.png"),
                ("all", "legend.yaml"),
                ("all", "legend-5.png"),
            ],
        )
        # Check that legend files were created
        for layer, result in (
            (
                "one",
                {
                    "metadata": [
                        {
                            "path": "1.0.0/one/default/legend-5.png",
                            "mime_type": "image/png",
                            "height": 20,
                            "width": 64,
                        },
                    ],
                },
            ),
            (
                "all",
                {
                    "metadata": [
                        {
                            "path": "1.0.0/all/default/legend-5.png",
                            "mime_type": "image/png",
                            "height": 20,
                            "width": 64,
                        },
                    ],
                },
            ),
        ):
            with pytest_check.check:
                # Check that legend files were created
                legend_yaml_path = Path(f"/tmp/tiles/1.0.0/{layer}/default/legend.yaml")
                assert legend_yaml_path.exists()
                with legend_yaml_path.open(encoding="utf-8") as legend_file:
                    legend_metadata = yaml.safe_load(legend_file)
                    assert legend_metadata == result

    @pytest.mark.asyncio
    async def test_capabilities(self) -> None:
        """Test capabilities generation for the multi-grid config."""
        gene = TileGeneration(AnyioPath("tilegeneration/test-multi-grid.yaml"), configure_logging=False)
        await gene.ainit()
        config = await gene.get_config(AnyioPath("tilegeneration/test-multi-grid.yaml"))

        from tilecloud_chain.tests.test_controller import wmts_capabilities

        capabilities = await wmts_capabilities(gene, config.config["generation"]["default_cache"])

        assert capabilities == """<?xml version="1.0" encoding="UTF-8"?>
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
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/all/default/legend-5.png" width="64" height="20" />
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
                   template="http://wmts1/tiles/1.0.0/all/default/{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_21781</TileMatrixSet>
      </TileMatrixSetLink>
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_2056</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>

    <Layer>
      <ows:Title>one</ows:Title>
      <ows:Identifier>one</ows:Identifier>
      <Style isDefault="true">
        <ows:Identifier>default</ows:Identifier>
        <LegendURL format="image/png" xlink:href="http://wmts1/tiles/1.0.0/one/default/legend-5.png" width="64" height="20" />
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
                   template="http://wmts1/tiles/1.0.0/one/default/{DATE}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png" />
      <TileMatrixSetLink>
        <TileMatrixSet>swissgrid_2056</TileMatrixSet>
      </TileMatrixSetLink>
    </Layer>



    <TileMatrixSet>
      <ows:Identifier>swissgrid_2056</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::2056</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>3571428.571428572</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>2</MatrixWidth>
        <MatrixHeight>2</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>1785714.285714286</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>4</MatrixWidth>
        <MatrixHeight>3</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>714285.7142857143</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>10</MatrixWidth>
        <MatrixHeight>7</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>357142.85714285716</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>178571.42857142858</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>5</ows:Identifier>
        <ScaleDenominator>71428.57142857143</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>6</ows:Identifier>
        <ScaleDenominator>35714.28571428572</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>7</ows:Identifier>
        <ScaleDenominator>17857.14285714286</ScaleDenominator>
        <TopLeftCorner>2420000 1350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
    <TileMatrixSet>
      <ows:Identifier>swissgrid_21781</ows:Identifier>
      <ows:SupportedCRS>urn:ogc:def:crs:EPSG::21781</ows:SupportedCRS>
      <TileMatrix>
        <ows:Identifier>0</ows:Identifier>
        <ScaleDenominator>3571428.571428572</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>2</MatrixWidth>
        <MatrixHeight>2</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>1</ows:Identifier>
        <ScaleDenominator>1785714.285714286</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>4</MatrixWidth>
        <MatrixHeight>3</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>2</ows:Identifier>
        <ScaleDenominator>714285.7142857143</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>10</MatrixWidth>
        <MatrixHeight>7</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>3</ows:Identifier>
        <ScaleDenominator>357142.85714285716</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>19</MatrixWidth>
        <MatrixHeight>13</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>4</ows:Identifier>
        <ScaleDenominator>178571.42857142858</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>38</MatrixWidth>
        <MatrixHeight>25</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>5</ows:Identifier>
        <ScaleDenominator>71428.57142857143</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>94</MatrixWidth>
        <MatrixHeight>63</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>6</ows:Identifier>
        <ScaleDenominator>35714.28571428572</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>188</MatrixWidth>
        <MatrixHeight>125</MatrixHeight>
      </TileMatrix>
      <TileMatrix>
        <ows:Identifier>7</ows:Identifier>
        <ScaleDenominator>17857.14285714286</ScaleDenominator>
        <TopLeftCorner>420000 350000</TopLeftCorner>
        <TileWidth>256</TileWidth>
        <TileHeight>256</TileHeight>
        <MatrixWidth>375</MatrixWidth>
        <MatrixHeight>250</MatrixHeight>
      </TileMatrix>
    </TileMatrixSet>
  </Contents>
</Capabilities>"""
