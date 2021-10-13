from itertools import chain, groupby, starmap
import logging
from typing import Callable, Dict, Iterable, Iterator, Optional, Tuple

from tilecloud import Tile, TileStore

logger = logging.getLogger(__name__)


class MultiTileStore(TileStore):
    """Redirect to the corresponding Tilestore for the layer and config file."""

    def __init__(self, get_store: Callable[[str, str], Optional[TileStore]]) -> None:
        """Initialize."""
        TileStore.__init__(self)
        self.get_store = get_store
        self.stores: Dict[Tuple[str, str], Optional[TileStore]] = {}

    def _get_store(self, config_file: str, layer: str) -> Optional[TileStore]:
        store = self.stores.get((config_file, layer))
        if store is None:
            store = self.get_store(config_file, layer)
            self.stores[(config_file, layer)] = store
        return store

    def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        Arguments:

            tile: Tile
        """
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        store = self._get_store(config_file, layer)
        assert store is not None
        return tile in store

    def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        Arguments:

            tile: Tile
        """
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        store = self._get_store(config_file, layer)
        assert store is not None
        return store.delete_one(tile)

    @staticmethod
    def list() -> Iterator[Tile]:
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
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        store = self._get_store(config_file, layer)
        assert store is not None
        return store.put_one(tile)

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        Arguments:

            tile: Tile
        """
        layer = tile.metadata["layer"]
        config_file = tile.metadata["config_file"]
        store = self._get_store(config_file, layer)
        assert store is not None
        return store.get_one(tile)

    def get(self, tiles: Iterable[Tile]) -> Iterator[Optional[Tile]]:
        """See in superclass."""

        def apply(key: Tuple[str, str], tiles: Iterator[Tile]) -> Iterable[Optional[Tile]]:
            store = self._get_store(*key)
            if store is None:
                return tiles
            return store.get(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        def apply(key: Tuple[str, str], tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(*key)
            assert store is not None
            return store.put(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def delete(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        def apply(key: Tuple[str, str], tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(*key)
            assert store is not None
            return store.delete(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    @staticmethod
    def _get_layer(tile: Tile) -> Tuple[str, str]:
        return (tile.metadata["config_file"], tile.metadata["layer"])
