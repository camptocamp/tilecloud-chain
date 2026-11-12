# Copyright (c) 2026 by Camptocamp
import os
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from testfixtures import LogCapture
from tilecloud import Tile, TileCoord

from tilecloud_chain import Run, controller, generate
from tilecloud_chain.error import ErrorContext, TileGenerationError, format_error
from tilecloud_chain.tests import CompareCase

if TYPE_CHECKING:
    from tilecloud_chain import TileGeneration


class TestError(CompareCase):
    def setup_method(self) -> None:  # noqa
        self.maxDiff = None

    @classmethod
    def setup_class(cls):  # noqa
        os.chdir(Path(__file__).parent)

    @classmethod
    def teardown_class(cls):  # noqa
        os.chdir(Path(__file__).parent.parent.parent)

    @pytest.mark.asyncio
    async def test_resolution(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_resolutions.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_resolutions.yaml"),
                ("tilecloud_chain", "ERROR", "The resolution 0.1 * resolution_scale 5 is not an integer."),
            )

    @pytest.mark.asyncio
    async def test_mapnik_grid_meta(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_mapnik_grid_meta.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                (
                    "tilecloud_chain",
                    "DEBUG",
                    "Get config for file tilegeneration/wrong_mapnik_grid_meta.yaml",
                ),
                (
                    "tilecloud_chain",
                    "ERROR",
                    "The layer 'b' is of type Mapnik/Grid, that can't support matatiles.",
                ),
            )

    @pytest.mark.asyncio
    async def test_type(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -v -c tilegeneration/wrong_type.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_type.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_type.yaml:10:10 grids.swissgrid_2.srs: {} is not of type 'string' (rule: properties.grids.additionalProperties.properties.srs.type)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3.srs: 'epsg:21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:12:5 grids.swissgrid_3: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4.srs: 'epsg21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:14:5 grids.swissgrid_4: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:15:16 grids.swissgrid_5: 'srs' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'resolutions' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:17:15 grids.swissgrid!: 'srs' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_type.yaml:22:3 layers: 'hi!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.propertyNames.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!.wmts_style: 'yo!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.wmts_style.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!.wmts_style: 'yo!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.wmts_style.pattern)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'layers' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_type.yaml:23:5 layers.hi!: 'url' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.default: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.default.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.default: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.default.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.name: 'DATE!' does not match '(?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.name.pattern)
-- tilegeneration/wrong_type.yaml:25:9 layers.hi!.dimensions.0.name: 'DATE!' does not match '(?i)^(?!(SERVICE|VERSION|REQUEST|LAYERS|STYLES|SRS|CRS|BBOX|WIDTH|HEIGHT|FORMAT|BGCOLOR|TRANSPARENT|SLD|EXCEPTIONS|SALT))[a-z0-9_\\\\-~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.name.pattern)
-- tilegeneration/wrong_type.yaml:27:19 layers.hi!.dimensions.0.generate.0: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.generate.items.pattern)
-- tilegeneration/wrong_type.yaml:27:19 layers.hi!.dimensions.0.generate.0: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.generate.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.0: '2005!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.0: '2005!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.1: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.1: '2010!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.2: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:28:17 layers.hi!.dimensions.0.values.2: '2012!' does not match '^[a-zA-Z0-9_\\\\-\\\\+~\\\\.]+$' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.pattern)
-- tilegeneration/wrong_type.yaml:29:9 layers.hi!.dimensions.1.default: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.default.type)
-- tilegeneration/wrong_type.yaml:29:9 layers.hi!.dimensions.1.default: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.default.type)
-- tilegeneration/wrong_type.yaml:2:3 grids.swissgrid_6: None is not of type 'object' (rule: properties.grids.additionalProperties.type)
-- tilegeneration/wrong_type.yaml:2:3 grids: 'swissgrid!' does not match '^[a-zA-Z0-9_\\\\-~\\\\.]+$' (rule: properties.grids.propertyNames.pattern)
-- tilegeneration/wrong_type.yaml:31:19 layers.hi!.dimensions.1.generate.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.generate.items.type)
-- tilegeneration/wrong_type.yaml:31:19 layers.hi!.dimensions.1.generate.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.generate.items.type)
-- tilegeneration/wrong_type.yaml:32:17 layers.hi!.dimensions.1.values.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.0.properties.dimensions.items.properties.values.items.type)
-- tilegeneration/wrong_type.yaml:32:17 layers.hi!.dimensions.1.values.0: 1 is not of type 'string' (rule: properties.layers.additionalProperties.anyOf.1.properties.dimensions.items.properties.values.items.type)
-- tilegeneration/wrong_type.yaml:3:5 grids.swissgrid_1.resolution_scale: 5.5 is not of type 'integer' (rule: properties.grids.additionalProperties.properties.resolution_scale.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.0: 'a' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.1: 'b' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:5:11 grids.swissgrid_1.bbox.2: 'c' is not of type 'number' (rule: properties.grids.additionalProperties.properties.bbox.items.type)
-- tilegeneration/wrong_type.yaml:6:10 grids.swissgrid_1.srs: ['EPSG:21781'] is not of type 'string' (rule: properties.grids.additionalProperties.properties.srs.type)""",  # noqa
                ),
            )

    @pytest.mark.asyncio
    async def test_zoom_errors(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-tiles -c tilegeneration/test-nosns.yaml -l point --zoom 4,10",
                main_func=generate.async_main,
            )
            log_capture.check_present(
                (
                    "tilecloud_chain",
                    "WARNING",
                    "zoom 10 is greater than the maximum zoom 4 of grid swissgrid_5 of layer point, ignored.",
                ),
                (
                    "tilecloud_chain",
                    "WARNING",
                    (
                        "zoom 4 corresponds to resolution 5 "
                        "is smaller than the 'min_resolution_seed' 10 of layer point, ignored."
                    ),
                ),
            )

    @pytest.mark.asyncio
    async def test_wrong_srs_auth(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs_auth.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_srs_auth.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs_auth.yaml:3:5 grids.swissgrid_01.srs: 'toto:21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",  # noqa
                ),
            )

    @pytest.mark.asyncio
    async def test_wrong_srs_id(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs_id.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_srs_id.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs_id.yaml:3:5 grids.swissgrid_01.srs: 'EPSG:21781a' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",  # noqa
                ),
            )

    @pytest.mark.asyncio
    async def test_wrong_srs(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_srs.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_srs.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_srs.yaml:3:5 grids.swissgrid_01.srs: 'EPSG21781' does not match '^EPSG:[0-9]+$' (rule: properties.grids.additionalProperties.properties.srs.pattern)""",
                ),
            )

    @pytest.mark.asyncio
    async def test_wrong_map(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_map.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_map.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_map.yaml:3:5 layers.test.empty_tile_detection: 'test' is not of type 'object' (rule: properties.layers.additionalProperties.anyOf.0.properties.empty_tile_detection.type)
-- tilegeneration/wrong_map.yaml:3:5 layers.test.empty_tile_detection: 'test' is not of type 'object' (rule: properties.layers.additionalProperties.anyOf.1.properties.empty_tile_detection.type)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'extension' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'layers' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'mime_type' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'url' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'wmts_style' is a required property (rule: properties.layers.additionalProperties.anyOf.0.required)
-- tilegeneration/wrong_map.yaml:3:5 layers.test: 'wmts_style' is a required property (rule: properties.layers.additionalProperties.anyOf.1.required)""",
                ),
            )

    @pytest.mark.asyncio
    async def test_wrong_sequence(self) -> None:
        with LogCapture("tilecloud_chain") as log_capture:
            await self.run_cmd(
                cmd=".build/venv/bin/generate-controller -c tilegeneration/wrong_sequence.yaml",
                main_func=controller.async_main,
                get_error=True,
            )
            log_capture.check(
                ("tilecloud_chain", "DEBUG", "Get config for file tilegeneration/wrong_sequence.yaml"),
                (
                    "tilecloud_chain",
                    "ERROR",
                    """The config file is invalid:
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test.resolutions: 'test' is not of type 'array' (rule: properties.grids.additionalProperties.properties.resolutions.type)
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test: 'bbox' is a required property (rule: properties.grids.additionalProperties.required)
-- tilegeneration/wrong_sequence.yaml:3:5 grids.test: 'srs' is a required property (rule: properties.grids.additionalProperties.required)""",
                ),
            )


@pytest.mark.asyncio
async def test_run_delete_metatile_on_error() -> None:
    class QueueStore:
        def __init__(self) -> None:
            self.deleted: list[Tile] = []

        async def delete_one(self, tile: Tile) -> Tile:
            self.deleted.append(tile)
            return tile

    queue_store = QueueStore()

    class DummyGeneration:
        def __init__(self, queue_store: QueueStore) -> None:
            self.queue_store = queue_store
            self.options = SimpleNamespace(debug=False)
            self.maxconsecutive_errors = False

        async def get_main_config(self):
            return SimpleNamespace(config={"generation": {}})

    async def identity(tile: Tile) -> Tile:
        return tile

    run = Run(cast("TileGeneration", DummyGeneration(queue_store)), [identity])
    run.max_consecutive_errors = None

    metatile = Tile(TileCoord(2, 2, 1))
    metatile.postgresql_id = 42
    metatile.elapsed_togenerate = 1

    child_tile = Tile(
        TileCoord(2, 2, 1),
        metadata={
            "config_file": "/etc/tilegeneration/config.yaml",
            "dimension_DATE": "20230811",
            "grid": "3857",
            "host": "localhost",
            "job_id": 3,
            "layer": "osm-wmts",
        },
    )
    child_tile.metatile = metatile
    child_tile.error = "boom"

    await run(child_tile)

    assert queue_store.deleted == [metatile]
    assert metatile.error == "boom"


@pytest.mark.asyncio
async def test_run_delete_tile_on_error_without_metatile() -> None:
    class QueueStore:
        def __init__(self) -> None:
            self.deleted: list[Tile] = []

        async def delete_one(self, tile: Tile) -> Tile:
            self.deleted.append(tile)
            return tile

    queue_store = QueueStore()

    class DummyGeneration:
        def __init__(self, queue_store: QueueStore) -> None:
            self.queue_store = queue_store
            self.options = SimpleNamespace(debug=False)
            self.maxconsecutive_errors = False

        async def get_main_config(self):
            return SimpleNamespace(config={"generation": {}})

    async def identity(tile: Tile) -> Tile:
        return tile

    run = Run(cast("TileGeneration", DummyGeneration(queue_store)), [identity])
    run.max_consecutive_errors = None

    tile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    tile.error = "boom"

    await run(tile)

    assert queue_store.deleted == [tile]


def test_format_error_empty_message() -> None:
    """The type of an exception without message is displayed."""
    assert format_error(TimeoutError()) == "TimeoutError: <no message>"


def test_format_error_exception() -> None:
    """The type of the exception is added to its message."""
    assert format_error(RuntimeError("Session is closed")) == "RuntimeError: Session is closed"


def test_format_error_string() -> None:
    """A string error is displayed as is."""
    assert format_error("WMS server error: boom") == "WMS server error: boom"


def test_format_error_cause() -> None:
    """The cause of the error is displayed."""
    error = ConnectionError("Cannot connect")
    wrapper = OSError("Failed")
    wrapper.__cause__ = error
    assert format_error(wrapper) == "OSError: Failed\nCaused by: ConnectionError: Cannot connect"


def test_format_error_note() -> None:
    """The notes added to the exception are displayed."""
    error = ValueError("bad value")
    error.add_note("the first note")
    assert format_error(error) == "ValueError: bad value\nNote: the first note"


def test_format_error_context() -> None:
    """The context of the error is displayed."""
    message = format_error(
        TimeoutError(),
        ErrorContext(
            url="http://example.com/tile.png",
            duration=1.5,
            step="get tile",
            layer="point",
            host="mapserver",
            hint="the server did not answer",
        ),
    )
    assert message == (
        "TimeoutError: <no message>\n"
        "URL: http://example.com/tile.png (after 1.500 s)\n"
        "Step: get tile\n"
        "Layer: point\n"
        "Host: mapserver\n"
        "Hint: the server did not answer"
    )


def test_format_error_duration_without_url() -> None:
    """The elapsed time is displayed alone when there is no URL."""
    assert format_error(ValueError("bad"), ErrorContext(duration=2.0)) == (
        "ValueError: bad\nElapsed: 2.000 s"
    )


def test_format_error_truncated() -> None:
    """A very long error is truncated."""
    message = format_error("a" * 5000)
    assert len(message) == 2015
    assert message.endswith("... (truncated)")


def test_format_error_already_formatted() -> None:
    """An error already formatted is not formatted twice."""
    error = TileGenerationError("RuntimeError: Session is closed\nURL: http://example.com")
    assert format_error(error) == "RuntimeError: Session is closed\nURL: http://example.com"


@pytest.mark.asyncio
async def test_run_error_with_the_step_context() -> None:
    """An exception raised by a step of the generation is reported with its context."""

    class QueueStore:
        def __init__(self) -> None:
            self.deleted: list[Tile] = []

        async def delete_one(self, tile: Tile) -> Tile:
            self.deleted.append(tile)
            return tile

    queue_store = QueueStore()

    class DummyGeneration:
        def __init__(self, queue_store: QueueStore) -> None:
            self.queue_store = queue_store
            self.options = SimpleNamespace(debug=False)
            self.maxconsecutive_errors = False

        async def get_main_config(self):
            return SimpleNamespace(config={"generation": {}})

    async def failing(tile: Tile) -> Tile:
        raise TimeoutError  # an exception with an empty message, like an aiohttp timeout

    failing.time_message = "Get the tiles"  # type: ignore[attr-defined]

    run = Run(cast("TileGeneration", DummyGeneration(queue_store)), [failing])
    run.max_consecutive_errors = None

    tile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    result = await run(tile)

    assert result is tile
    assert isinstance(tile.error, TileGenerationError)
    assert tile.error.__cause__ is not None
    assert str(tile.error) == (
        "TimeoutError: <no message>\nStep: Get the tiles\nLayer: osm-wmts\nHost: localhost"
    )
