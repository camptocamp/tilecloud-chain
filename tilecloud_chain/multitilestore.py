# Copyright (c) 2026 by Camptocamp
"""Redirect to the corresponding Tilestore for the layer and config file."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from anyio import Path
from tilecloud import Tile

from tilecloud_chain.store import AsyncTilesIterator, AsyncTileStore

logger = logging.getLogger(__name__)

pending_closes: set[asyncio.Task[None]] = set()


@dataclass
class _DatedStore:
    """Store the date and the store."""

    mtime: float
    store: AsyncTileStore


async def close_store(store: AsyncTileStore) -> None:
    """Close a tile store, waiting for its requests in flight and ignoring the errors."""
    try:
        await store.close()
    except Exception:
        # an error while closing a store must not prevent closing the other ones
        logger.warning("Error while closing tile store %s", store, exc_info=True)


def close_store_later(store: AsyncTileStore) -> None:
    """
    Close the given store without waiting for it.

    The store is replaced by a new configuration: closing it in the current request would delay
    the generation of all the tiles of that layer, then it's closed in the background, and it
    waits itself for the requests it still has in flight.
    """
    task = asyncio.create_task(close_store(store))
    pending_closes.add(task)
    task.add_done_callback(pending_closes.discard)


class MultiTileStore(AsyncTileStore):
    """Redirect to the corresponding Tilestore for the layer and config file."""

    def __init__(
        self,
        get_store: Callable[[Path, str, str | None], Awaitable[AsyncTileStore | None]],
    ) -> None:
        """Initialize."""
        self.get_store = get_store
        self.stores: dict[tuple[Path, str, str], _DatedStore | None] = {}

    async def _get_store(self, config_file: Path, layer: str, grid_name: str) -> AsyncTileStore | None:
        stat_info = await config_file.stat()
        mtime = stat_info.st_mtime
        key = (config_file, layer, grid_name)
        dated_store = self.stores.get(key)
        if dated_store is not None and dated_store.mtime != mtime:
            close_store_later(dated_store.store)
            del self.stores[key]
            dated_store = None
        if dated_store is None:
            tile_store = await self.get_store(config_file, layer, grid_name)
            if tile_store is not None:
                dated_store = _DatedStore(mtime, tile_store)
                self.stores[key] = dated_store
        return dated_store.store if dated_store is not None else None

    async def _get_store_tile(self, tile: Tile) -> AsyncTileStore | None:
        """Return the store corresponding to the tile."""
        layer = tile.metadata["layer"]
        grid = tile.metadata["grid"]
        config_file = Path(tile.metadata["config_file"])
        return await self._get_store(config_file, layer, grid)

    async def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        Arguments:
            tile: Tile
        """
        store = await self._get_store_tile(tile)
        assert store is not None
        return tile in store

    async def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        Arguments:
            tile: Tile
        """
        store = await self._get_store_tile(tile)
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
        store = await self._get_store_tile(tile)
        assert store is not None
        return await store.put_one(tile)

    async def get_one(self, tile: Tile) -> Tile | None:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        Arguments:
            tile: Tile
        """
        store = await self._get_store_tile(tile)
        assert store is not None
        return await store.get_one(tile)

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """
        Add data to the tiles, or return ``None`` if the tile is not in the store.

        Arguments:
            tiles: AsyncIterator[Tile]
        """
        async for tile in tiles:
            store = await self._get_store_tile(tile)
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

    async def close(self) -> None:
        """Close all cached tile stores, in parallel, as each of them waits for its own requests."""
        stores = [dated_store.store for dated_store in self.stores.values() if dated_store is not None]
        self.stores.clear()
        async with asyncio.TaskGroup() as task_group:
            for store in stores:
                task_group.create_task(close_store(store))
        # finish to close the stores which were replaced by a new configuration during the generation
        if pending_closes:
            await asyncio.gather(*list(pending_closes))

    @staticmethod
    def _get_layer(tile: Tile | None) -> tuple[str, str]:
        assert tile is not None
        return (tile.metadata["config_file"], tile.metadata["layer"])
