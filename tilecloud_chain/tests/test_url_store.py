# Copyright (c) 2026 by Camptocamp
"""Tests for the URL tile store."""

import logging
from unittest.mock import patch

import aiohttp
import pytest
from tilecloud import Tile, TileCoord, TileLayout

from tilecloud_chain.settings import settings
from tilecloud_chain.store.url import URLTileStore


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
                patch.object(store._session, "get") as mock_get,
            ):
                mock_get.return_value.__aenter__.return_value.status = 404
                tile = Tile(TileCoord(0, 0, 0))
                await store.get_one(tile)
            semaphore = store._hosts_semaphore["example.com"]
            assert semaphore._value == 5
        finally:
            settings.host_concurrent = original_host_concurrent
