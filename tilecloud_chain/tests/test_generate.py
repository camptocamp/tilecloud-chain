import json
import os
import shutil
import sys
from argparse import Namespace
from io import StringIO
from itertools import product, repeat
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anyio import Path as AnyioPath
from PIL import Image
from shapely.geometry import box
from testfixtures import LogCapture
from tilecloud import Tile, TileCoord
from tilecloud.store.redis import RedisTileStore

import tilecloud_chain
from tilecloud_chain import (
    DatedConfig,
    HashLogger,
    IntersectGeometryFilter,
    SparseMetaTileBoundingPyramid,
    TileGeneration,
    controller,
    generate,
    get_proj4_literal,
    get_tile_matrix_limits,
    normalize_bbox,
    transform_bbox,
)
from tilecloud_chain import configuration as tcc_configuration
from tilecloud_chain.settings import settings
from tilecloud_chain.tests import CompareCase


@pytest.mark.asyncio
async def test_master_initializes_tilegeneration_with_queue_store(monkeypatch: pytest.MonkeyPatch) -> None:
    queue_store = object()

    async def fake_get_queue_store(_config: object, _daemon: bool) -> object:
        return queue_store

    monkeypatch.setattr(generate, "get_queue_store", fake_get_queue_store)

    gene = Mock()
    gene.get_main_config = AsyncMock(return_value=SimpleNamespace(config={}))
    gene.add_geom_filter = Mock()
    gene.imap = Mock()
    gene.add_logger = Mock()
    gene.put = Mock()
    gene.counter = Mock(return_value=object())
    gene.init = Mock()

    generate_ = generate.Generate(
        Namespace(
            get_hash=None,
            tiles=None,
            role="master",
            daemon=False,
            local_process_number=None,
        ),
        gene,
        out=None,
    )

    await generate_._generate_init()  # noqa: SLF001

    gene.init.assert_called_once_with(queue_store, daemon=False)


@pytest.mark.asyncio
async def test_ensure_postgresql_job_id_uses_default_title(monkeypatch: pytest.MonkeyPatch) -> None:
    queue_store = Mock()
    queue_store.create_job = AsyncMock(return_value=42)
    queue_store.close = AsyncMock()
    monkeypatch.setattr(generate, "get_queue_store", AsyncMock(return_value=queue_store))

    options = Namespace(
        role="master",
        job_id=None,
        get_hash=None,
        get_bbox=None,
        tiles=None,
        daemon=False,
        job_title=None,
    )
    gene = Mock()
    gene.get_main_config = AsyncMock(
        return_value=SimpleNamespace(config={"queue_store": "postgresql"}, file=AnyioPath("config.yaml")),
    )

    await generate._ensure_postgresql_job_id(options, gene, ["generate-tiles", "--role", "master"])

    assert options.job_id == 42
    queue_store.create_job.assert_awaited_once_with(
        "User call",
        "generate-tiles --role master",
        AnyioPath("config.yaml"),
        initial_status="pending",
    )


@pytest.mark.asyncio
async def test_ensure_postgresql_job_id_uses_custom_title(monkeypatch: pytest.MonkeyPatch) -> None:
    queue_store = Mock()
    queue_store.create_job = AsyncMock(return_value=84)
    queue_store.close = AsyncMock()
    monkeypatch.setattr(generate, "get_queue_store", AsyncMock(return_value=queue_store))

    options = Namespace(
        role="master",
        job_id=None,
        get_hash=None,
        get_bbox=None,
        tiles=None,
        daemon=False,
        job_title="custom-title",
    )
    gene = Mock()
    gene.get_main_config = AsyncMock(
        return_value=SimpleNamespace(config={"queue_store": "postgresql"}, file=AnyioPath("config.yaml")),
    )

    await generate._ensure_postgresql_job_id(options, gene, ["generate-tiles", "--role", "master"])

    assert options.job_id == 84
    queue_store.create_job.assert_awaited_once_with(
        "custom-title",
        "generate-tiles --role master",
        AnyioPath("config.yaml"),
        initial_status="pending",
    )


@pytest.mark.asyncio
async def test_ensure_postgresql_job_id_removes_job_title_from_saved_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue_store = Mock()
    queue_store.create_job = AsyncMock(return_value=84)
    queue_store.close = AsyncMock()
    monkeypatch.setattr(generate, "get_queue_store", AsyncMock(return_value=queue_store))

    options = Namespace(
        role="master",
        job_id=None,
        get_hash=None,
        get_bbox=None,
        tiles=None,
        daemon=False,
        job_title="custom-title",
    )
    gene = Mock()
    gene.get_main_config = AsyncMock(
        return_value=SimpleNamespace(config={"queue_store": "postgresql"}, file=AnyioPath("config.yaml")),
    )

    await generate._ensure_postgresql_job_id(
        options,
        gene,
        ["/tmp/.build/venv/bin/generate-tiles", "--role", "master", "--job-title", "custom-title"],
    )

    queue_store.create_job.assert_awaited_once_with(
        "custom-title",
        "generate-tiles --role master",
        AnyioPath("config.yaml"),
        initial_status="pending",
    )


