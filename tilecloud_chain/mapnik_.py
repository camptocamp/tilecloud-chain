import logging
from typing import Any, Callable, List, Optional

from tilecloud import Tile, TileStore
from tilecloud.store.mapnik_ import MapnikTileStore

logger = logging.getLogger(__name__)


class MapnikDropActionTileStore(MapnikTileStore):
    """MapnikTileStore with drop action if the generated tile is empty."""

    def __init__(
        self,
        store: Optional[TileStore] = None,
        queue_store: Optional[TileStore] = None,
        count: Optional[List[Callable[[Optional[Tile]], Any]]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize."""
        self.store = store
        self.queue_store = queue_store
        self.count = count or []
        MapnikTileStore.__init__(self, **kwargs)

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """See in superclass."""
        result = MapnikTileStore.get_one(self, tile)
        if result is None:
            if self.store is not None:
                if tile.tilecoord.n != 1:
                    for tilecoord in tile.tilecoord:
                        self.store.delete_one(Tile(tilecoord))
                else:
                    self.store.delete_one(tile)
            logger.info("The tile %s %s is dropped", tile.tilecoord, tile.formated_metadata)
            if hasattr(tile, "metatile"):
                metatile: Tile = tile.metatile  # type: ignore
                metatile.elapsed_togenerate -= 1  # type: ignore
                if metatile.elapsed_togenerate == 0 and self.queue_store is not None:  # type: ignore
                    self.queue_store.delete_one(metatile)
            elif self.queue_store is not None:
                self.queue_store.delete_one(tile)

            for count in self.count:
                count(None)
        return result
