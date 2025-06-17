import json
import os
import shutil
from itertools import product, repeat

from testfixtures import LogCapture
from tilecloud.store.redis import RedisTileStore

from tilecloud_chain import controller, generate
from tilecloud_chain.tests import CompareCase


class TestGenerate(CompareCase):
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

    def test_get_hash(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            for d in ("-d", ""):
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} --get-hash 4/0/0 "
                    "-c tilegeneration/test.yaml -l point",
                    main_func=generate.main,
                    expected="""Tile: 4/0/0:+8/+8 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=point
            empty_metatile_detection:
                size: 20743
                hash: 01062bb3b25dcead792d7824f9a7045f0dd92992
        Tile: 4/0/0 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=point
            empty_tile_detection:
                size: 334
                hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
    """,
                )

            log_capture.check()

    def test_get_wrong_hash(self) -> None:
        for d in ("-d", "-q"):
            with LogCapture("tilecloud_chain") as log_capture:
                self.assert_cmd_exit_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} --get-hash 0/7/5 "
                    "-c tilegeneration/test.yaml -l all",
                    main_func=generate.main,
                )
                log_capture.check_present(
                    (
                        "tilecloud_chain",
                        "DEBUG",
                        "Error: image is not uniform.",
                    ),
                )

    def test_get_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4 -l point",
                    main_func=generate.main,
                    expected="""Tile bounds: [425120,343600,426400,344880]
""",
                )
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4:+1/+1 -l point",
                    main_func=generate.main,
                    expected="""Tile bounds: [425120,343600,426400,344880]
    """,
                )
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4:+2/+2 -l point",
                    main_func=generate.main,
                    expected="""Tile bounds: [425120,342320,427680,344880]
    """,
                )
                log_capture.check()

    def test_hash_mapnik(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "--get-hash 4/0/0 -c tilegeneration/test.yaml -l mapnik",
                    main_func=generate.main,
                    expected="""Tile: 4/0/0 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=mapnik
    empty_metatile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
Tile: 4/0/0 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=mapnik
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
""",
                )
                log_capture.check()

    def test_hash_mapnik_grid(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "--get-hash 4/0/0 -c tilegeneration/test.yaml -l all",
                    main_func=generate.main,
                    expected="""Tile: 4/0/0 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=all
    empty_metatile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
    Tile: 4/0/0 config_file=tilegeneration/test.yaml dimension_DATE=2012 grid=swissgrid_5 host=localhost layer=all
    empty_tile_detection:
        size: 334
        hash: dd6cb45962bccb3ad2450ab07011ef88f766eda8
    """,
                )
                log_capture.check()

    def test_test_all(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -t 1",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[
                        ("line", 0, 5, 6),
                        ("line", 0, 5, 7),
                        ("line", 0, 6, 5),
                        ("line", 0, 6, 6),
                        ("line", 0, 7, 4),
                        ("line", 0, 7, 5),
                        ("polygon", 0, 5, 4),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'line \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 58
    Nb tiles stored: 6
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 3.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 6[0-9][0-9] o

    The tile generation of layer 'polygon \(DATE=2012\)' is finish
    Nb generated tiles: 1
    Nb tiles dropped: 0
    Nb tiles stored: 1
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [45][0-9][0-9] o
    Time per tile: [0-9]+ ms
    Size per tile: [45][0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_test_dimensions(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -t 1 "
                    "--dimensions DATE=2013",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2013/swissgrid_5/%i/%i/%i.png",
                    tiles=[
                        ("line", 0, 5, 6),
                        ("line", 0, 5, 7),
                        ("line", 0, 6, 5),
                        ("line", 0, 6, 6),
                        ("line", 0, 7, 4),
                        ("line", 0, 7, 5),
                        ("polygon", 0, 5, 4),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'line \(DATE=2013\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 58
    Nb tiles stored: 6
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 3.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 6[0-9][0-9] o

    The tile generation of layer 'polygon \(DATE=2013\)' is finish
    Nb generated tiles: 1
    Nb tiles dropped: 0
    Nb tiles stored: 1
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [45][0-9][0-9] o
    Time per tile: [0-9]+ ms
    Size per tile: [45][0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_multigeom(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-multigeom.yaml",
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/pp/default/2012/swissgrid_5/%i/%i/%i.png",
                tiles=[
                    (0, 5, 4),
                    (0, 5, 5),
                    (0, 5, 6),
                    (0, 5, 7),
                    (0, 6, 4),
                    (0, 6, 5),
                    (0, 6, 6),
                    (0, 6, 7),
                    (0, 7, 4),
                    (0, 7, 5),
                    (0, 7, 6),
                    (0, 7, 7),
                    (1, 11, 8),
                    (1, 11, 9),
                    (1, 11, 10),
                    (1, 11, 11),
                    (1, 11, 12),
                    (1, 11, 13),
                    (1, 11, 14),
                    (1, 12, 8),
                    (1, 12, 9),
                    (1, 12, 10),
                    (1, 12, 11),
                    (1, 12, 12),
                    (1, 12, 13),
                    (1, 12, 14),
                    (1, 13, 8),
                    (1, 13, 9),
                    (1, 13, 10),
                    (1, 13, 11),
                    (1, 13, 12),
                    (1, 13, 13),
                    (1, 13, 14),
                    (1, 14, 8),
                    (1, 14, 9),
                    (1, 14, 10),
                    (1, 14, 11),
                    (1, 14, 12),
                    (1, 14, 13),
                    (1, 14, 14),
                    (1, 15, 8),
                    (1, 15, 9),
                    (1, 15, 10),
                    (1, 15, 11),
                    (1, 15, 12),
                    (1, 15, 13),
                    (1, 15, 14),
                    (2, 29, 35),
                    (2, 39, 21),
                    (3, 78, 42),
                    (3, 58, 70),
                ],
                regex=True,
                expected=r"""The tile generation of layer 'pp \(DATE=2012\)' is finish
    Nb generated tiles: 51
    Nb tiles dropped: 0
    Nb tiles stored: 51
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [34][0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: [79][0-9][0-9] o

    """,
            )
            log_capture.check()

    def test_zoom_identifier(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            xy = list(product(range(585, 592), range(429, 432)))
            x = [e[0] for e in xy]
            y = [e[1] for e in xy]
            xy2 = list(product(range(2929, 2936), range(2148, 2152)))
            x2 = [e[0] for e in xy2]
            y2 = [e[1] for e in xy2]
            xy3 = list(product(range(5859, 5864), range(4296, 4304)))
            x3 = [e[0] for e in xy3]
            y3 = [e[1] for e in xy3]
            for d in ("-d", ""):
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png",
                    tiles=list(zip(repeat("polygon2", len(x)), repeat("1", len(x)), x, y, strict=False)),
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon2 \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 43
    Nb tiles stored: 21
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 16 Kio
    Time per tile: [0-9]+ ms
    Size per tile: 788 o

    """,
                )
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 1",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png",
                    tiles=list(
                        zip(repeat("polygon2", len(x2)), repeat("0_2", len(x2)), x2, y2, strict=False)
                    ),
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon2 \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 36
    Nb tiles stored: 28
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 22 Kio
    Time per tile: [0-9]+ ms
    Size per tile: 806 o

    """,
                )
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 2",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png",
                    tiles=list(
                        zip(repeat("polygon2", len(x3)), repeat("0_1", len(x3)), x3, y3, strict=False)
                    ),
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon2 \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 24
    Nb tiles stored: 40
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 32 Kio
    Time per tile: [0-9]+ ms
    Size per tile: 818 o

    """,
                )
            log_capture.check()

    def test_empty_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash --bbox 700000 250000 800000 300000",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s",
                    tiles=[],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
    Nb generated metatiles: 0
    Nb metatiles dropped: 0
    Nb generated tiles: 0
    Nb tiles dropped: 0
    Nb tiles stored: 0
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]

    """,
                )
                # Second time for the debug mode
                log_capture.check(
                    ("tilecloud_chain", "WARNING", "bounds empty for zoom 0"),
                    ("tilecloud_chain", "WARNING", "bounds empty for zoom 1"),
                    ("tilecloud_chain", "WARNING", "bounds empty for zoom 2"),
                    ("tilecloud_chain", "WARNING", "bounds empty for zoom 3"),
                )

    def test_zoom(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash --zoom 1",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[("point_hash", 1, 11, 14), ("point_hash", 1, 15, 8)],
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
                log_capture.check()

    def test_zoom_range(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash --zoom 1-3",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[
                        ("point_hash", 1, 11, 14),
                        ("point_hash", 1, 15, 8),
                        ("point_hash", 2, 29, 35),
                        ("point_hash", 2, 39, 21),
                        ("point_hash", 3, 58, 70),
                        ("point_hash", 3, 78, 42),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
    Nb generated metatiles: 9
    Nb metatiles dropped: 4
    Nb generated tiles: 320
    Nb tiles dropped: 314
    Nb tiles stored: 6
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 2.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 4[0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_no_zoom(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=(
                        f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -l point_hash"
                    ),
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[
                        ("point_hash", 0, 5, 7),
                        ("point_hash", 0, 7, 4),
                        ("point_hash", 1, 11, 14),
                        ("point_hash", 1, 15, 8),
                        ("point_hash", 2, 29, 35),
                        ("point_hash", 2, 39, 21),
                        ("point_hash", 3, 58, 70),
                        ("point_hash", 3, 78, 42),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
    Nb generated metatiles: 10
    Nb metatiles dropped: 4
    Nb generated tiles: 384
    Nb tiles dropped: 376
    Nb tiles stored: 8
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 3.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 4[0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_py_buffer(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_px_buffer --zoom 0-2",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/point_px_buffer/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[(0, 5, 7), (0, 7, 4), (1, 11, 14), (1, 15, 8), (2, 29, 35), (2, 39, 21)],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_px_buffer \(DATE=2012\)' is finish
    Nb generated metatiles: 10
    Nb metatiles dropped: 4
    Nb generated tiles: 384
    Nb tiles dropped: 378
    Nb tiles stored: 6
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 2.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 4[0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_zoom_list(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=(
                        f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                        "-l point_hash --zoom 0,2,3"
                    ),
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                    tiles=[
                        ("point_hash", 0, 5, 7),
                        ("point_hash", 0, 7, 4),
                        ("point_hash", 2, 29, 35),
                        ("point_hash", 2, 39, 21),
                        ("point_hash", 3, 58, 70),
                        ("point_hash", 3, 78, 42),
                    ],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
    Nb generated metatiles: 9
    Nb metatiles dropped: 4
    Nb generated tiles: 320
    Nb tiles dropped: 314
    Nb tiles stored: 6
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 2.[0-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: 4[0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_layer_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon \(DATE=2012\)' is finish
    Nb generated tiles: 12
    Nb tiles dropped: 0
    Nb tiles stored: 12
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [0-9.]+ Kio
    Time per tile: [0-9.]+ ms
    Size per tile: [69][0-9][0-9] o

    """,
                )

                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0"
                    " -b 550000 170000 560000 180000",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=[(6, 5), (7, 5)],
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon \(DATE=2012\)' is finish
    Nb generated tiles: 2
    Nb tiles dropped: 0
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 1.[6-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: [89][0-9][0-9] o

    """,
                )

                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0"
                    " -b 550000.0 170000.0 560000.0 180000.0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=[(6, 5), (7, 5)],
                    regex=True,
                    expected=r"""The tile generation of layer 'polygon \(DATE=2012\)' is finish
    Nb generated tiles: 2
    Nb tiles dropped: 0
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 1.[6-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: [89][0-9][0-9] o

    """,
                )

                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -l all -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/all/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=[(6, 5), (7, 5)],
                    regex=True,
                    expected=r"""The tile generation of layer 'all \(DATE=2012\)' is finish
    Nb generated tiles: 2
    Nb tiles dropped: 0
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 1.[6-9] Kio
    Time per tile: [0-9]+ ms
    Size per tile: [89][0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_hash_generation(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/point_hash/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=[(5, 7), (7, 4)],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_hash \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 64
    Nb tiles dropped: 62
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 9[0-9][0-9] o
    Time per tile: [0-9]+ ms
    Size per tile: [45][0-9][0-9] o

    """,
                )
                log_capture.check()

    def test_mapnik(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/mapnik/default/2012/swissgrid_5/0/%i/%i.png",
                    tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                    regex=True,
                    expected=r"""The tile generation of layer 'mapnik' is finish
    Nb generated tiles: 12
    Nb tiles dropped: 0
    Nb tiles stored: 12
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 9.7 Kio
    Time per tile: [0-9]+ ms
    Size per tile: 824 o

    """,
                )
                log_capture.check()

    def test_mapnik_grid(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik_grid -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/mapnik_grid/default/2012/swissgrid_5/0/%i/%i.json",
                    tiles=list(product((5, 6, 7), (4, 5, 6, 7))),
                    regex=True,
                    expected=r"""The tile generation of layer 'mapnik_grid' is finish
    Nb generated tiles: 12
    Nb tiles dropped: 0
    Nb tiles stored: 12
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 4.5 Kio
    Time per tile: [0-9]+ ms
    Size per tile: 385 o

    """,
                )
                with open("/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/5/5.json") as f:
                    assert json.loads(f.read()) == {
                        "grid": [
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "!!!!!!!!!!!!!!!!",
                            "!!!!!!!!!!!!!!!!",
                        ],
                        "keys": ["", "1"],
                        "data": {"1": {"name": "polygon1"}},
                    }
                with open("/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/6/5.json") as f:
                    assert json.loads(f.read()) == {
                        "grid": [
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                            "                ",
                        ],
                        "keys": ["1"],
                        "data": {"1": {"name": "polygon1"}},
                    }
                log_capture.check()

    def test_mapnik_grid_drop(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik_grid_drop -z 0",
                    main_func=generate.main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/mapnik_grid_drop/default/2012/swissgrid_5/0/%i/%i.json",
                    tiles=((5, 7), (7, 4)),
                    regex=True,
                    expected=r"""The tile generation of layer 'mapnik_grid_drop' is finish
    Nb generated tiles: 2
    Nb tiles dropped: 0
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 768 o
    Time per tile: [0-9]+ ms
    Size per tile: 384 o

    """,
                )
                log_capture.check()

    def test_not_authorised_user(self) -> None:
        for d in ("-d", "-q"):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_exit_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-authorised.yaml",
                    main_func=generate.main,
                )
                log_capture.check(
                    (
                        "tilecloud_chain.generate",
                        "ERROR",
                        "not authorized, authorized user is: www-data.",
                    )
                )

    def test_verbose(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.run_cmd(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 2 -v -l polygon",
                    main_func=generate.main,
                )
                log_capture.check()

    def test_time(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test.yaml --time 2 -l polygon",
                    main_func=generate.main,
                    expected=r"""size: 770
    size: 862
    size: 862
    size: 862
    time: [0-9]*
    size: 862
    size: 862
    """,
                    regex=True,
                    empty_err=True,
                )
                log_capture.check()

    def test_time_layer_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test.yaml --time 2 -l all",
                    main_func=generate.main,
                    expected=r"""size: 1010
    size: 1010
    size: 1010
    size: 1010
    time: [0-9]*
    size: 1010
    size: 1010
    """,
                    regex=True,
                    empty_err=True,
                )
                log_capture.check()

    # def test_daemonize(self):
    #     with LogCapture("tilecloud_chain", level=30) as log_capture:
    #         self.assert_cmd_equals(
    #             cmd='.build/venv/bin/generate-tiles %s -c tilegeneration/test.yaml -t 1 --daemonize' % d,
    #             main_func=generate.main,
    #             expected=r"""Daemonize with pid [0-9]*.""",
    #             regex=True)
    #         log_capture.check()

    def _touch(self, tiles_pattern: str, tiles: list[tuple[int, int]]) -> None:
        for tile in tiles:
            path = tiles_pattern % tile
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            with open(path, "w"):
                pass

    def test_delete_meta(self) -> None:
        for d in ("-d", ""):
            if os.path.exists("/tmp/tiles/"):
                shutil.rmtree("/tmp/tiles/")
            self._touch(
                tiles_pattern="/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=list(product(range(12), range(16))),
            )
            self.assert_tiles_generated_deleted(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash_no_meta -z 0"
                ),
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=[(5, 7), (7, 4)],
                regex=True,
                expected=r"""The tile generation of layer 'point_hash_no_meta \(DATE=2012\)' is finish
Nb generated tiles: 247
Nb tiles dropped: 245
Nb tiles stored: 2
Nb tiles in error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tile: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )

    def test_delete_no_meta(self) -> None:
        for d in ("-d", ""):
            if os.path.exists("/tmp/tiles/"):
                shutil.rmtree("/tmp/tiles/")
            self._touch(
                tiles_pattern="/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=list(product(range(12), range(16))),
            )
            self.assert_tiles_generated_deleted(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash_no_meta -z 0"
                ),
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=[(5, 7), (7, 4)],
                regex=True,
                expected=r"""The tile generation of layer 'point_hash_no_meta \(DATE=2012\)' is finish
Nb generated tiles: 247
Nb tiles dropped: 245
Nb tiles stored: 2
Nb tiles in error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: [89][0-9][0-9] o
Time per tile: [0-9]+ ms
Size per tile: 4[0-9][0-9] o

""",
            )

    def test_error_file_create(self) -> None:
        tile_mbt = os.environ["TILE_NB_THREAD"]
        metatile_mbt = os.environ["METATILE_NB_THREAD"]
        os.environ["TILE_NB_THREAD"] = "1"
        os.environ["METATILE_NB_THREAD"] = "1"

        if os.path.exists("error.list"):
            os.remove("error.list")
        self.assert_main_except_equals(
            cmd=".build/venv/bin/generate-tiles -q -c tilegeneration/test-nosns.yaml -l point_error",
            main_func=generate.main,
            regex=True,
            get_error=True,
            expected=[
                [
                    "error.list",
                    "\n".join(
                        [
                            r"# \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] "
                            r"Start the layer 'point_error' generation",
                            r"0/0/0:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request "
                            r"settings\.'",
                            r"0/0/8:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request "
                            r"settings\.'",
                            r"0/8/0:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request settings\.'",
                            "",
                        ]
                    ),
                ]
            ],
        )

        os.environ["TILE_NB_THREAD"] = tile_mbt
        os.environ["METATILE_NB_THREAD"] = metatile_mbt

    def test_error_file_use(self) -> None:
        tile_mbt = os.environ["TILE_NB_THREAD"]
        metatile_mbt = os.environ["METATILE_NB_THREAD"]
        main_congifile = os.environ["TILEGENERATION_MAIN_CONFIGFILE"]
        os.environ["TILE_NB_THREAD"] = "1"
        os.environ["METATILE_NB_THREAD"] = "1"
        os.environ["TILEGENERATION_MAIN_CONFIGFILE"] = "tilegeneration/test-nosns.yaml"

        try:
            if os.path.exists("error.list"):
                os.remove("error.list")

            with open("error.list", "w") as error_file:
                error_file.write(
                    "# comment\n"
                    "0/0/0:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5 "
                    "# comment\n"
                    "0/0/8:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5\n"
                    "0/8/0:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5\n"
                )

            self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --tiles error.list",
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/point_hash/default/2012/swissgrid_5/%i/%i/%i.png",
                tiles=[(0, 5, 7), (0, 7, 4)],
                regex=True,
                expected=r"""The tile generation is finish
    Nb generated metatiles: 3
    Nb metatiles dropped: 1
    Nb generated tiles: 128
    Nb tiles dropped: 126
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [89][0-9][0-9] o
    Time per tile: [0-9]+ ms
    Size per tile: [45][0-9][0-9] o

    """,
            )
        finally:
            os.environ["TILE_NB_THREAD"] = tile_mbt
            os.environ["METATILE_NB_THREAD"] = metatile_mbt
            os.environ["TILEGENERATION_MAIN_CONFIGFILE"] = main_congifile

    def test_multy(self) -> None:
        for d in ("-v", ""):
            self.assert_tiles_generated(
                cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-multidim.yaml",
                main_func=generate.main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/multi/default/%s/swissgrid/%i/%i/%i.png",
                tiles=[
                    ("point1", 0, 5, 7),
                    ("point1", 1, 11, 14),
                    ("point1", 2, 29, 35),
                    ("point2", 0, 7, 4),
                    ("point2", 1, 15, 8),
                    ("point2", 2, 39, 21),
                ],
                regex=True,
                expected=r"""The tile generation of layer 'multi \(POINT_NAME=point1 - POINT_NAME=point2\)' is finish
Nb generated metatiles: 16
Nb metatiles dropped: 10
Nb generated tiles: 384
Nb tiles dropped: 378
Nb tiles stored: 6
Nb tiles in error: 0
Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
Total size: 2.9 Kio
Time per tile: [0-9]+ ms
Size per tile: 498 o

""",
            )

    def test_redis(self) -> None:
        RedisTileStore(sentinels=[["redis_sentinel", 26379]]).delete_all()
        self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis.yaml --role master -l point",
            main_func=generate.main,
            regex=False,
            expected="""The tile generation of layer 'point (DATE=2012)' is finish
Nb of generated jobs: 10

""",
        )

        self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis.yaml --status",
            main_func=controller.main,
            regex=False,
            expected="""Approximate number of tiles to generate: 10
Approximate number of generating tiles: 0
Tiles in error:
""",
        )

        self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis.yaml --role slave",
            main_func=generate.main,
            regex=True,
            expected=r"""The tile generation is finish
Nb generated metatiles: 10
Nb metatiles dropped: 0
Nb generated tiles: 640
Nb tiles dropped: 0
Nb tiles stored: 640
Nb tiles in error: 0
Total time: 0:\d\d:\d\d
Total size: \d+ Kio
Time per tile: \d+ ms
Size per tile: \d+ o

""",
        )

        self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis.yaml --status",
            main_func=controller.main,
            regex=False,
            expected="""Approximate number of tiles to generate: 0
Approximate number of generating tiles: 0
Tiles in error:
""",
        )

    def test_redis_main_config(self) -> None:
        main_congifile = os.environ["TILEGENERATION_MAIN_CONFIGFILE"]
        os.environ["TILEGENERATION_MAIN_CONFIGFILE"] = "tilegeneration/test-redis-main.yaml"

        try:
            RedisTileStore(sentinels=[["redis_sentinel", 26379]]).delete_all()
            self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis-project.yaml --role master -l point",
                main_func=generate.main,
                regex=False,
                expected="""The tile generation of layer 'point (DATE=2012)' is finish
    Nb of generated jobs: 10

    """,
            )

            self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis-project.yaml --status",
                main_func=controller.main,
                regex=False,
                expected="""Approximate number of tiles to generate: 10
    Approximate number of generating tiles: 0
    Tiles in error:
    """,
            )

            self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis-project.yaml --role slave",
                main_func=generate.main,
                regex=True,
                expected=r"""The tile generation is finish
    Nb generated metatiles: 10
    Nb metatiles dropped: 0
    Nb generated tiles: 640
    Nb tiles dropped: 0
    Nb tiles stored: 640
    Nb tiles in error: 0
    Total time: 0:\d\d:\d\d
    Total size: \d+ Kio
    Time per tile: \d+ ms
    Size per tile: \d+ o

    """,
            )

            self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis-project.yaml --status",
                main_func=controller.main,
                regex=False,
                expected="""Approximate number of tiles to generate: 0
    Approximate number of generating tiles: 0
    Tiles in error:
    """,
            )
        finally:
            os.environ["TILEGENERATION_MAIN_CONFIGFILE"] = main_congifile