@pytest.mark.asyncio
async def test_activate_postgresql_job(monkeypatch: pytest.MonkeyPatch) -> None:
    queue_store = Mock()
    queue_store.close = AsyncMock()
    queue_store.start_job = AsyncMock()

    options = Namespace(job_id=42)

    await generate._activate_postgresql_job(options, queue_store)

    queue_store.close.assert_awaited_once_with()
    queue_store.start_job.assert_awaited_once_with(42)


def test_normalize_job_command_arguments() -> None:
    assert generate._normalize_job_command_arguments(
        ["/tmp/.build/venv/bin/generate-tiles", "--role", "master", "--job-title", "my title"],
    ) == ["generate-tiles", "--role", "master"]

    assert generate._normalize_job_command_arguments(
        ["/tmp/.build/venv/bin/generate-tiles", "--role", "master", "--job-title=my title"],
    ) == ["generate-tiles", "--role", "master"]


def test_merge_index_intervals_merges_overlaps_and_adjacency() -> None:
    assert SparseMetaTileBoundingPyramid._merge_index_intervals([(5, 7), (1, 3), (3, 4), (9, 9), (8, 8)]) == [
        (1, 9),
    ]


@pytest.mark.asyncio
async def test_generate_queue_enables_sparse_seed_on_master() -> None:
    options = Namespace(
        get_hash=None,
        tiles=None,
        role="master",
        get_bbox=None,
        tile=None,
        grid=None,
    )
    gene = Mock()
    gene.config_file = AnyioPath("config.yaml")
    config = SimpleNamespace(config={"layers": {"point": {}}})
    gene.get_config = AsyncMock(return_value=config)
    gene.init_tilecoords = Mock()

    generate_ = generate.Generate(options, gene, out=None)
    await generate_._generate_queue("point")  # noqa: SLF001

    gene.init_tilecoords.assert_called_once_with(config, "point", None, sparse_meta_seed=True)


@pytest.mark.asyncio
async def test_generate_queue_disables_sparse_seed_on_local() -> None:
    options = Namespace(
        get_hash=None,
        tiles=None,
        role="local",
        get_bbox=None,
        tile=None,
        grid=None,
    )
    gene = Mock()
    gene.config_file = AnyioPath("config.yaml")
    config = SimpleNamespace(config={"layers": {"point": {}}})
    gene.get_config = AsyncMock(return_value=config)
    gene.init_tilecoords = Mock()

    generate_ = generate.Generate(options, gene, out=None)
    await generate_._generate_queue("point")  # noqa: SLF001

    gene.init_tilecoords.assert_called_once_with(config, "point", None, sparse_meta_seed=False)


def test_sparse_metatilecoords_split_by_row() -> None:
    grid = {
        "bbox": [0, 0, 8, 8],
        "tile_size": 1,
        "resolutions": [1],
    }
    geom = box(0.2, 4.2, 1.8, 4.8).union(box(3.2, 4.2, 3.8, 4.8)).union(box(6.2, 2.2, 6.8, 2.8))

    bounding_pyramid = SparseMetaTileBoundingPyramid(
        tilegrid=Mock(),
        grid=cast("tcc_configuration.Grid", grid),
        geoms={0: geom},
        zooms=[0],
        resolutions=[1],
        px_buffer=0,
    )

    metatilecoords = list(bounding_pyramid.metatilecoords(1))

    assert [(coord.z, coord.x, coord.y, coord.n) for coord in metatilecoords] == [
        (0, 0, 3, 1),
        (0, 1, 3, 1),
        (0, 3, 3, 1),
        (0, 6, 5, 1),
    ]


def test_resolve_gdal_datasource_relative() -> None:
    datasource = TileGeneration._resolve_gdal_datasource(
        AnyioPath("/tmp/tilegeneration/config.yaml"),
        "geoms/mask.geojson",
    )
    assert datasource == "/tmp/tilegeneration/geoms/mask.geojson"


def test_resolve_gdal_datasource_uri() -> None:
    with pytest.raises(ValueError, match="Only relative file paths"):
        TileGeneration._resolve_gdal_datasource(
            AnyioPath("/tmp/tilegeneration/config.yaml"),
            "PG:host=db dbname=tests",
        )


