#!/usr/bin/env python

import os
from pathlib import Path

import pytest
import pytest_check
import yaml

from tilecloud_chain import TileGeneration, controller, generate
from tilecloud_chain.tests import CompareCase


class TestMultiGrid(CompareCase):
    def setUp(self) -> None:
        self.maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        os.chdir(Path(__file__).parent)

    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(Path(__file__).parent.parent.parent)

    def test_generate_all(self) -> None:
        """Test generating tiles for layer 'all'."""
        # This creates and checks tiles for the 'all' layer
        self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
                "--zoom=0",
            ],
            main_func=generate.main,
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
            expected="""The tile generation of layer 'all \(DATE=2012\)' is finish
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

    def test_generate_one(self) -> None:
        """Test generating tiles for layer 'one' which has only one grid."""
        self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=one",
                "--zoom=0",
            ],
            main_func=generate.main,
            directory="/tmp/tiles/",
            tiles_pattern="1.0.0/one/default/2012/%s/%i/%i/%i.png",
            tiles=[
                ("swissgrid_2056", 0, 0, 0),
                ("swissgrid_2056", 0, 1, 0),
                ("swissgrid_2056", 0, 0, 1),
                ("swissgrid_2056", 0, 1, 1),
            ],
            regex=True,
            expected="""The tile generation of layer 'one \(DATE=2012\)' is finish
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

    def test_generate_all_with_grid(self) -> None:
        """Test generating tiles for layer 'all' with --grid parameter."""
        for grid in ("swissgrid_2056", "swissgrid_21781"):
            with pytest_check.check:
                self.assert_tiles_generated(
                    cmd=[
                        ".build/venv/bin/generate-tiles",
                        "-d",
                        "--config=tilegeneration/test-multi-grid.yaml",
                        "--layer=all",
                        f"--grid={grid}",
                        "--zoom=0",
                    ],
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern=f"1.0.0/all/default/2012/{grid}/%i/%i/%i.png",
                    tiles=[
                        (0, 0, 0),
                        (0, 1, 0),
                        (0, 0, 1),
                        (0, 1, 1),
                    ],
                    regex=True,
                    expected="""The tile generation of layer 'all \(DATE=2012\)' is finish
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

    def test_get_hash(self) -> None:
        """Test getting hash on layer 'all'."""
        self.assert_cmd_equals(
            cmd=[
                ".build/venv/bin/generate-tiles",
                "-d",
                "--get-hash=4/0/0",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
                "--grid=swissgrid_21781",
            ],
            main_func=generate.main,
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

    def test_get_bbox_grid(self) -> None:
        """Test getting bbox on layer 'all'."""
        for grid, expected in (
            ("swissgrid_2056", "2420000,1094000,2676000,1350000"),
            ("swissgrid_21781", "420000,94000,676000,350000"),
        ):
            with pytest_check.check:
                self.assert_cmd_equals(
                    cmd=[
                        ".build/venv/bin/generate-tiles",
                        "-d",
                        "--get-bbox=0/0/0",
                        "--config=tilegeneration/test-multi-grid.yaml",
                        "--layer=all",
                        f"--grid={grid}",
                    ],
                    main_func=generate.main,
                    expected=f"""Tile bounds: [{expected}]
        """,
                )

    def test_generate_legend_all(self) -> None:
        """Test generating legend images for layer 'all'."""
        self.assert_tiles_generated(
            cmd=[
                ".build/venv/bin/generate-controller",
                "-d",
                "--legends",
                "--config=tilegeneration/test-multi-grid.yaml",
                "--layer=all",
            ],
            main_func=controller.main,
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
                        }
                    ]
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
                        }
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
    async def test_capabilities(self) -> None:
        """Test capabilities generation for the multi-grid config."""
        gene = TileGeneration(Path("tilegeneration/test-multi-grid.yaml"), configure_logging=False)
        config = gene.get_config(Path("tilegeneration/test-multi-grid.yaml"))

        capabilities = await controller.get_wmts_capabilities(
            gene, config.config["generation"]["default_cache"]
        )

        assert capabilities == "gggg"
