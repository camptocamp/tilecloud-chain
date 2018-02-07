from itertools import chain, groupby, starmap

from tilecloud import TileStore


class MultiTileStore(TileStore):
    def __init__(self, stores):
        TileStore.__init__(self)
        self._stores = stores

    def _get_store(self, layer):
        assert layer is not None
        result = self._stores.get(layer) if layer is not None else self._default_store
        return result

    def __contains__(self, tile):
        """
        Return true if this store contains ``tile``.

        :param tile: Tile
        :type tile: :class:`Tile`

        :rtype: bool

        """
        layer = self._get_layer(tile)
        return tile in self._get_store(layer)

    def delete_one(self, tile):
        """
        Delete ``tile`` and return ``tile``.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        assert layer is not None
        store = self._get_store(layer)
        assert store is not None
        return store.delete_one(tile)

    @staticmethod
    def list():
        """
        Generate all the tiles in the store, but without their data.

        :rtype: iterator

        """
        # Too dangerous to list all tiles in all stores. Return an empty iterator instead
        while False:
            yield

    def put_one(self, tile):
        """
        Store ``tile`` in the store.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        return self._get_store(layer).put_one(tile)

    def get_one(self, tile):
        """
        Add data to ``tile``, or return ``None`` if ``tile`` is not in the store.

        :param tile: Tile
        :type tile: :class:`Tile` or ``None``

        :rtype: :class:`Tile` or ``None``

        """
        layer = self._get_layer(tile)
        return self._get_store(layer).get_one(tile)

    def get(self, tiles):
        def apply(layer, tiles):
            store = self._get_store(layer)
            return tiles if store is None else store.get(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def put(self, tiles):
        def apply(layer, tiles):
            return self._get_store(layer).put(tiles) if layer is not None else None

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    def delete(self, tiles):
        def apply(layer, tiles):
            return self._get_store(layer).delete(tiles)

        return chain.from_iterable(starmap(apply, groupby(tiles, self._get_layer)))

    @staticmethod
    def _get_layer(tile):
        if tile:
            return tile.metadata['layer']
        else:
            return None
