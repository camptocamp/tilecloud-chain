"""Redirect to the corresponding Tilestore for the layer and config file."""

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

from tilecloud import Tile

from tilecloud_chain.store import AsyncTilesIterator, AsyncTileStore

logger = logging.getLogger(__name__)


@dataclass
class _DatedStore:
    """Store the date and the store."""

    mtime: float
    store: AsyncTileStore


class MultiTileStore(AsyncTileStore):
    """Redirect to the corresponding Tilestore for the layer and config file."""

    def __init__(self, get_store: Callable[[Path, str, str | None], AsyncTileStore | None]) -> None:
        """Initialize."""
        self.get_store = get_store
        self.stores: dict[tuple[Path, str, str], _DatedStore | None] = {}

    def _get_store(self, config_file: Path, layer: str, grid_name: str) -> AsyncTileStore | None:
        config_path = Path(config_file)
        mtime = config_path.stat().st_mtime
        store = self.stores.get((config_file, layer, grid_name))
        if store is not None and store.mtime != mtime:
            store = None
        if store is None:
            tile_store = self.get_store(config_file, layer, grid_name)
            if tile_store is not None:
                store = _DatedStore(mtime, tile_store)
                self.stores[(config_file, layer, grid_name)] = store
        return store.store if store is not None else None

    def _get_store_tile(self, tile: Tile) -> AsyncTileStore | None:
        """Return the store corresponding to the tile."""
        layer = tile.metadata["layer"]
        grid = tile.metadata["grid"]
        config_file = Path(tile.metadata["config_file"])
        return self._get_store(config_file, layer, grid)

    async def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return tile in store

    async def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return await store.delete_one(tile)

    async def list(self) -> AsyncIterator[Tile]:
        """Generate all the tiles in the store, but without their data."""
        # Too dangerous to list all tiles in all stores. Return an empty iterator instead
        while False:
            yield

    async def put_one(self, tile: Tile) -> Tile:
        """
        Store ``tile`` in the store.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return await store.put_one(tile)

    async def get_one(self, tile: Tile) -> Tile | None:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return await store.get_one(tile)

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """
        Add data to the tiles, or return ``None`` if the tile is not in the store.

        Arguments:
            tiles: AsyncIterator[Tile]
        """
        async for tile in tiles:
            store = self._get_store_tile(tile)
            assert store is not None, f"No store found for tile {tile.tilecoord} {tile.formated_metadata}"

            async for new_tile in store.get(AsyncTilesIterator([tile])()):
                yield new_tile

    def __str__(self) -> str:
        """Return a string representation of the object."""
        stores = {str(store) for store in self.stores.values()}
        keys = {f"{config_file}:{layer}:{grid}" for config_file, layer, grid in self.stores}
        return f"{self.__class__.__name__}({', '.join(stores)} - {', '.join(keys)})"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        stores = {repr(store) for store in self.stores.values()}
        keys = {f"{config_file}:{layer}:{grid}" for config_file, layer, grid in self.stores}
        return f"{self.__class__.__name__}({', '.join(stores)} - {', '.join(keys)})"

    @staticmethod
    def _get_layer(tile: Tile | None) -> tuple[str, str]:
        assert tile is not None
        return (tile.metadata["config_file"], tile.metadata["layer"])
