from typing import Any, Iterable, Iterator, List, Optional, TypeVar, cast

from c2cwsgiutils import stats

from tilecloud import BoundingPyramid, Tile, TileStore

OPTIONAL_TILE_OR_NOT = TypeVar("OPTIONAL_TILE_OR_NOT", Optional[Tile], Tile)


class TimedTileStoreWrapper(TileStore):
    """A wrapper around a TileStore that adds timer metrics."""

    def __init__(self, tile_store: TileStore, stats_name: str) -> None:
        """Initialise."""
        super().__init__()
        self._tile_store = tile_store
        self._stats_name = stats_name

    def _get_stats_name(self, func_name: str, tile: Optional[Tile] = None) -> List[str]:
        if tile and "layer" in tile.metadata:
            return [self._stats_name, tile.metadata["layer"], func_name]
        else:
            return [self._stats_name, func_name]

    def _time_iteration(
        self, generator: Iterable[OPTIONAL_TILE_OR_NOT], func_name: str
    ) -> Iterator[OPTIONAL_TILE_OR_NOT]:
        while True:
            timer = stats.timer()
            try:
                tile = next(generator)  # type: ignore
            except StopIteration:
                break
            except RuntimeError as exception:
                if isinstance(exception.__cause__, StopIteration):
                    # since python 3.7, a StopIteration is wrapped in a RuntimeError (PEP 479)
                    break
                else:
                    raise
            timer.stop(self._get_stats_name(func_name, tile))
            yield tile

    def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        with stats.timer_context(self._get_stats_name("contains", tile)):
            return self._tile_store.__contains__(tile)

    def __len__(self) -> int:
        """See in superclass."""
        with stats.timer_context(self._get_stats_name("len")):
            return self._tile_store.__len__()

    def delete(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""
        return self._time_iteration(self._tile_store.delete(tiles), "delete")

    def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with stats.timer_context(self._get_stats_name("delete_one", tile)):
            return self._tile_store.delete_one(tile)

    def list(self) -> Iterable[Tile]:
        """See in superclass."""
        return cast(Iterable[Tile], self._time_iteration(self._tile_store.list(), "list"))

    def get(self, tiles: Iterable[Tile]) -> Iterator[Optional[Tile]]:
        """See in superclass."""
        return self._time_iteration(self._tile_store.get(tiles), "get")

    def get_all(self) -> Iterator[Optional[Tile]]:
        """See in superclass."""
        return self._time_iteration(self._tile_store.get_all(), "get_all")

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """See in superclass."""
        with stats.timer_context(self._get_stats_name("get_one", tile)):
            return self._tile_store.get_one(tile)

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""
        return cast(Iterator[Tile], self._time_iteration(self._tile_store.put(tiles), "put"))

    def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with stats.timer_context(self._get_stats_name("put_one", tile)):
            return self._tile_store.put_one(tile)

    def __getattr__(self, item: str) -> Any:
        """See in superclass."""
        return getattr(self._tile_store, item)

    def get_bounding_pyramid(self) -> BoundingPyramid:
        """See in superclass."""
        return self._tile_store.get_bounding_pyramid()

    def get_cheap_bounding_pyramid(self) -> Optional[BoundingPyramid]:
        """See in superclass."""
        return self._tile_store.get_cheap_bounding_pyramid()

    def __str__(self) -> str:
        """Get string representation."""
        return f"tilecloud_chain.timedtilestore.TimedTileStoreWrapper: {self._tile_store}"