def test_resolve_gdal_datasource_parent_not_allowed() -> None:
    with pytest.raises(ValueError, match="inside the config directory"):
        TileGeneration._resolve_gdal_datasource(
            AnyioPath("/tmp/tilegeneration/config.yaml"),
            "../mask.geojson",
        )


def test_resolve_gdal_datasource_absolute_not_allowed() -> None:
    with pytest.raises(ValueError, match="Only relative file paths"):
        TileGeneration._resolve_gdal_datasource(
            AnyioPath("/tmp/tilegeneration/config.yaml"),
            "/tmp/mask.geojson",
        )


def test_load_geom_from_datasource_with_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    read_args: tuple[str, str | None] | None = None

    def _read_ogr_geometries(datasource: str, sql: str | None) -> list[Any]:
        nonlocal read_args
        read_args = (datasource, sql)
        return []

    monkeypatch.setattr(TileGeneration, "_read_ogr_geometries", _read_ogr_geometries)

    geom = TileGeneration._load_geom_from_datasource(
        AnyioPath("/tmp/tilegeneration/config.yaml"),
        {"datasource": "geoms/mask.geojson", "sql": "SELECT * FROM mask"},
    )

    assert read_args == ("/tmp/tilegeneration/geoms/mask.geojson", "SELECT * FROM mask")
    assert geom.is_empty


def test_load_geom_from_datasource_reprojects_to_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    source_projection = get_proj4_literal(21781)
    destination_projection = get_proj4_literal(2056)
    source_geom = box(550100.0, 170100.0, 550200.0, 170200.0)

    def _read_ogr_geometries(_datasource: str, _sql: str | None) -> list[Any]:
        return [source_geom]

    monkeypatch.setattr(TileGeneration, "_read_ogr_geometries", _read_ogr_geometries)

    geom = TileGeneration._load_geom_from_datasource(
        AnyioPath("/tmp/tilegeneration/config.yaml"),
        {"datasource": "geoms/mask.geojson"},
        layer_proj4_literal=source_projection,
        grid_proj4_literal=destination_projection,
        layer_srs="EPSG:21781",
        grid_srs="EPSG:2056",
    )

    assert geom.bounds == pytest.approx(
        tuple(transform_bbox(source_projection, destination_projection, source_geom.bounds)),
        abs=1e-6,
    )


def test_get_geoms_from_datasource(monkeypatch: pytest.MonkeyPatch) -> None:
    read_args: tuple[str, str | None] | None = None

    def _read_ogr_geometries(datasource: str, sql: str | None) -> list[Any]:
        nonlocal read_args
        read_args = (datasource, sql)
        return [box(550000, 170000, 560000, 180000)]

    monkeypatch.setattr(TileGeneration, "_read_ogr_geometries", _read_ogr_geometries)

    gene = TileGeneration(
        options=Namespace(
            verbose=False,
            debug=False,
            quiet=False,
            bbox=None,
            zoom=None,
            test=None,
            near=None,
            time=None,
            geom=True,
            ignore_error=False,
            host="localhost",
        ),
        configure_logging=False,
    )
    config = DatedConfig(
        {
            "grids": {
                "swissgrid_5": {
                    "resolutions": [1000, 500, 250],
                    "bbox": [420000, 30000, 900000, 350000],
                    "srs": "EPSG:21781",
                },
            },
            "layers": {
                "point_datasource": {
                    "type": "wms",
                    "url": "http://mapserver:8080/",
                    "layers": "point",
                    "wmts_style": "default",
                    "mime_type": "image/png",
                    "extension": "png",
                    "grid": "swissgrid_5",
                    "geoms": [{"datasource": "geoms/mask.geojson"}],
                },
            },
        },
        0,
        AnyioPath("/tmp/tilegeneration/test-geoms-datasource.yaml"),
    )

    geoms = gene.get_geoms(config, "point_datasource", "swissgrid_5")

    assert read_args == ("/tmp/tilegeneration/geoms/mask.geojson", None)
    assert sorted(geoms.keys()) == [0, 1, 2]
    assert geoms[0].bounds == (550000.0, 170000.0, 560000.0, 180000.0)


def test_read_ogr_geometries_uses_sql_and_releases_result_set(monkeypatch: pytest.MonkeyPatch) -> None:
    execute_sql_calls: list[str] = []
    release_calls = 0

    class _Geometry:
        def ExportToJson(self) -> str:  # noqa: N802
            return json.dumps({"type": "Point", "coordinates": [1, 2]})

    class _Feature:
        @staticmethod
        def GetGeometryRef() -> _Geometry:  # noqa: N802
            return _Geometry()

    class _Layer:
        def __iter__(self):
            return iter([_Feature()])

    class _DataSource:
        def GetLayer(self) -> _Layer:  # noqa: N802
            return _Layer()

        def ExecuteSQL(self, sql: str) -> _Layer:  # noqa: N802
            execute_sql_calls.append(sql)
            return _Layer()

        def ReleaseResultSet(self, _layer: _Layer) -> None:  # noqa: N802
            nonlocal release_calls
            release_calls += 1

    class _Ogr:
        @staticmethod
        def Open(_datasource: str) -> _DataSource:  # noqa: N802
            return _DataSource()

    monkeypatch.setitem(sys.modules, "osgeo", SimpleNamespace(ogr=_Ogr()))

    geometries = TileGeneration._read_ogr_geometries("/tmp/mask.geojson", "SELECT * FROM mask")

    assert len(geometries) == 1
    assert execute_sql_calls == ["SELECT * FROM mask"]
    assert release_calls == 1


