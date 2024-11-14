"""A wrapper around a TileStore that adds timer metrics."""

import time
from collections.abc import Iterable, Iterator
from typing import Any, TypeVar, cast

from prometheus_client import Summary
from tilecloud import BoundingPyramid, Tile, TileStore

_OptionalTileOrNot = TypeVar("_OptionalTileOrNot", Tile | None, Tile)

_TILESTORE_OPERATION_SUMMARY = Summary(
    "tilecloud_chain_tilestore", "Number of tilestore contains", ["layer", "host", "store", "operation"]
)
_LEN_SUMMARY = Summary("tilecloud_chain_tilestore_len", "Number of tilestore len", ["store"])


class TimedTileStoreWrapper(TileStore):
    """A wrapper around a TileStore that adds timer metrics."""

    def __init__(self, tile_store: TileStore, store_name: str) -> None:
        """Initialize."""
        super().__init__()
        self._tile_store = tile_store
        self._store_name = store_name

    def _time_iteration(
        self, generator: Iterable[_OptionalTileOrNot], operation: str
    ) -> Iterator[_OptionalTileOrNot]:
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
                raise
            _TILESTORE_OPERATION_SUMMARY.labels(
                tile.metadata.get("layer", "none"),
                tile.metadata.get("host", "none"),
                self._store_name,
                operation,
            ).observe(time.perf_counter() - start)
            yield tile

    def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "contains",
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
        return self._time_iteration(self._tile_store.delete(tiles), "delete")

    def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"),
            tile.metadata.get("host", "none"),
            self._store_name,
            "delete_one",
        ).time():
            return self._tile_store.delete_one(tile)

    def list(self) -> Iterable[Tile]:
        """See in superclass."""
        return cast(Iterable[Tile], self._time_iteration(self._tile_store.list(), "list"))

    def get(self, tiles: Iterable[Tile | None]) -> Iterator[Tile | None]:
        """See in superclass."""
        return self._time_iteration(self._tile_store.get(tiles), "get")

    def get_all(self) -> Iterator[Tile | None]:
        """See in superclass."""
        return self._time_iteration(self._tile_store.get_all(), "get_all")

    def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name, "get_one"
        ).time():
            return self._tile_store.get_one(tile)

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        """See in superclass."""
        return cast(Iterator[Tile], self._time_iteration(self._tile_store.put(tiles), "put"))

    def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        with _TILESTORE_OPERATION_SUMMARY.labels(
            tile.metadata.get("layer", "none"), tile.metadata.get("host", "none"), self._store_name, "put_one"
        ).time():
            return self._tile_store.put_one(tile)

    def __getattr__(self, item: str) -> Any:
        """See in superclass."""
        return getattr(self._tile_store, item)

    def get_bounding_pyramid(self) -> BoundingPyramid:
        """See in superclass."""
        return self._tile_store.get_bounding_pyramid()

    def get_cheap_bounding_pyramid(self) -> BoundingPyramid | None:
        """See in superclass."""
        return self._tile_store.get_cheap_bounding_pyramid()

    def __str__(self) -> str:
        """Get string representation."""
        return f"tilecloud_chain.timedtilestore.TimedTileStoreWrapper: {self._tile_store}"
