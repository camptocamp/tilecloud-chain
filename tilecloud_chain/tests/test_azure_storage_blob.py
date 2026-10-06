# Copyright (c) 2026 by Camptocamp
"""Tests for the Azure storage blob tile store."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from tilecloud import Tile, TileCoord, TileLayout

from tilecloud_chain.store.azure_storage_blob import AzureStorageBlobTileStore


def _build_store(dry_run: bool = False, exists: bool = True) -> tuple[AzureStorageBlobTileStore, MagicMock]:
    """Build a store on top of a mocked Azure container client."""
    tile_layout = TileLayout()
    tile_layout.filename = lambda tilecoord, metadata=None: "0/0/0.png"
    container_client = MagicMock()
    blob_client = container_client.get_blob_client.return_value
    blob_client.exists = AsyncMock(return_value=exists)
    blob_client.delete_blob = AsyncMock()
    store = AzureStorageBlobTileStore(tile_layout, container_client=container_client, dry_run=dry_run)
    return store, blob_client


class TestAzureStorageBlobTileStore:
    """Tests for the AzureStorageBlobTileStore class."""

    @pytest.mark.asyncio
    async def test_delete_one_awaits_the_azure_calls(self) -> None:
        """Test that delete_one() awaits exists() and delete_blob()."""
        store, blob_client = _build_store()

        tile = await store.delete_one(Tile(TileCoord(0, 0, 0)))

        assert tile.error is None
        blob_client.exists.assert_awaited_once()
        blob_client.delete_blob.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_one_of_a_missing_blob(self) -> None:
        """Test that delete_one() does not delete a blob that does not exist."""
        store, blob_client = _build_store(exists=False)

        tile = await store.delete_one(Tile(TileCoord(0, 0, 0)))

        assert tile.error is None
        blob_client.exists.assert_awaited_once()
        blob_client.delete_blob.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_one_in_dry_run(self) -> None:
        """Test that delete_one() does not touch Azure in dry run mode."""
        store, blob_client = _build_store(dry_run=True)

        tile = await store.delete_one(Tile(TileCoord(0, 0, 0)))

        assert tile.error is None
        blob_client.exists.assert_not_awaited()
        blob_client.delete_blob.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_one_on_error(self) -> None:
        """Test that delete_one() reports the error on the tile."""
        store, blob_client = _build_store()
        error = RuntimeError("Azure is down")
        blob_client.delete_blob = AsyncMock(side_effect=error)

        tile = await store.delete_one(Tile(TileCoord(0, 0, 0)))

        assert tile.error is error
        blob_client.delete_blob.assert_awaited_once()