def test_read_ogr_geometries_without_sql_uses_default_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    get_layer_calls = 0

    class _Geometry:
        def ExportToJson(self) -> str:  # noqa: N802
            return json.dumps({"type": "Point", "coordinates": [1, 2]})

    class _Feature:
        @staticmethod
        def GetGeometryRef() -> _Geometry:  # noqa: N802
            return _Geometry()

    class _Layer:
        def __iter__(self):
            return iter([_Feature()])

    class _DataSource:
        def GetLayer(self) -> _Layer:  # noqa: N802
            nonlocal get_layer_calls
            get_layer_calls += 1
            return _Layer()

        def ExecuteSQL(self, _sql: str) -> _Layer:  # noqa: N802
            raise AssertionError("ExecuteSQL should not be called without sql")

        def ReleaseResultSet(self, _layer: _Layer) -> None:  # noqa: N802
            raise AssertionError("ReleaseResultSet should not be called without sql")

    class _Ogr:
        @staticmethod
        def Open(_datasource: str) -> _DataSource:  # noqa: N802
            return _DataSource()

    monkeypatch.setitem(sys.modules, "osgeo", SimpleNamespace(ogr=_Ogr()))

    geometries = TileGeneration._read_ogr_geometries("/tmp/mask.geojson", None)

    assert len(geometries) == 1
    assert get_layer_calls == 1


@pytest.mark.asyncio
async def test_datasource_geom_config_is_valid() -> None:
    gene = TileGeneration(configure_logging=False)
    config = await gene.get_config(
        AnyioPath(str(Path(__file__).parent / "tilegeneration/test-geoms-datasource.yaml")),
        ignore_error=False,
    )

    assert "point_datasource" in config.config.get("layers", {})


def test_intersect_geometry_filter_can_be_disabled_per_layer() -> None:
    gene = Mock()
    filter_ = IntersectGeometryFilter(gene=gene)
    config = SimpleNamespace(
        config={
            "layers": {
                "point": {
                    "meta": True,
                    "geom_filter": False,
                },
            },
            "grids": {
                "swissgrid": {
                    "resolutions": [1],
                },
            },
        },
        file=AnyioPath("config.yaml"),
    )

    assert filter_.filter_tilecoord(cast("Any", config), Mock(), "point", "swissgrid") is True
    gene.get_grid.assert_not_called()
    gene.get_geoms.assert_not_called()


def test_normalize_bbox() -> None:
    assert normalize_bbox([6, 2, 1, 5]) == [1.0, 2.0, 6.0, 5.0]


def test_transform_bbox_normalizes_reversed_input() -> None:
    source = "+proj=longlat +datum=WGS84 +no_defs"
    destination = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +k=1 +units=m +no_defs"

    transformed = transform_bbox(source, destination, [8.0, 47.0, 7.5, 46.5])

    assert transformed[0] < transformed[2]
    assert transformed[1] < transformed[3]


def test_get_tile_matrix_limits_with_reversed_bbox() -> None:
    config = DatedConfig(
        cast(
            "tcc_configuration.Configuration",
            {
                "layers": {
                    "layer": {
                        "bbox": [560000.0, 180000.0, 550000.0, 170000.0],
                    },
                },
                "grids": {
                    "grid": {
                        "bbox": [420000.0, 30000.0, 900000.0, 350000.0],
                        "resolutions": [100.0],
                        "tile_size": 256,
                    },
                },
            },
        ),
        0,
        AnyioPath("config.yaml"),
    )

    limits = get_tile_matrix_limits(config, "layer", "grid")

    assert limits == [
        {
            "tile_matrix": "0",
            "min_tile_row": 6,
            "max_tile_row": 7,
            "min_tile_col": 5,
            "max_tile_col": 5,
        },
    ]


