"""Redirect to the corresponding Tilestore for the layer and config file."""

import logging
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from itertools import chain, groupby, starmap
from pathlib import Path

from tilecloud import Tile, TileStore

logger = logging.getLogger(__name__)


@dataclass
class _DatedStore:
    """Store the date and the store."""

    mtime: float
    store: TileStore


class MultiTileStore(TileStore):
    """Redirect to the corresponding Tilestore for the layer and config file."""

    def __init__(self, get_store: Callable[[str, str], TileStore | None]) -> None:
        """Initialize."""
        TileStore.__init__(self)
        self.get_store = get_store
        self.stores: dict[tuple[str, str], _DatedStore | None] = {}

    def _get_store(self, config_file: str, layer: str) -> TileStore | None:
        mtime = Path(config_file).stat().st_mtime
        store = self.stores.get((config_file, layer))
        if store is not None and store.mtime != mtime:
            store = None
        if store is None:
            tile_store = self.get_store(config_file, layer)
            if tile_store is not None:
                store = _DatedStore(mtime, tile_store)
                self.stores[(config_file, layer)] = store
        return store.store if store is not None else None

    def _get_store_tile(self, tile: Tile) -> TileStore | None:
        """Return the store corresponding to the tile."""
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        return self._get_store(config_file, layer)

    def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return tile in store

    def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return store.delete_one(tile)

    def list(self) -> Iterator[Tile]:
        """Generate all the tiles in the store, but without their data."""
        # Too dangerous to list all tiles in all stores. Return an empty iterator instead
        while False:
            yield

    def put_one(self, tile: Tile) -> Tile:
        """
        Store ``tile`` in the store.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return store.put_one(tile)

    def get_one(self, tile: Tile) -> Tile | None:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        Arguments:
            tile: Tile
        """
        store = self._get_store_tile(tile)
        assert store is not None
        return store.get_one(tile)

    def get(self, tiles: Iterable[Tile | None]) -> Iterator[Tile | None]:
        """See in superclass."""

        def apply(key: tuple[str, str], tiles: Iterator[Tile]) -> Iterable[Tile | None]:
            store = self._get_store(*key)
            if store is None:
                return tiles
            return store.get(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        def apply(key: tuple[str, str], tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(*key)
            assert store is not None
            return store.put(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def delete(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        def apply(key: tuple[str, str], tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(*key)
            assert store is not None
            return store.delete(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def __str__(self) -> str:
        """Return a string representation of the object."""
        stores = {str(store) for store in self.stores.values()}
        keys = {f"{config_file}:{layer}" for config_file, layer in self.stores}
        return f"{self.__class__.__name__}({', '.join(stores)} - {', '.join(keys)})"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        stores = {repr(store) for store in self.stores.values()}
        keys = {f"{config_file}:{layer}" for config_file, layer in self.stores}
        return f"{self.__class__.__name__}({', '.join(stores)} - {', '.join(keys)})"

    @staticmethod
    def _get_layer(tile: Tile | None) -> tuple[str, str]:
        assert tile is not None
        return (tile.metadata["config_file"], tile.metadata["layer"])
