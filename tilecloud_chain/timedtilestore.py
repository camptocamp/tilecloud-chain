"""A wrapper around a TileStore that adds timer metrics."""

import time
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar

from prometheus_client import Summary
from tilecloud import Tile

from tilecloud_chain.store import AsyncTileStore

_OptionalTileOrNot = TypeVar("_OptionalTileOrNot", Tile | None, Tile)

_TILESTORE_OPERATION_SUMMARY = Summary(
    "tilecloud_chain_tilestore",
    "Number of tilestore contains",
    ["layer", "host", "store", "operation"],
)


class TimedTileStoreWrapper(AsyncTileStore):
    """A wrapper around a TileStore that adds timer metrics."""

    def __init__(self, tile_store: AsyncTileStore, store_name: str) -> None:
        """Initialize."""
        super().__init__()
        self._tile_store = tile_store
        self._store_name = store_name

    async def _time_iteration(self) -> AsyncGenerator[_OptionalTileOrNot]:
        while True:
            start = time.perf_counter()
            try:
                tile = await anext(self._tile_store.list())
            except StopAsyncIteration:
                break
            except RuntimeError as exception:
                if isinstance(exception.__cause__, StopAsyncIteration):
                    # since python 3.7, a StopIteration is wrapped in a RuntimeError (PEP 479)
                    break
                raise
            _TILESTORE_OPERATION_SUMMARY.labels(
                tile.metadata.get("layer", "none"),
                tile.metadata.get("host", "none"),
                self._store_name,
                "list",
            ).observe(time.perf_counter() - start)
            yield tile

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "contains",
        ).time():
            return await self._tile_store.__contains__(tile)

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "delete_one",
        ).time():
            return await self._tile_store.delete_one(tile)

    async def list(self) -> AsyncIterator[Tile]:
        """See in superclass."""
        async for tile in self._time_iteration():
            yield tile

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "get_one",
        ).time():
            return await self._tile_store.get_one(tile)

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "put_one",
        ).time():
            return await self._tile_store.put_one(tile)

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels("none", "none", self._store_name, "get").time():
            async for tile in self._tile_store.get(tiles):
                yield tile

    def __getattr__(self, item: str) -> Any:
        """See in superclass."""
        return getattr(self._tile_store, item)

    def __str__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}({self._store_name}: {self._tile_store}"

    def __repr__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}({self._store_name}: {self._tile_store!r})"
