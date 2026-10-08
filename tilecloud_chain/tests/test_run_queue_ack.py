# Copyright (c) 2026 by Camptocamp
"""Tests for the queue acknowledgement of tiles dropped during the generation."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from tilecloud import Tile, TileCoord

from tilecloud_chain import Run

if TYPE_CHECKING:
    from tilecloud_chain import TileGeneration


class _RecordingQueueStore:
    """Queue store double recording the released tiles."""

    def __init__(self) -> None:
        self.deleted: list[Tile] = []

    async def delete_one(self, tile: Tile) -> Tile:
        self.deleted.append(tile)
        return tile


class _DummyGeneration:
    def __init__(self, queue_store: _RecordingQueueStore | None) -> None:
        self.queue_store = queue_store
        self.options = SimpleNamespace(debug=False)
        self.maxconsecutive_errors = False

    async def get_main_config(self):
        return SimpleNamespace(config={"generation": {}})


@pytest.mark.asyncio
async def test_ack_metatile_on_drop() -> None:
    """A meta tile dropped by the source (no data) must be released from the queue."""
    queue_store = _RecordingQueueStore()

    async def drop(tile: Tile) -> Tile | None:
        return None

    run = Run(cast("TileGeneration", _DummyGeneration(queue_store)), [drop])
    run.max_consecutive_errors = None

    metatile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    metatile.postgresql_id = 42

    assert await run(metatile) is None
    assert queue_store.deleted == [metatile]
    assert not metatile.error


@pytest.mark.asyncio
async def test_ack_child_tile_on_drop() -> None:
    """A dropped child tile decrements the meta tile countdown and releases it at zero."""
    queue_store = _RecordingQueueStore()

    async def drop(tile: Tile) -> Tile | None:
        return None

    run = Run(cast("TileGeneration", _DummyGeneration(queue_store)), [drop])
    run.max_consecutive_errors = None

    metatile = Tile(TileCoord(2, 2, 1))
    metatile.postgresql_id = 42
    metatile.elapsed_togenerate = 1

    child_tile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    child_tile.metatile = metatile

    assert await run(child_tile) is None
    assert metatile.elapsed_togenerate == 0
    assert queue_store.deleted == [metatile]


@pytest.mark.asyncio
async def test_no_double_ack_on_drop_when_already_acked() -> None:
    """A tile that already released the queue (e.g. HashDropper) must not be released twice."""
    queue_store = _RecordingQueueStore()

    async def drop_and_ack(tile: Tile) -> Tile | None:
        tile.queue_acked = True
        return None

    run = Run(cast("TileGeneration", _DummyGeneration(queue_store)), [drop_and_ack])
    run.max_consecutive_errors = None

    metatile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    metatile.postgresql_id = 42

    assert await run(metatile) is None
    assert queue_store.deleted == []


@pytest.mark.asyncio
async def test_no_ack_on_drop_without_queue_store() -> None:
    """Without a queue store (e.g. local role) a drop is silent and does nothing."""

    async def drop(tile: Tile) -> Tile | None:
        return None

    run = Run(cast("TileGeneration", _DummyGeneration(None)), [drop])
    run.max_consecutive_errors = None

    metatile = Tile(TileCoord(2, 2, 1), metadata={"layer": "osm-wmts", "host": "localhost"})
    metatile.postgresql_id = 42

    assert await run(metatile) is None
