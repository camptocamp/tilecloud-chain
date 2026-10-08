# Copyright (c) 2026 by Camptocamp
"""Tests for the URL tile store."""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from tilecloud import Tile, TileCoord, TileLayout

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
        tile_layout = TileLayout()
        tile_layout.filename = lambda tc, md: "http://example.com/0/0/0.png"
        store = URLTileStore([tile_layout])
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
        tile_layout = TileLayout()
        tile_layout.filename = lambda tc, md: "http://example.com/0/0/0.png"
        store = URLTileStore([tile_layout])
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(store._session, "get", return_value=_response_cm(204)),
        ):
            tile = Tile(TileCoord(0, 0, 0))
            assert await store.get_one(tile) is None

    @pytest.mark.asyncio
    async def test_get_one_404_sets_error(self) -> None:
        """A 404 from the source is reported as a tile error, not silently dropped."""
        tile_layout = TileLayout()
        tile_layout.filename = lambda tc, md: "http://example.com/0/0/0.png"
        store = URLTileStore([tile_layout])
        with (
            patch.object(store, "_get_hosts_limit", return_value={}),
            patch.object(
                store._session,
                "get",
                return_value=_response_cm(404, "Not Found", "map not found"),
            ),
        ):
            tile = Tile(TileCoord(0, 0, 0))
            result = await store.get_one(tile)
        assert result is tile
        assert isinstance(result.error, str)
        assert "404" in result.error
        assert "map not found" in result.error
