"""Tests for the URL tile store."""

import logging
from unittest.mock import patch

import aiohttp
import pytest

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
