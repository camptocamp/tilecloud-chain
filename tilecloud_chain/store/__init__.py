from collections.abc import AsyncIterator, Callable
from typing import Any

from tilecloud import Tile, TileCoord, TileStore


class AsyncTileStore:
    """A tile store."""

    async def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        Attributes
        ----------
            tile: Tile

        """
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        Attributes
        ----------
            tile: Tile

        """
        raise NotImplementedError

    async def get_one(self, tile: Tile) -> Tile | None:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        Attributes
        ----------
            tile: Tile

        """
        raise NotImplementedError

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """
        Add data to the tiles, or return ``None`` if the tile is not in the store.

        Attributes
        ----------
            tiles: AsyncIterator[Tile]

        """
        del tiles
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable
        # async for tile in tiles:
        #     yield await self.get_one(tile)

    async def list(self) -> AsyncIterator[Tile]:
        """Generate all the tiles in the store, but without their data."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable

    async def put_one(self, tile: Tile) -> Tile:
        """
        Store ``tile`` in the store.

        Attributes
        ----------
            tile: Tile

        """
        raise NotImplementedError


class TileStoreWrapper(AsyncTileStore):
    """Wrap a TileStore."""

    def __init__(self, tile_store: TileStore) -> None:
        """Initialize."""
        self.tile_store = tile_store

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        return self.tile_store.__contains__(tile)

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        return self.tile_store.delete_one(tile)

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        return self.tile_store.get_one(tile)

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """See in superclass."""
        all_tiles = []
        all_tiles = [tile async for tile in tiles]
        for new_tile in self.tile_store.get(all_tiles):
            yield new_tile

    async def list(self) -> AsyncIterator[Tile]:
        """See in superclass."""
        for tile in self.tile_store.list():
            yield tile

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        return self.tile_store.put_one(tile)

    def __getattr__(self, item: str) -> Any:
        """See in superclass."""
        return getattr(self.tile_store, item)


class NoneTileStore(AsyncTileStore):
    """A tile store that does nothing."""

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        return tile

    async def list(self) -> AsyncIterator[Tile]:
        """See in superclass."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """See in superclass."""
        async for tile in tiles:
            yield tile


class CallWrapper:
    """Wrap a function call."""

    def __init__(self, function: Callable[[Tile], Tile | None]) -> None:
        """Initialize."""
        self.function = function

    async def __call__(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        return self.function(tile)


class AsyncTilesIterator:
    """An async iterator."""

    def __init__(self, tiles: list[Tile]) -> None:
        """Initialize."""
        self._tiles = tiles

    async def __call__(self) -> AsyncIterator[Tile]:
        """Async iterator of the tiles."""
        for tile in self._tiles:
            yield tile
