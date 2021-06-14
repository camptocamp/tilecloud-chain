from itertools import chain, groupby, starmap
from typing import Dict, Iterable, Iterator, Optional

from tilecloud import Tile, TileStore


class MultiTileStore(TileStore):
    def __init__(self, stores: Dict[str, Optional[TileStore]]) -> None:
        TileStore.__init__(self)
        self._stores = stores

    def _get_store(self, layer: Optional[str]) -> Optional[TileStore]:
        assert layer is not None
        return self._stores.get(layer)

    def __contains__(self, tile: Tile) -> bool:
        """
        Return true if this store contains ``tile``.

        :param tile: Tile
        :type tile: :class:`Tile`

        :rtype: bool

        """
        layer = self._get_layer(tile)
        store = self._get_store(layer)
        assert store is not None
        return tile in store

    def delete_one(self, tile: Tile) -> Tile:
        """
        Delete ``tile`` and return ``tile``.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        store = self._get_store(layer)
        assert store is not None
        return store.delete_one(tile)

    @staticmethod
    def list() -> Iterator[Tile]:
        """
        Generate all the tiles in the store, but without their data.

        :rtype: iterator

        """
        # Too dangerous to list all tiles in all stores. Return an empty iterator instead
        while False:
            yield

    def put_one(self, tile: Tile) -> Tile:
        """
        Store ``tile`` in the store.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        store = self._get_store(layer)
        assert store is not None
        return store.put_one(tile)

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        store = self._get_store(layer)
        assert store is not None
        return store.get_one(tile)

    def get(self, tiles: Iterable[Tile]) -> Iterator[Optional[Tile]]:
        def apply(layer: str, tiles: Iterator[Tile]) -> Iterable[Optional[Tile]]:
            store = self._get_store(layer)
            return tiles if store is None else store.get(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        def apply(layer: str, tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(layer)
            assert store is not None
            return store.put(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def delete(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        def apply(layer: str, tiles: Iterator[Tile]) -> Iterator[Tile]:
            store = self._get_store(layer)
            assert store is not None
            return store.delete(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    @staticmethod
    def _get_layer(tile: Optional[Tile]) -> Optional[str]:
        if tile:
            return tile.metadata["layer"]
        else:
            return None
