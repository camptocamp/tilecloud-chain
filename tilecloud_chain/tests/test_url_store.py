# Copyright (c) 2026 by Camptocamp
"""Tests for the URL tile store."""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from anyio import Path as AnyPath
from tilecloud import Tile, TileCoord, TileLayout

from tilecloud_chain.multitilestore import MultiTileStore
from tilecloud_chain.settings import settings
from tilecloud_chain.store.url import URLTileStore


def _response_cm(
    status: int,
    reason: str = "",
    text: str = "",
    headers: dict[str, Any] | None = None,
    data: bytes = b"",
) -> MagicMock:
    """Build an aiohttp response usable as an async context manager mock."""
    response = MagicMock()
    response.status = status
    response.reason = reason
    response.headers = headers if headers is not None else {}
    response.text = AsyncMock(return_value=text)
    response.read = AsyncMock(return_value=data)
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    return context_manager


def _build_store() -> URLTileStore:
    """Build a store which gets all its tiles on the same URL."""
    tile_layout = TileLayout()
    tile_layout.filename = lambda tilecoord, metadata=None: "http://example.com/0/0/0.png"  # type: ignore[method-assign]
    return URLTileStore([tile_layout])


class _SlowResponseContext:
    """An async context manager which stays in the request until it's released, answering 204."""

    def __init__(self, entered: asyncio.Event, release: asyncio.Event) -> None:
        self._entered = entered
        self._release = release
        self.response = MagicMock()
        self.response.status = 204
        self.response.headers = {}

    async def __aenter__(self) -> MagicMock:
        self._entered.set()
        await self._release.wait()
        return self.response

    async def __aexit__(self, *args: object) -> None:
        """Nothing to clean in the mocked response."""


