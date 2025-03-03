import os

import psycopg2
import pytest
from testfixtures import LogCapture

from tilecloud_chain import expiretiles
from tilecloud_chain.tests import CompareCase, MatchRegex


class TestExpireTiles(CompareCase):
    def setUp(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setUpClass(cls):  # noqa
        with open("/tmp/expired", "w") as f:
            f.write("18/135900/92720\n")
            f.write("18/135900/92721\n")
            f.write("18/135900/92722\n")
            f.write("18/135901/92721\n")
            f.write("18/135901/92722\n")
            f.write("18/135902/92722\n")

        with open("/tmp/expired-empty", "w"):
            pass

    @classmethod
    def tearDownClass(cls):  # noqa
        os.remove("/tmp/expired")
        os.remove("/tmp/expired-empty")

    def test_expire_tiles(
        self,
    ) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            geom_re = MatchRegex(r"MULTIPOLYGON\(\(\(([0-9\. ,]+)\)\)\)")
            geom_coords = [
                pytest.approx([538274.006497397, 151463.940954133], abs=1e-6),
                pytest.approx([538272.927475664, 151358.882137848], abs=1e-6),
                pytest.approx([538167.532395446, 151359.965536437], abs=1e-6),
                pytest.approx([538062.137334338, 151361.050781072], abs=1e-6),
                pytest.approx([537956.742292377, 151362.137871759], abs=1e-6),
                pytest.approx([537957.826834589, 151467.19663084], abs=1e-6),
                pytest.approx([537958.911357866, 151572.253567259], abs=1e-6),
                pytest.approx([537959.995862209, 151677.308681051], abs=1e-6),
                pytest.approx([538065.385383791, 151676.221647663], abs=1e-6),
                pytest.approx([538064.302719542, 151571.166514773], abs=1e-6),
                pytest.approx([538169.694100363, 151570.08130827], abs=1e-6),
                pytest.approx([538168.61325734, 151465.024333685], abs=1e-6),
                pytest.approx([538274.006497397, 151463.940954133], abs=1e-6),
            ]

            self.assert_cmd_equals(
                cmd=[
                    ".build/venv/bin/import_expiretiles",
                    "--create",
                    "--delete",
                    "--srid",
                    "21781",
                    "/tmp/expired",
                    "user=postgresql password=postgresql dbname=tests host=db",
                    "expired",
                    "the_geom",
                ],
                main_func=expiretiles.main,
                expected="""Import successful
    """,
            )
            connection = psycopg2.connect("user=postgresql password=postgresql dbname=tests host=db")
            cursor = connection.cursor()
            cursor.execute("SELECT ST_AsText(the_geom) FROM expired")
            geoms = [str(r[0]) for r in cursor.fetchall()]
            assert [geom_re] == geoms

            def parse_coord(coord: str) -> tuple[float, float]:
                coord_split = coord.split(" ")
                return [float(c) for c in coord_split]

            assert [parse_coord(e) for e in geom_re.match(geoms[0]).group(1).split(",")] == geom_coords

            self.assert_cmd_equals(
                cmd=[
                    ".build/venv/bin/import_expiretiles",
                    "--create",
                    "--delete",
                    "--srid",
                    "21781",
                    "/tmp/expired",
                    "user=postgresql password=postgresql dbname=tests host=db",
                    "expired",
                    "the_geom",
                ],
                main_func=expiretiles.main,
                expected="""Import successful
    """,
            )
            connection = psycopg2.connect("user=postgresql password=postgresql dbname=tests host=db")
            cursor = connection.cursor()
            cursor.execute("SELECT ST_AsText(the_geom) FROM expired")
            geoms = [str(r[0]) for r in cursor.fetchall()]
            assert [geom_re] == geoms
            assert [parse_coord(e) for e in geom_re.match(geoms[0]).group(1).split(",")] == geom_coords

            self.assert_cmd_equals(
                cmd=[
                    ".build/venv/bin/import_expiretiles",
                    "--simplify",
                    "1000",
                    "--create",
                    "--delete",
                    "/tmp/expired",
                    "user=postgresql password=postgresql dbname=tests host=db",
                    "expired2",
                ],
                main_func=expiretiles.main,
                expected="""Import successful
    """,
            )
            connection = psycopg2.connect("user=postgresql password=postgresql dbname=tests host=db")
            cursor = connection.cursor()
            cursor.execute("SELECT ST_AsText(geom) FROM expired2")
            geoms = [str(r[0]) for r in cursor.fetchall()]
            geom_coords = [
                pytest.approx([738534.567188568, 5862720.06865692], abs=1e-6),
                pytest.approx([738534.567188568, 5862567.19460037], abs=1e-6),
                pytest.approx([738381.693132021, 5862567.19460037], abs=1e-6),
                pytest.approx([738228.819075469, 5862567.19460037], abs=1e-6),
                pytest.approx([738075.945018921, 5862567.19460037], abs=1e-6),
                pytest.approx([738075.945018921, 5862720.06865692], abs=1e-6),
                pytest.approx([738075.945018921, 5862872.94271347], abs=1e-6),
                pytest.approx([738075.945018921, 5863025.81677002], abs=1e-6),
                pytest.approx([738228.819075469, 5863025.81677002], abs=1e-6),
                pytest.approx([738228.819075469, 5862872.94271347], abs=1e-6),
                pytest.approx([738381.693132021, 5862872.94271347], abs=1e-6),
                pytest.approx([738381.693132021, 5862720.06865692], abs=1e-6),
                pytest.approx([738534.567188568, 5862720.06865692], abs=1e-6),
            ]
            assert [geom_re] == geoms
            assert [parse_coord(e) for e in geom_re.match(geoms[0]).group(1).split(",")] == geom_coords

            log_capture.check()

    def test_expire_tiles_empty(self) -> None:
        with LogCapture("tilecloud_chain", level=30):
            self.assert_cmd_equals(
                cmd=[
                    ".build/venv/bin/import_expiretiles",
                    "--create",
                    "--delete",
                    "--srid",
                    "21781",
                    "/tmp/expired-empty",
                    "user=postgresql password=postgresql dbname=tests host=db",
                    "expired",
                    "the_geom",
                ],
                main_func=expiretiles.main,
                expected="""No coords found
    """,
            )
            connection = psycopg2.connect("user=postgresql password=postgresql dbname=tests host=db")
            cursor = connection.cursor()
            cursor.execute("SELECT the_geom FROM expired")
            geoms = cursor.fetchall()
            assert len(geoms) == 0
