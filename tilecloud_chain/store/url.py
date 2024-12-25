import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Any

import aiohttp
from tilecloud import BoundingPyramid, Tile, TileCoord, TileLayout

from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


class URLTileStore(AsyncTileStore):
    """A tile store that reads and writes tiles from a formatted URL."""

    def __init__(
        self,
        tilelayouts: Iterable[TileLayout],
        headers: Any | None = None,
        allows_no_contenttype: bool = False,
        bounding_pyramid: BoundingPyramid | None = None,
    ) -> None:
        self._allows_no_contenttype = allows_no_contenttype
        self._tilelayouts = tuple(tilelayouts)
        self._bounding_pyramid = bounding_pyramid
        self._session = aiohttp.ClientSession()
        if headers is not None:
            self._session.headers.update(headers)

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        if tile is None:
            return None
        if self._bounding_pyramid is not None and tile.tilecoord not in self._bounding_pyramid:
            return None
        tilelayout = self._tilelayouts[hash(tile.tilecoord) % len(self._tilelayouts)]
        try:
            url = tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.warning("Error while getting tile %s", tile, exc_info=True)
            tile.error = exception
            return tile

        _LOGGER.info("GET %s", url)
        try:
            async with self._session.get(url) as response:
                if response.status in (404, 204):
                    _LOGGER.debug("Got empty tile from %s: %s", url, response.status)
                    return None
                tile.content_encoding = response.headers.get("Content-Encoding")
                tile.content_type = response.headers.get("Content-Type")
                if response.status < 300:
                    if response.status != 200:
                        tile.error = (
                            f"URL: {url}\nUnsupported status code {response.status}: {response.reason}"
                        )
                    if tile.content_type:
                        if tile.content_type.startswith("image/"):
                            tile.data = await response.read()
                        else:
                            tile.error = f"URL: {url}\n{await response.text()}"
                    else:
                        if self._allows_no_contenttype:
                            tile.data = await response.read()
                        else:
                            tile.error = f"URL: {url}\nThe Content-Type header is missing"

                else:
                    tile.error = f"URL: {url}\n{response.status}: {response.reason}\n{response.text}"
        except aiohttp.ClientError as exception:
            _LOGGER.warning("Error while getting tile %s", tile, exc_info=True)
            tile.error = exception
        return tile

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        raise NotImplementedError()

    async def list(self) -> AsyncGenerator[Tile]:
        """See in superclass."""
        raise NotImplementedError()
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError()

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError()