class TestURLTileStore:
    """Tests for the URLTileStore class."""

    @pytest.mark.asyncio
    async def test_close_handles_client_connection_error(self) -> None:
        """Test that close() catches ClientConnectionError gracefully."""
        store = URLTileStore([])
        with patch.object(store._session, "close", side_effect=aiohttp.ClientConnectionError):
            await store.close()

    @pytest.mark.asyncio
    async def test_close_handles_timeout_error(self) -> None:
        """Test that close() catches TimeoutError gracefully."""
        store = URLTileStore([])
        with patch.object(store._session, "close", side_effect=TimeoutError):
            await store.close()

    @pytest.mark.asyncio
    async def test_close_logs_warning_on_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that close() logs a warning on error."""
        store = URLTileStore([])
        caplog.set_level(logging.WARNING)
        with patch.object(store._session, "close", side_effect=aiohttp.ClientConnectionError):
            await store.close()
        assert "Ignored error during aiohttp session close" in caplog.text

    @pytest.mark.asyncio
    async def test_host_concurrent_fallback(self) -> None:
        """Test that TILECLOUD_CHAIN__HOST_CONCURRENT is used as fallback."""
        store = _build_store()
        original_host_concurrent = settings.host_concurrent
        settings.host_concurrent = 5
        try:
            with (
                patch.object(store, "_get_hosts_limit", return_value={}),
                patch.object(store._session, "get", return_value=_response_cm(204)),
            ):
                tile = Tile(TileCoord(0, 0, 0))
                await store.get_one(tile)
            semaphore = store._hosts_semaphore["example.com"]
            assert semaphore._value == 5
        finally:
            settings.host_concurrent = original_host_concurrent

    @pytest.mark.asyncio
    async def test_get_one_204_returns_none(self) -> None:
        """A 204 (No Content) is a legitimate empty response: the tile is dropped."""
        store = _build_store()
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(store._session, "get", return_value=_response_cm(204)),
        ):
            tile = Tile(TileCoord(0, 0, 0))
            assert await store.get_one(tile) is None

    @pytest.mark.asyncio
    async def test_get_one_404_sets_error(self) -> None:
        """A 404 from the source is reported as a tile error, not silently dropped."""
        store = _build_store()
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(
                store._session,
                "get",
                return_value=_response_cm(404, "Not Found", "map not found"),
            ),
        ):
            tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point", "host": "example.com"})
            result = await store.get_one(tile)
        assert result is tile
        assert isinstance(result.error, str)
        assert "404" in result.error
        assert "map not found" in result.error
        assert "URL: http://example.com/0/0/0.png" in result.error

    @pytest.mark.asyncio
    async def test_session_timeout_is_configured(self) -> None:
        """The session is created with the configured timeouts."""
        store = URLTileStore([])
        try:
            assert store._session.timeout.total == settings.http.timeout
            assert store._session.timeout.connect == settings.http.connect_timeout
        finally:
            await store.close()

    @pytest.mark.asyncio
    async def test_get_one_reports_the_connector_closed(self) -> None:
        """A closed connector is reported with the URL and an explanation."""
        store = _build_store()
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(
                store._session,
                "get",
                side_effect=aiohttp.ClientConnectionError("Connector is closed."),
            ),
        ):
            tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point", "host": "example.com"})
            result = await store.get_one(tile)
        await store.close()

        assert result is tile
        assert isinstance(result.error, str)
        assert "ClientConnectionError: Connector is closed." in result.error
        assert "URL: http://example.com/0/0/0.png" in result.error
        assert "Layer: point" in result.error
        assert "Host: example.com" in result.error
        assert "Hint: the HTTP session of the tile store was already closed" in result.error

    @pytest.mark.asyncio
    async def test_get_one_reports_the_session_closed(self) -> None:
        """The runtime error raised by aiohttp on a closed session is reported."""
        store = _build_store()
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(store._session, "get", side_effect=RuntimeError("Session is closed")),
        ):
            tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point", "host": "example.com"})
            result = await store.get_one(tile)
        await store.close()

        assert result is tile
        assert isinstance(result.error, str)
        assert "RuntimeError: Session is closed" in result.error
        assert "Hint: the HTTP session of the tile store was already closed" in result.error

    @pytest.mark.asyncio
    async def test_get_one_reports_the_timeout(self) -> None:
        """A timeout, which has an empty message, is reported with its type and the URL."""
        store = _build_store()
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(store._session, "get", side_effect=TimeoutError),
        ):
            tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point", "host": "example.com"})
            result = await store.get_one(tile)
        await store.close()

        assert result is tile
        assert isinstance(result.error, str)
        assert result.error.startswith("TimeoutError: <no message>\n")
        assert "URL: http://example.com/0/0/0.png" in result.error

    @pytest.mark.asyncio
    async def test_get_one_on_a_closed_store(self) -> None:
        """A request done after the store was closed is reported as an error."""
        store = _build_store()
        with patch.object(store, "_get_hosts_limit", return_value={}):
            await store.close()
            tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point", "host": "example.com"})
            result = await store.get_one(tile)

        assert result is tile
        assert isinstance(result.error, str)
        assert "Tile store is closed" in result.error
        assert "URL: http://example.com/0/0/0.png" in result.error

    @pytest.mark.asyncio
    async def test_close_waits_for_the_requests_in_flight(self) -> None:
        """The session is closed only once the requests in flight are finished."""
        store = _build_store()

        entered = asyncio.Event()
        release = asyncio.Event()
        context_manager = _SlowResponseContext(entered, release)

        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(store._session, "get", return_value=context_manager),
            patch.object(store._session, "close", wraps=store._session.close) as close,
        ):
            request = asyncio.create_task(
                store.get_one(Tile(TileCoord(0, 0, 0), metadata={"layer": "point"}))
            )
            await entered.wait()

            closing = asyncio.create_task(store.close())
            await asyncio.sleep(0)
            assert close.await_count == 0

            release.set()
            await request
            await closing
            assert close.await_count == 1

    @pytest.mark.asyncio
    async def test_close_forces_after_the_grace_period(self, caplog: pytest.LogCaptureFixture) -> None:
        """The session is closed even if a request is still running after the grace period."""
        store = _build_store()

        entered = asyncio.Event()
        release = asyncio.Event()
        context_manager = _SlowResponseContext(entered, release)

        original_grace_period = settings.http.close_grace_period
        settings.http.close_grace_period = 0.01
        caplog.set_level(logging.WARNING)
        try:
            with (
                patch.object(store, "_get_hosts_limit", return_value={}),
                patch.object(store._session, "get", return_value=context_manager),
                patch.object(store._session, "close", wraps=store._session.close) as close,
            ):
                request = asyncio.create_task(
                    store.get_one(Tile(TileCoord(0, 0, 0), metadata={"layer": "point"}))
                )
                await entered.wait()
                await store.close()
                assert close.await_count == 1
                release.set()
                await request
        finally:
            settings.http.close_grace_period = original_grace_period

        assert "requests still in flight after" in caplog.text


@pytest.mark.asyncio
async def test_replaced_store_does_not_fail_the_requests_in_flight(tmp_path: Path) -> None:
    """A store replaced by a new configuration does not break the requests it still has in flight."""
    config_file = tmp_path / "config.yaml"
    config_file.touch()
    stores: list[URLTileStore] = []

    async def get_store(_config_file: AnyPath, _layer: str, _grid: str | None) -> URLTileStore:
        store = _build_store()
        stores.append(store)
        return store

    multi_store = MultiTileStore(get_store)
    first_store = await multi_store._get_store(AnyPath(str(config_file)), "point", "grid")  # noqa: SLF001
    assert isinstance(first_store, URLTileStore)

    entered = asyncio.Event()
    release = asyncio.Event()
    tile = Tile(TileCoord(0, 0, 0), metadata={"layer": "point"})
    with (
        patch.object(first_store, "_get_hosts_limit", return_value={}),
        patch.object(first_store._session, "get", return_value=_SlowResponseContext(entered, release)),
    ):
        request = asyncio.create_task(first_store.get_one(tile))
        await entered.wait()

        # new configuration file, then the store is replaced and the old one is closed
        os.utime(config_file, (time.time() + 5, time.time() + 5))
        second_store = await multi_store._get_store(AnyPath(str(config_file)), "point", "grid")  # noqa: SLF001
        assert isinstance(second_store, URLTileStore)
        assert second_store is not first_store
        assert not first_store._session.closed

        release.set()
        assert await request is None
        assert tile.error is None

        await multi_store.close()

    assert first_store._session.closed
    assert second_store._session.closed
