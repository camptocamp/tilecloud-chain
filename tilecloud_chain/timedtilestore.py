import time
from typing import Any, Iterable, Iterator, List, Optional, TypeVar, cast

from prometheus_client import Summary

from tilecloud import BoundingPyramid, Tile, TileStore

_OPTIONAL_TILE_OR_NOT = TypeVar("_OPTIONAL_TILE_OR_NOT", Optional[Tile], Tile)

_CONTAINS_SUMMARY = Summary(
    "tilecloud_chain_tilestore_contains", "Number of tilestore contains", ["layer", "host", "store"]
)
_LEN_SUMMARY = Summary("tilecloud_chain_tilestore_len", "Number of tilestore len", ["store"])
_DELETE_SUMMARY = Summary(
    "tilecloud_chain_tilestore_delete", "Number of tilestore delete all", ["layer", "host", "store"]
)
_DELETE_ONE_SUMMARY = Summary(
    "tilecloud_chain_tilestore_delete_one", "Number of tilestore delete", ["layer", "host", "store"]
)
_GET_ALL_SUMMARY = Summary(
    "tilecloud_chain_tilestore_get_all", "Number of tilestore get all", ["layer", "host", "store"]
)
_GET_SUMMARY = Summary("tilecloud_chain_tilestore_get", "Number of tilestore get", ["layer", "host", "store"])
_GET_ONE_SUMMARY = Summary(
    "tilecloud_chain_tilestore_get_one", "Number of tilestore get one", ["layer", "host", "store"]
)
_PUT_SUMMARY = Summary("tilecloud_chain_tilestore_put", "Number of tilestore put", ["layer", "host", "store"])
_PUT_ONE_SUMMARY = Summary(
    "tilecloud_chain_tilestore_put_one", "Number of tilestore put one", ["layer", "host", "store"]
)
_LIST_SUMMARY = Summary(
    "tilecloud_chain_tilestore_list", "Number of tilestore list", ["layer", "host", "store"]
)


class TimedTileStoreWrapper(TileStore):
    """A wrapper around a TileStore that adds timer metrics."""

    def __init__(self, tile_store: TileStore, store_name: str) -> None:
        """Initialize."""
        super().__init__()
        self._tile_store = tile_store
        self._store_name = store_name

    def _get_stats_name(self, func_name: str, tile: Optional[Tile] = None) -> List[str]:
        if tile and "layer" in tile.metadata:
            return [self._store_name, tile.metadata["layer"], func_name]
        else:
            return [self._store_name, func_name]

    def _time_iteration(
        self, generator: Iterable[_OPTIONAL_TILE_OR_NOT], summary: Summary
    ) -> Iterator[_OPTIONAL_TILE_OR_NOT]:
        while True:
            start = time.perf_counter()
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
            summary.labels(
                tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name
            ).observe(time.perf_counter() - start)
            yield tile

    def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""

        with _CONTAINS_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name
        ).time():
            return self._tile_store.__contains__(tile)

    def __len__(self) -> int:
        """See in superclass."""

        with _LEN_SUMMARY.labels(
            self._store_name,
        ).time():
            return self._tile_store.__len__()

    def delete(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        return self._time_iteration(self._tile_store.delete(tiles), _DELETE_SUMMARY)

    def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""

        with _DELETE_ONE_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name
        ).time():
            return self._tile_store.delete_one(tile)

    def list(self) -> Iterable[Tile]:
        """See in superclass."""

        return cast(Iterable[Tile], self._time_iteration(self._tile_store.list(), _LIST_SUMMARY))

    def get(self, tiles: Iterable[Optional[Tile]]) -> Iterator[Optional[Tile]]:
        """See in superclass."""

        return self._time_iteration(self._tile_store.get(tiles), _GET_SUMMARY)

    def get_all(self) -> Iterator[Optional[Tile]]:
        """See in superclass."""

        return self._time_iteration(self._tile_store.get_all(), _GET_ALL_SUMMARY)

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """See in superclass."""

        with _GET_ONE_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name
        ).time():
            return self._tile_store.get_one(tile)

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""

        return cast(Iterator[Tile], self._time_iteration(self._tile_store.put(tiles), _PUT_SUMMARY))

    def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""

        with _PUT_ONE_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name
        ).time():
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