def test_get_tile_matrix_limits_with_px_buffer() -> None:
    config = DatedConfig(
        cast(
            "tcc_configuration.Configuration",
            {
                "layers": {
                    "layer": {
                        "bbox": [560000.0, 180000.0, 550000.0, 170000.0],
                        "px_buffer": 100,
                    },
                },
                "grids": {
                    "grid": {
                        "bbox": [420000.0, 30000.0, 900000.0, 350000.0],
                        "resolutions": [100.0],
                        "tile_size": 256,
                    },
                },
            },
        ),
        0,
        AnyioPath("config.yaml"),
    )

    limits = get_tile_matrix_limits(config, "layer", "grid")

    assert limits == [
        {
            "tile_matrix": "0",
            "min_tile_row": 6,
            "max_tile_row": 7,
            "min_tile_col": 4,
            "max_tile_col": 5,
        },
    ]


def test_get_geoms_respects_geometry_srid(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __init__(self, rows: list[tuple[bytes, int]]) -> None:
            self.rows = rows

        def execute(self, _sql: str) -> None:
            return

        def fetchall(self) -> list[tuple[bytes, int]]:
            return self.rows

        def close(self) -> None:
            return

    class FakeConnection:
        def __init__(self, rows: list[tuple[bytes, int]]) -> None:
            self.rows = rows

        def cursor(self) -> FakeCursor:
            return FakeCursor(self.rows)

        def close(self) -> None:
            return

    layer_projection = get_proj4_literal(21781)
    grid_projection = get_proj4_literal(2056)
    transformed_layer_bbox = transform_bbox(layer_projection, grid_projection, [550000, 170000, 560000, 180000])
    geom = box(
        transformed_layer_bbox[0] + 500,
        transformed_layer_bbox[1] + 500,
        transformed_layer_bbox[0] + 1000,
        transformed_layer_bbox[1] + 1000,
    )
    rows = [(geom.wkb, 2056)]

    monkeypatch.setattr(
        tilecloud_chain.psycopg2,
        "connect",
        lambda _connection: FakeConnection(rows),
    )

    gene = TileGeneration(options=Namespace(host="localhost"), configure_logging=False)
    config = DatedConfig(
        cast(
            "tcc_configuration.Configuration",
            {
                "layers": {
                    "layer": {
                        "bbox": [550000.0, 170000.0, 560000.0, 180000.0],
                        "proj4_literal": layer_projection,
                        "grids": ["grid_2056"],
                        "geoms": [
                            {
                                "sql": "the_geom AS geom FROM tests.point",
                                "connection": "postgresql://dummy",
                            },
                        ],
                    },
                },
                "grids": {
                    "grid_2056": {
                        "bbox": [2420000.0, 1030000.0, 2900000.0, 1350000.0],
                        "resolutions": [1000.0],
                        "tile_size": 256,
                        "proj4_literal": grid_projection,
                    },
                },
            },
        ),
        0,
        AnyioPath("config.yaml"),
    )

    geoms = gene.get_geoms(config, "layer", "grid_2056")

    assert not geoms[0].is_empty
    assert geoms[0].symmetric_difference(geom).area < 1e-5


class TestGenerate(CompareCase):
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
    async def test_postgresql_master_job_id_and_job_title_are_mutually_exclusive(self) -> None:
        await self.assert_cmd_exit_equals(
            cmd=(
                ".build/venv/bin/generate-tiles -c tilegeneration/test-postgresql.yaml "
                "--role master -l point --job-id 1 --job-title custom-title"
            ),
            main_func=generate.async_main,
        )

    @pytest.mark.asyncio
    async def test_get_hash(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            for d in ("-d", ""):
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} --get-hash 4/0/0 "
                    "-c tilegeneration/test.yaml -l point",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_get_wrong_hash(self) -> None:
        for d in ("-d", "-q"):
            with LogCapture("tilecloud_chain") as log_capture:
                await self.assert_cmd_exit_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} --get-hash 0/7/5 "
                    "-c tilegeneration/test.yaml -l all",
                    main_func=generate.async_main,
                )
                log_capture.check_present(
                    (
                        "tilecloud_chain",
                        "DEBUG",
                        "Error: image is not uniform.",
                    ),
                )

    @pytest.mark.asyncio
    async def test_hash_logger_ignores_hidden_rgb_on_transparent_pixels(self) -> None:
        class ImageStub:
            def convert(self, mode: str) -> "ImageStub":
                assert mode == "RGBA"
                return self

            def tobytes(self) -> bytes:
                return bytes((0, 0, 0, 0, 255, 255, 255, 0))

        out = StringIO()
        with patch("tilecloud_chain.Image.open", return_value=ImageStub()):
            await HashLogger("empty_tile_detection", out)(
                Tile(TileCoord(0, 0, 0), data=b"image", metadata={"layer": "test"})
            )

        assert "empty_tile_detection" in out.getvalue()

    @pytest.mark.asyncio
    async def test_get_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4 -l point",
                    main_func=generate.async_main,
                    expected="""Tile bounds: [425120,343600,426400,344880]
""",
                )
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4:+1/+1 -l point",
                    main_func=generate.async_main,
                    expected="""Tile bounds: [425120,343600,426400,344880]
    """,
                )
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test.yaml --get-bbox 4/4/4:+2/+2 -l point",
                    main_func=generate.async_main,
                    expected="""Tile bounds: [425120,342320,427680,344880]
    """,
                )
                log_capture.check()

    @pytest.mark.asyncio
    async def test_tile_option_metatile(self) -> None:
        for d in ("-d", ""):
            await self.assert_tiles_generated(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -q -c tilegeneration/test-nosns.yaml "
                    "-l point_hash --tile 0/0/0:+8/+8"
                ),
                main_func=generate.async_main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.png",
                tiles=[("point_hash", 0, 5, 7), ("point_hash", 0, 7, 4)],
            )

    @pytest.mark.asyncio
    async def test_tile_option_single_tile(self) -> None:
        for d in ("-d", ""):
            await self.assert_tiles_generated(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -q -c tilegeneration/test-nosns.yaml "
                    "-l polygon --tile 0/6/5"
                ),
                main_func=generate.async_main,
                directory="/tmp/tiles/",
                tiles_pattern="1.0.0/polygon/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=[(5, 6)],
            )

    @pytest.mark.asyncio
    async def test_tile_option_errors(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.assert_cmd_exit_equals(
                cmd=".build/venv/bin/generate-tiles -q -c tilegeneration/test-nosns.yaml --tile 0/0/0",
                main_func=generate.async_main,
            )
            await self.assert_cmd_exit_equals(
                cmd=(
                    ".build/venv/bin/generate-tiles -q -c tilegeneration/test-nosns.yaml "
                    "-l point_hash --tiles error.list --tile 0/0/0"
                ),
                main_func=generate.async_main,
            )
            log_capture.check_present(
                (
                    "tilecloud_chain.generate",
                    "ERROR",
                    "With --tile option you need to specify a layer",
                ),
                (
                    "tilecloud_chain.generate",
                    "ERROR",
                    "The --tile and --tiles options are mutually exclusive",
                ),
            )

    @pytest.mark.asyncio
    async def test_hash_mapnik(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "--get-hash 4/0/0 -c tilegeneration/test.yaml -l mapnik",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_hash_mapnik_grid(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "--get-hash 4/0/0 -c tilegeneration/test.yaml -l all",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_test_all(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -t 1",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_test_dimensions(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -t 1 "
                    "--dimensions DATE=2013",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_multigeom(self) -> None:
        with LogCapture("tilecloud_chain", level=30) as log_capture:
            await self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-multigeom.yaml",
                main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_zoom_identifier(self) -> None:
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
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 0",
                    main_func=generate.async_main,
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
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 1",
                    main_func=generate.async_main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png",
                    tiles=list(
                        zip(repeat("polygon2", len(x2)), repeat("0_2", len(x2)), x2, y2, strict=False),
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
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 1 -l polygon2 -z 2",
                    main_func=generate.async_main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_01/%s/%i/%i.png",
                    tiles=list(
                        zip(repeat("polygon2", len(x3)), repeat("0_1", len(x3)), x3, y3, strict=False),
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

    @pytest.mark.asyncio
    async def test_empty_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash --bbox 700000 250000 800000 300000",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_zoom(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash --zoom 1",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_zoom_range(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash --zoom 1-3",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_no_zoom(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=(
                        f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -l point_hash"
                    ),
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_py_buffer(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_px_buffer --zoom 0-2",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_zoom_list(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=(
                        f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                        "-l point_hash --zoom 0,2,3"
                    ),
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_layer_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0",
                    main_func=generate.async_main,
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

                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0"
                    " -b 550000 170000 560000 180000",
                    main_func=generate.async_main,
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

                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l polygon -z 0"
                    " -b 550000.0 170000.0 560000.0 180000.0",
                    main_func=generate.async_main,
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

                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml -l all -z 0",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_hash_generation(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_hash -z 0",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_mapnik(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik -z 0",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_mapnik_grid(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik_grid -z 0",
                    main_func=generate.async_main,
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
                with Path("/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/5/5.json").open() as f:
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
                with Path("/tmp/tiles/1.0.0/mapnik_grid/default/2012/swissgrid_5/0/6/5.json").open() as f:
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

    @pytest.mark.asyncio
    async def test_mapnik_grid_drop(self):
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l mapnik_grid_drop -z 0",
                    main_func=generate.async_main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/mapnik_grid_drop/default/2012/swissgrid_5/0/%i/%i.json",
                    tiles=((5, 7), (7, 4)),
                    regex=True,
                    expected=r"""The tile generation of layer 'mapnik_grid_drop' is finish
    Nb generated tiles: 12
    Nb tiles dropped: 10
    Nb tiles stored: 2
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: 768 o
    Time per tile: [0-9]+ ms
    Size per tile: 384 o

    """,
                )
                log_capture.check()

    @pytest.mark.asyncio
    async def test_not_authorised_user(self) -> None:
        for d in ("-d", "-q"):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_exit_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-authorised.yaml",
                    main_func=generate.async_main,
                )
                log_capture.check(
                    (
                        "tilecloud_chain.generate",
                        "ERROR",
                        "not authorized, authorized user is: www-data.",
                    ),
                )

    @pytest.mark.asyncio
    async def test_verbose(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.run_cmd(
                    cmd=f".build/venv/bin/generate-tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -t 2 -v -l polygon",
                    main_func=generate.async_main,
                )
                log_capture.check()

    @pytest.mark.asyncio
    async def test_time(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test.yaml --time 2 -l polygon",
                    main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_time_layer_bbox(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_cmd_equals(
                    cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test.yaml --time 2 -l all",
                    main_func=generate.async_main,
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
    #             main_func=generate.async_main,
    #             expected=r"""Daemonize with pid [0-9]*.""",
    #             regex=True)
    #         log_capture.check()

    def _touch(self, tiles_pattern: str, tiles: list[tuple[int, int]]) -> None:
        for tile in tiles:
            path = Path(tiles_pattern % tile)
            directory = path.parent
            if not directory.exists():
                directory.mkdir(parents=True)
            with path.open("w"):
                pass

    @pytest.mark.asyncio
    async def test_delete_meta(self) -> None:
        for d in ("-d", ""):
            if Path("/tmp/tiles/").exists():
                shutil.rmtree("/tmp/tiles/")
            self._touch(
                tiles_pattern="/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=list(product(range(12), range(16))),
            )
            await self.assert_tiles_generated_deleted(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash_no_meta -z 0"
                ),
                main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_delete_no_meta(self) -> None:
        for d in ("-d", ""):
            if Path("/tmp/tiles/").exists():
                shutil.rmtree("/tmp/tiles/")
            self._touch(
                tiles_pattern="/tmp/tiles/1.0.0/point_hash_no_meta/default/2012/swissgrid_5/0/%i/%i.png",
                tiles=list(product(range(12), range(16))),
            )
            await self.assert_tiles_generated_deleted(
                cmd=(
                    f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-nosns.yaml "
                    "-l point_hash_no_meta -z 0"
                ),
                main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_error_file_create(self) -> None:
        error_list_path = Path("error.list")
        if error_list_path.exists():
            error_list_path.unlink()
        await self.assert_main_except_equals(
            cmd=".build/venv/bin/generate-tiles -q -c tilegeneration/test-nosns.yaml -l point_error",
            main_func=generate.async_main,
            regex=True,
            get_error=True,
            expected=[
                [
                    "error.list",
                    "\n".join(  # noqa: FLY002
                        [
                            r"# \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] "
                            r"Start the layer 'point_error' generation",
                            r"0/0/0:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+?(?:\\n|\s)+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request "
                            r"settings\.(?:\\n|\s)*'",
                            r"0/0/8:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+?(?:\\n|\s)+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request "
                            r"settings\.(?:\\n|\s)*'",
                            r"0/8/0:\+8/\+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 "
                            r"grid=swissgrid_5 host=localhost layer=point_error # \[[0-9][0-9]-[0-9][0-9]-20[0-9][0-9] "
                            r"[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] 'WMS server error: URL: http:[^ ]+?(?:\\n|\s)+"
                            r"msWMSLoadGetMapParams\(\): "
                            r"WMS server error\. Invalid layer\(s\) given in the LAYERS parameter\. "
                            r"A layer might be disabled for this request\. Check wms/ows_enable_request "
                            r"settings\.(?:\\n|\s)*'",
                            "",
                        ],
                    ),
                ],
            ],
        )

    @pytest.mark.asyncio
    async def test_error_file_use(self) -> None:
        main_config_file = settings.main_config_file
        settings.main_config_file = AnyioPath("tilegeneration/test-nosns.yaml")

        try:
            error_list_path = Path("error.list")
            if error_list_path.exists():
                error_list_path.unlink()

            with error_list_path.open("w") as error_file:
                error_file.write(
                    "# comment\n"
                    "0/0/0:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5 "
                    "# comment\n"
                    "0/0/8:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5\n"
                    "0/8/0:+8/+8 config_file=tilegeneration/test-nosns.yaml dimension_DATE=2012 layer=point_hash grid=swissgrid_5\n",
                )

            await self.assert_tiles_generated(
                cmd=".build/venv/bin/generate-tiles -d --tiles error.list",
                main_func=generate.async_main,
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
            settings.main_config_file = main_config_file

    @pytest.mark.asyncio
    async def test_multy(self) -> None:
        for d in ("-v", ""):
            await self.assert_tiles_generated(
                cmd=f".build/venv/bin/generate-tiles {d} -c tilegeneration/test-multidim.yaml",
                main_func=generate.async_main,
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

    @pytest.mark.asyncio
    async def test_redis(self) -> None:
        RedisTileStore(sentinels=[["redis_sentinel", 26379]]).delete_all()
        await self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis.yaml --role master -l point",
            main_func=generate.async_main,
            regex=False,
            expected="""The tile generation of layer 'point (DATE=2012)' is finish
Nb of generated jobs: 6

""",
        )

        await self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis.yaml --status",
            main_func=controller.async_main,
            regex=False,
            expected="""Approximate number of tiles to generate: 6
Approximate number of generating tiles: 0
Tiles in error:
""",
        )

        await self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis.yaml --role slave",
            main_func=generate.async_main,
            regex=True,
            expected=r"""The tile generation is finish
Nb generated metatiles: 6
Nb metatiles dropped: 0
Nb generated tiles: 384
Nb tiles dropped: 0
Nb tiles stored: 384
Nb tiles in error: 0
Total time: 0:\d\d:\d\d
Total size: \d+ Kio
Time per tile: \d+ ms
Size per tile: \d+ o

""",
        )

        await self.assert_cmd_equals(
            cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis.yaml --status",
            main_func=controller.async_main,
            regex=False,
            expected="""Approximate number of tiles to generate: 0
Approximate number of generating tiles: 0
Tiles in error:
""",
        )

    @pytest.mark.asyncio
    async def test_redis_main_config(self) -> None:
        main_config_file = settings.main_config_file
        settings.main_config_file = AnyioPath("tilegeneration/test-redis-main.yaml")

        try:
            RedisTileStore(sentinels=[["redis_sentinel", 26379]]).delete_all()
            await self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis-project.yaml --role master -l point",
                main_func=generate.async_main,
                regex=False,
                expected="""The tile generation of layer 'point (DATE=2012)' is finish
    Nb of generated jobs: 6

    """,
            )

            await self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis-project.yaml --status",
                main_func=controller.async_main,
                regex=False,
                expected="""Approximate number of tiles to generate: 6
    Approximate number of generating tiles: 0
    Tiles in error:
    """,
            )

            await self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-redis-project.yaml --role slave",
                main_func=generate.async_main,
                regex=True,
                expected=r"""The tile generation is finish
    Nb generated metatiles: 6
    Nb metatiles dropped: 0
    Nb generated tiles: 384
    Nb tiles dropped: 0
    Nb tiles stored: 384
    Nb tiles in error: 0
    Total time: 0:\d\d:\d\d
    Total size: \d+ Kio
    Time per tile: \d+ ms
    Size per tile: \d+ o

    """,
            )

            await self.assert_cmd_equals(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/test-redis-project.yaml --status",
                main_func=controller.async_main,
                regex=False,
                expected="""Approximate number of tiles to generate: 0
    Approximate number of generating tiles: 0
    Tiles in error:
    """,
            )
        finally:
            settings.main_config_file = main_config_file

    @pytest.mark.asyncio
    async def test_webp(self) -> None:
        for d in ("-d", ""):
            with LogCapture("tilecloud_chain", level=30) as log_capture:
                await self.assert_tiles_generated(
                    cmd=f".build/venv/bin/generate_tiles {d} "
                    "-c tilegeneration/test-nosns.yaml -l point_webp --zoom 0",
                    main_func=generate.async_main,
                    directory="/tmp/tiles/",
                    tiles_pattern="1.0.0/%s/default/2012/swissgrid_5/%i/%i/%i.webp",
                    tiles=[("point_webp", 0, 7, 4)],
                    regex=True,
                    expected=r"""The tile generation of layer 'point_webp \(DATE=2012\)' is finish
    Nb generated metatiles: 1
    Nb metatiles dropped: 0
    Nb generated tiles: 1
    Nb tiles dropped: 0
    Nb tiles stored: 1
    Nb tiles in error: 0
    Total time: [0-9]+:[0-9][0-9]:[0-9][0-9]
    Total size: [234][0-9][0-9] o
    Time per tile: [0-9]+ ms
    Size per tile: [234][0-9][0-9] o

    """,
                )
                log_capture.check()
                with Path("/tmp/tiles/1.0.0/point_webp/default/2012/swissgrid_5/0/7/4.webp").open(
                    "rb",
                ) as file:
                    image = Image.open(file, formats=["WEBP"])
                    assert image.format == "WEBP"
