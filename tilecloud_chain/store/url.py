import asyncio
import json
import logging
import os
import pkgutil
import urllib.parse
from collections.abc import AsyncGenerator, Iterable
from typing import Any, cast

import aiohttp
import jsonschema_validator
from anyio import Path
from ruamel.yaml import YAML
from tilecloud import BoundingPyramid, Tile, TileCoord, TileLayout

from tilecloud_chain import host_limit
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


class _DatedConfig:
    """Loaded config with timestamps to be able to invalidate it on configuration file change."""

    def __init__(self) -> None:
        self.config: host_limit.HostLimit = {}
        self.mtime = 0.0


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
        self._hosts_limit = _DatedConfig()
        if headers is not None:
            self._session.headers.update(headers)

    async def _get_hosts_limit(self) -> host_limit.HostLimit:
        """Initialize the store."""
        host_limit_path = Path(
            os.environ.get(
                "TILEGENERATION_HOSTS_LIMIT",
                "/etc/tilegeneration/hosts_limit.yaml",
            ),
        )
        if await host_limit_path.exists():
            host_stat = await host_limit_path.stat()
            if self._hosts_limit.mtime != host_stat.st_mtime:
                yaml = YAML(typ="safe")
                async with await host_limit_path.open(encoding="utf-8") as f:
                    content = await f.read()
                    self._hosts_limit.config = yaml.load(content)
                    self._hosts_limit.mtime = host_stat.st_mtime

                    schema_data = pkgutil.get_data("tilecloud_chain", "host-limit-schema.json")
                    assert schema_data
                    errors, _ = jsonschema_validator.validate(
                        str(host_limit_path),
                        cast("dict[str, Any]", self._hosts_limit),
                        json.loads(schema_data),
                    )

                if errors:
                    _LOGGER.error("The host limit file is invalid, ignoring:\n%s", "\n".join(errors))
                    self._hosts_limit.config = {}
        return self._hosts_limit.config

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
                (await self._get_hosts_limit())
                .get("hosts", {})
                .get(url_split.hostname, {})
                .get(
                    "concurrent",
                    (await self._get_hosts_limit())
                    .get("default", {})
                    .get(
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
