import asyncio
import json
import logging
import os
import pkgutil
import urllib.parse
from collections.abc import AsyncGenerator, Iterable
from pathlib import Path
from typing import Any, cast

import aiohttp
import jsonschema_validator
from ruamel.yaml import YAML
from tilecloud import BoundingPyramid, Tile, TileCoord, TileLayout

from tilecloud_chain import host_limit
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


class URLTileStore(AsyncTileStore):
    """A tile store that reads and writes tiles from a formatted URL."""

    def __init__(
        self,
        tile_layouts: Iterable[TileLayout],
        headers: Any | None = None,
        allows_no_contenttype: bool = False,
        bounding_pyramid: BoundingPyramid | None = None,
    ) -> None:
        self._allows_no_contenttype = allows_no_contenttype
        self._tile_layouts = tuple(tile_layouts)
        self._bounding_pyramid = bounding_pyramid
        self._session = aiohttp.ClientSession()
        self._hosts_semaphore: dict[str, asyncio.Semaphore] = {}
        self._hosts_limit: host_limit.HostLimit = {}
        if headers is not None:
            self._session.headers.update(headers)
        host_limit_path = Path(
            os.environ.get(
                "TILEGENERATION_HOSTS_LIMIT",
                "/etc/tilegeneration/hosts_limit.yaml",
            ),
        )
        if host_limit_path.exists():
            yaml = YAML(typ="safe")
            with host_limit_path.open(encoding="utf-8") as f:
                self._hosts_limit = yaml.load(f)

                schema_data = pkgutil.get_data("tilecloud_chain", "host-limit-schema.json")
                assert schema_data
                errors, _ = jsonschema_validator.validate(
                    str(host_limit_path),
                    cast("dict[str, Any]", self._hosts_limit),
                    json.loads(schema_data),
                )

                if errors:
                    _LOGGER.error("The host limit file is invalid, ignoring:\n%s", "\n".join(errors))
                    self._hosts_limit = {}

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        if tile is None:
            return None
        if self._bounding_pyramid is not None and tile.tilecoord not in self._bounding_pyramid:
            return None
        tilelayout = self._tile_layouts[hash(tile.tilecoord) % len(self._tile_layouts)]
        try:
            url = tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except # noqa: BLE001
            _LOGGER.warning("Error while getting tile %s", tile, exc_info=True)
            tile.error = exception
            return tile

        url_split = urllib.parse.urlparse(url)
        assert url_split.hostname is not None
        if url_split.hostname in self._hosts_semaphore:
            semaphore = self._hosts_semaphore[url_split.hostname]
        else:
            limit = (
                self._hosts_limit.get("hosts", {})
                .get(url_split.hostname, {})
                .get(
                    "concurrent",
                    self._hosts_limit.get("default", {}).get(
                        "concurrent",
                        host_limit.DEFAULT_CONCURRENT_LIMIT_DEFAULT,
                    ),
                )
            )
            semaphore = asyncio.Semaphore(limit)
            self._hosts_semaphore[url_split.hostname] = semaphore

        async with semaphore:
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
                        elif self._allows_no_contenttype:
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
        raise NotImplementedError

    async def list(self) -> AsyncGenerator[Tile]:
        """See in superclass."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError
