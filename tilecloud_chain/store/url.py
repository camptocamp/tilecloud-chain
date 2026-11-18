# Copyright (c) 2026 by Camptocamp
import asyncio
import json
import logging
import pkgutil
import time
import urllib.parse
from collections.abc import AsyncGenerator, Iterable
from dataclasses import replace
from typing import Any, cast

import aiohttp
import jsonschema_validator
from ruamel.yaml import YAML
from tilecloud import BoundingPyramid, Tile, TileCoord, TileLayout

from tilecloud_chain import host_limit
from tilecloud_chain.error import ErrorContext, format_error
from tilecloud_chain.settings import settings
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)

_CLOSED_SESSION_MESSAGES = ("Connector is closed", "Session is closed")
_CLOSED_SESSION_HINT = (
    "the HTTP session of the tile store was already closed: the store was closed (configuration file "
    "change or process shutdown) while this tile was still being generated"
)


def _closed_session_hint(error: BaseException, closed: bool) -> str | None:
    """Get the hint to add when the error comes from a closed session or connector."""
    if any(message in str(error) for message in _CLOSED_SESSION_MESSAGES):
        return _CLOSED_SESSION_HINT
    if closed:
        return "the tile store is closed, the requests it receives can not be done anymore"
    return None


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
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=settings.http.timeout,
                connect=settings.http.connect_timeout,
            )
        )
        self._hosts_semaphore: dict[str, asyncio.Semaphore] = {}
        self._hosts_limit = _DatedConfig()
        self._closed = False
        self._in_flight = 0
        self._idle = asyncio.Event()
        self._idle.set()
        if headers is not None:
            self._session.headers.update(headers)

    async def close(self) -> None:
        """
        Close the aiohttp session.

        The requests which are still in flight are awaited first, to not fail the tiles which
        are being generated with a `Connector is closed` or `Session is closed` error.
        """
        self._closed = True
        if self._in_flight > 0:
            _LOGGER.info("Waiting for %s requests in flight to finish before closing", self._in_flight)
            try:
                await asyncio.wait_for(self._idle.wait(), timeout=settings.http.close_grace_period)
            except TimeoutError:
                _LOGGER.warning(
                    "%s requests still in flight after %ss, closing the session anyway",
                    self._in_flight,
                    settings.http.close_grace_period,
                )
        try:
            await self._session.close()
        except (TimeoutError, aiohttp.ClientConnectionError):
            # the peer does not answer anymore, there is nothing left to do with the session
            _LOGGER.warning("Ignored error during aiohttp session close", exc_info=True)

    async def _get_hosts_limit(self) -> host_limit.HostLimit:
        """Initialize the store."""
        host_limit_path = settings.hosts_limit
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
                        cast("dict[str, Any]", self._hosts_limit.config),
                        json.loads(schema_data),
                    )

                if errors:
                    _LOGGER.error("The host limit file is invalid, ignoring:\n%s", "\n".join(errors))
                    self._hosts_limit.config = {}
        return self._hosts_limit.config

    async def _get_semaphore(self, hostname: str) -> asyncio.Semaphore:
        """Get the semaphore which limits the number of concurrent requests on the given host."""
        semaphore = self._hosts_semaphore.get(hostname)
        if semaphore is None:
            hosts_limit = await self._get_hosts_limit()
            limit = (
                hosts_limit.get("hosts", {})
                .get(hostname, {})
                .get(
                    "concurrent",
                    hosts_limit.get("default", {}).get("concurrent", settings.host_concurrent),
                )
            )
            semaphore = asyncio.Semaphore(limit)
            self._hosts_semaphore[hostname] = semaphore
        return semaphore

    def _start_request(self) -> None:
        """Flag that a request is in flight."""
        self._in_flight += 1
        self._idle.clear()

    def _end_request(self) -> None:
        """Flag that a request is not in flight anymore."""
        self._in_flight -= 1
        if self._in_flight == 0:
            self._idle.set()

    async def _handle_response(
        self,
        tile: Tile,
        response: aiohttp.ClientResponse,
        context: ErrorContext,
    ) -> Tile | None:
        """Handle the response to a tile request, and return the tile, or None on a 204 response."""
        if response.status == 204:
            _LOGGER.debug("Got empty tile from %s: %s", context.url, response.status)
            return None
        tile.content_encoding = response.headers.get("Content-Encoding")
        tile.content_type = response.headers.get("Content-Type")
        if response.status >= 300:
            tile.error = format_error(
                f"{response.status}: {response.reason}\n{await response.text()}",
                context,
            )
            return tile
        if response.status != 200:
            tile.error = format_error(
                f"Unsupported status code {response.status}: {response.reason}",
                context,
            )
        if tile.content_type:
            if tile.content_type.startswith("image/"):
                tile.data = await response.read()
            else:
                tile.error = format_error(await response.text(), context)
        elif self._allows_no_contenttype:
            tile.data = await response.read()
        else:
            tile.error = format_error("The Content-Type header is missing", context)
        return tile

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        if tile is None:
            return None
        if self._bounding_pyramid is not None and tile.tilecoord not in self._bounding_pyramid:
            return None
        layer = tile.metadata.get("layer", "none")
        host = tile.metadata.get("host", "none")
        tilelayout = self._tile_layouts[hash(tile.tilecoord) % len(self._tile_layouts)]
        try:
            url = tilelayout.filename(tile.tilecoord, tile.metadata)
        except Exception as exception:  # pylint: disable=broad-except
            # the URL layout is built from a user provided format string, then it can fail
            _LOGGER.warning(
                "Error while getting the URL of the tile %s %s of layer '%s'",
                tile.tilecoord,
                tile.formated_metadata,
                layer,
                exc_info=True,
            )
            tile.error = format_error(
                exception,
                ErrorContext(step="build the request URL", layer=layer, host=host),
            )
            return tile
        context = ErrorContext(url=url, layer=layer, host=host)

        url_split = urllib.parse.urlparse(url)
        assert url_split.hostname is not None, f"Parsed URL is missing a hostname: {url!r}"
        semaphore = await self._get_semaphore(url_split.hostname)

        async with semaphore:
            if self._closed:
                tile.error = format_error(
                    aiohttp.ClientConnectionError("Tile store is closed"),
                    replace(context, hint="the tile store is closed, it can not do any request anymore"),
                )
                return tile
            _LOGGER.info("GET %s", url)
            self._start_request()
            start = time.monotonic()
            try:
                async with self._session.get(url) as response:
                    return await self._handle_response(
                        tile,
                        response,
                        replace(context, duration=time.monotonic() - start),
                    )
            except (aiohttp.ClientError, TimeoutError, RuntimeError) as exception:
                # aiohttp raises a RuntimeError when the session is closed, and a TimeoutError
                # (with an empty message) when the request exceeds the configured timeout
                _LOGGER.warning(
                    "Error while getting the tile %s %s of layer '%s' from %s",
                    tile.tilecoord,
                    tile.formated_metadata,
                    layer,
                    url,
                    exc_info=True,
                )
                tile.error = format_error(
                    exception,
                    replace(
                        context,
                        duration=time.monotonic() - start,
                        hint=_closed_session_hint(exception, self._closed),
                    ),
                )
            finally:
                self._end_request()
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
