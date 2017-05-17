# -*- coding: utf-8 -*-
# pragma: no cover

import logging

from tilecloud import Tile
from tilecloud.store.mapnik_ import MapnikTileStore


logger = logging.getLogger(__name__)


class MapnikDropActionTileStore(MapnikTileStore):
    def __init__(self, store=None, queue_store=None, count=None, **kwargs):
        self.store = store
        self.queue_store = queue_store
        self.count = count or []
        MapnikTileStore.__init__(self, **kwargs)

    def get_one(self, tile):
        result = MapnikTileStore.get_one(self, tile)
        if result is None:
            if self.store is not None:
                if tile.tilecoord.n != 1:  # pragma: no cover
                    for tilecoord in tile.tilecoord:
                        self.store.delete_one(Tile(tilecoord))
                else:
                    self.store.delete_one(tile)
            logger.info("The tile {} is dropped".format(str(tile.tilecoord)))
            if hasattr(tile, 'metatile'):  # pragma: no cover
                tile.metatile.elapsed_togenerate -= 1
                if tile.metatile.elapsed_togenerate == 0 and self.queue_store is not None:
                    self.queue_store.delete_one(tile.metatile)
            elif self.queue_store is not None:  # pragma: no cover
                self.queue_store.delete_one(tile)

            for count in self.count:
                count()
        return result
