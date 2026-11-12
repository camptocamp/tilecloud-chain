# Copyright (c) 2026 by Camptocamp
"""Async filesystem tile store."""

import errno
import logging
from collections.abc import AsyncIterator
from typing import Any

from anyio import Path
from tilecloud import Tile, TileLayout

from tilecloud_chain.error import ErrorContext, format_error
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


def _tile_error(exception: BaseException, tile: Tile, action: str) -> str:
    """Format an error of the filesystem tile store with the context of the tile."""
    return format_error(
        exception,
        ErrorContext(
            step=action,
            layer=tile.metadata.get("layer"),
            host=tile.metadata.get("host"),
        ),
    )


class FilesystemTileStore(AsyncTileStore):
    """Tiles stored in a filesystem, async version."""

    def __init__(self, tilelayout: TileLayout, **kwargs: Any) -> None:
        self.tilelayout = tilelayout
        self.content_type = kwargs.get("content_type")

    async def delete_one(self, tile: Tile) -> Tile:
        """Delete one tile."""
        try:
            filename = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Error while getting the filename to delete the tile %s", tile.tilecoord, exc_info=True
            )
            tile.error = _tile_error(exception, tile, "build the filename of the tile to delete")
            return tile
        path = Path(filename)
        if await path.exists():
            await path.unlink()
        return tile

    async def get_one(self, tile: Tile) -> Tile | None:
        """Get one tile."""
        try:
            filename = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.warning("Error while getting the filename of the tile %s", tile.tilecoord, exc_info=True)
            tile.error = _tile_error(exception, tile, "build the filename of the tile to get")
            return tile
        path = Path(filename)
        try:
            async with await path.open("rb") as file:
                tile.data = await file.read()
        except OSError as exception:
            if exception.errno == errno.ENOENT:
                return None
            # a filesystem error (permission, disk full, ...) has to be reported as a tile error
            _LOGGER.warning(
                "Error while reading the file %s of tile %s", filename, tile.tilecoord, exc_info=True
            )
            tile.error = _tile_error(exception, tile, f"read the file {filename}")
            return tile
        if self.content_type is not None:
            tile.content_type = self.content_type
        return tile

    async def list(self) -> AsyncIterator[Tile]:
        """List all tiles."""
        top = getattr(self.tilelayout, "prefix", ".")
        top_path = Path(top)
        async for path in top_path.glob("**/*"):
            if await path.is_file():
                tilecoord = self.tilelayout.tilecoord(str(path))
                if tilecoord:
                    yield Tile(tilecoord, path=str(path))

    async def put_one(self, tile: Tile) -> Tile:
        """Put one tile."""
        assert isinstance(tile.data, bytes)
        try:
            filename = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.warning("Error while getting the filename of the tile %s", tile.tilecoord, exc_info=True)
            tile.error = _tile_error(exception, tile, "build the filename of the tile to store")
            return tile
        path = Path(filename)
        await path.parent.mkdir(parents=True, exist_ok=True)
        async with await path.open("wb") as file:
            await file.write(tile.data)
        return tile

    async def __contains__(self, tile: Tile) -> bool:
        try:
            filename = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.warning("Error while getting the filename of the tile %s", tile.tilecoord, exc_info=True)
            tile.error = _tile_error(exception, tile, "build the filename of the tile to check")
            return False
        return await Path(filename).exists()
