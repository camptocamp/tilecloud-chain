"""Internal Mapcache."""

import contextlib
import datetime
import json
import logging
import os
import struct
import sys
import threading
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, NamedTuple, cast

import redis.asyncio as aioredis
import yaml
from fastapi import Response
from prometheus_client import Summary
from tilecloud import Tile, TileCoord

import tilecloud_chain.configuration
from tilecloud_chain import Run, configuration
from tilecloud_chain.generate import Generate
from tilecloud_chain.store import AsyncTileStore

if TYPE_CHECKING:
    from tilecloud_chain.server import Server

_MAX_GENERATION_TIME = int(os.environ.get("TILEGENERATION_MAX_GENERATION_TIME", "60"))
_LOG = logging.getLogger(__name__)
_lock = threading.Lock()
_GENERATOR = None

_GET_TILE = Summary("tilecloud_chain_get_generated_tile", "Time to get the generated tiles", ["storage"])


def _decode_tile(data: bytes, tile: Tile) -> None:
    """Decode a tile."""
    image_len = struct.unpack("q", data[:8])[0]
    tile.data = data[8 : (image_len + 8)]
    other = json.loads((data[(8 + image_len) :]).decode("utf-8"))
    tile.content_encoding = other["content_encoding"]
    tile.content_type = other["content_type"]


def _encode_tile(tile: Tile) -> bytes:
    """Encode a tile."""
    other = {"content_encoding": tile.content_encoding, "content_type": tile.content_type}
    assert tile.data
    return struct.pack("q", len(tile.data)) + tile.data + json.dumps(other).encode("utf-8")


class RedisStore(AsyncTileStore):
    """A store based on Redis."""

    def __init__(self, config: tilecloud_chain.configuration.Redis, **kwargs: Any) -> None:
        """Initialize."""
        super().__init__(**kwargs)

        redis_options = os.environ.get(
            "TILECLOUD_CHAIN_REDIS_OPTIONS",
            cast("str", config.get("redis_options", "")),
        )
        connection_kwargs = {
            key: yaml.load(value, Loader=yaml.SafeLoader)
            for key, value in [e.split("=", 1) for e in redis_options.split(",") if "=" in e]
        }

        socket_timeout = os.environ.get(
            "TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT",
            cast("str", config.get("socket_timeout")),
        )
        if socket_timeout is not None:
            connection_kwargs["socket_timeout"] = int(socket_timeout)
        db = os.environ.get("TILECLOUD_CHAIN_REDIS_DB", cast("str", config.get("db")))
        if db is not None:
            connection_kwargs["db"] = int(db)
        url = os.environ.get("TILECLOUD_CHAIN_REDIS_URL", cast("str", config.get("url")))
        if url is not None:
            self._master = aioredis.Redis.from_url(url, **connection_kwargs)
            self._slave = self._master
        else:
            sentinels: list[tuple[str, str | int]] = []
            if "TILECLOUD_CHAIN_REDIS_SENTINELs" in os.environ:
                sentinels_string = os.environ["TILECLOUD_CHAIN_REDIS_SENTINELS"]
                sentinels_tmp = [s.split(":") for s in sentinels_string.split(",")]
                sentinels = [  # pylint: disable=unnecessary-comprehension
                    (host, port) for host, port in sentinels_tmp
                ]
            else:
                sentinels = config["sentinels"]

            sentinels = [(host, int(port)) for host, port in sentinels]
            sentinel = aioredis.Sentinel(sentinels, **connection_kwargs)
            service_name = os.environ.get(
                "TILECLOUD_CHAIN_REDIS_SERVICE_NAME",
                config.get("service_name", tilecloud_chain.configuration.SERVICE_NAME_DEFAULT),
            )
            self._master = sentinel.master_for(service_name)
            self._slave = sentinel.slave_for(service_name)
        self._prefix = config.get("prefix", tilecloud_chain.configuration.PREFIX_DEFAULT)
        self._expiration = config.get("expiration", tilecloud_chain.configuration.EXPIRATION_DEFAULT)

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        key = self._get_key(tile)
        data = await self._slave.get(key)
        if data is None:
            _LOG.debug("Tile not found: %s/%s", tile.metadata["layer"], tile.tilecoord)
            return None
        _decode_tile(data, tile)
        _LOG.debug("Tile found: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        key = self._get_key(tile)
        await self._master.set(key, _encode_tile(tile), ex=self._expiration)
        _LOG.info("Tile saved: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        key = self._get_key(tile)
        await self._master.delete(key)
        return tile

    def _get_key(self, tile: Tile) -> str:
        keys = [
            self._prefix,
            tile.metadata["config_file"],
            tile.metadata["layer"],
            tile.tilecoord.z,
            tile.tilecoord.x,
            tile.tilecoord.y,
        ] + [value for key, value in tile.metadata.items() if key.startswith("dimension_")]
        return "_".join([str(key) for key in keys])

    @contextlib.asynccontextmanager
    async def lock(self, tile: Tile) -> AsyncIterator[None]:
        """Lock a tile."""
        key = self._get_key(tile) + "_l"
        async with self._master.lock(key, timeout=_MAX_GENERATION_TIME):
            yield

    async def __contains__(self, tile: Tile) -> bool:
        """Check if the tile is in the store."""
        raise NotImplementedError

    async def list(self) -> AsyncIterator[Tile]:
        """See in superclass."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable


class Generator:
    """Get the tile from the cache (Redis) or generated it on the WMS server."""

    _cache_store: RedisStore | None = None

    def __init__(self, tilegeneration: tilecloud_chain.TileGeneration) -> None:
        """Initialize."""
        self._tilegeneration = tilegeneration
        self.run: Run | None = None

    async def init(self) -> None:
        """Initialize the generator."""
        redis_config = (await self._tilegeneration.get_main_config()).config.get("redis", {})
        self._cache_store = RedisStore(redis_config)

        log_level = os.environ.get("TILE_MAPCACHE_LOGLEVEL")

        class Options(NamedTuple):
            verbose: bool
            debug: bool
            quiet: bool
            role: str
            near: bool
            time: bool
            daemon: bool
            local_process_number: int | None
            tiles: None | list[Any] | dict[str, Any] | str

        options = Options(
            log_level == "verbose",
            log_level == "debug",
            log_level == "quiet",
            "server",
            near=True,
            time=False,
            daemon=True,
            local_process_number=None,
            tiles=None,
        )

        generator = Generate(
            options,  # type: ignore[arg-type]
            self._tilegeneration,
            out=sys.stdout,
        )
        await generator.init(server=True)
        await generator._generate_tiles()  # pylint: disable=protected-access
        self.run = Run(self._tilegeneration, self._tilegeneration.functions_metatiles)
        await self.run.init()

    async def read_from_cache(self, tile: Tile) -> Tile | None:
        """Get the tile from the cache (Redis)."""
        assert self._cache_store is not None
        with _GET_TILE.labels("redis").time():
            return await self._cache_store.get_one(tile)

    async def compute_tile(self, tile: Tile, try_: int = 5) -> bool:
        """Create the tile."""
        with _GET_TILE.labels("wms").time():
            assert self.run is not None
            await self.run(tile)
        if tile.error:
            if try_ > 0:
                _LOG.info("Retry tile %s %s", tile.tilecoord, tile.formated_metadata)
                return await self.compute_tile(tile, try_ - 1)
            _LOG.error("Tile %s %s in error: %s", tile.tilecoord, tile.formated_metadata, tile.error)
            return False
        success = True
        for tile_ in tile.metadata["tiles"].values():  # type: ignore[attr-defined]
            if tile_.error:
                if try_ > 0:
                    _LOG.info("Retry tile %s %s", tile_.tilecoord, tile_.formated_metadata)
                    return await self.compute_tile(tile, try_ - 1)
                _LOG.error("Tile %s %s in error: %s", tile_.tilecoord, tile_.formated_metadata, tile_.error)
                success = False
            elif tile_.data is None:
                if try_ > 0:
                    _LOG.info("Retry tile %s %s", tile_.tilecoord, tile_.formated_metadata)
                    return await self.compute_tile(tile, try_ - 1)
                _LOG.error("Tile %s %s in error: no data", tile_.tilecoord, tile_.formated_metadata)
                success = False
            else:
                _LOG.debug("Tile %s %s generated", tile_.tilecoord, tile_.formated_metadata)
                assert self._cache_store is not None
                await self._cache_store.put_one(tile_)
        return success

    @contextlib.asynccontextmanager
    async def lock(self, tile: Tile) -> AsyncIterator[None]:
        """Lock the tile."""
        assert self._cache_store is not None
        async with self._cache_store.lock(tile):
            yield


async def _get_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    if _GENERATOR is None:
        return await _init_generator(tilegeneration)
    return _GENERATOR


async def _init_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    with _lock:
        global _GENERATOR  # noqa: PLW0603
        if _GENERATOR is None:
            _GENERATOR = Generator(tilegeneration)
            await _GENERATOR.init()
        return _GENERATOR


async def fetch(
    config: tilecloud_chain.DatedConfig,
    server: "Server",
    tilegeneration: tilecloud_chain.TileGeneration,
    layer: tilecloud_chain.configuration.Layer,
    tile: Tile,
) -> Response:
    """Fetch a time in the cache (redis) or get it on the WMS server."""
    generator = await _get_generator(tilegeneration)
    fetched_tile = await generator.read_from_cache(tile)
    backend = "redis"
    if fetched_tile is None:
        backend = "wms-wait"

        tile.metadata.setdefault("tiles", {})  # type: ignore[arg-type]
        meta_tile = tile
        if layer["meta"]:
            meta_tile = Tile(
                tilecoord=tile.tilecoord.metatilecoord(
                    layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT),
                ),
                metadata=tile.metadata,
            )

        async with generator.lock(meta_tile):
            fetched_tile = await generator.read_from_cache(tile)
            if fetched_tile is None:
                backend = "wms-generate"
                success = await generator.compute_tile(meta_tile)
                if not success:
                    return server.error(config, 500, "Error while generate the tile, see logs for details")

                if meta_tile.error:
                    _LOG.error(
                        "Tile %s %s in error: %s",
                        meta_tile.tilecoord,
                        meta_tile.formated_metadata,
                        meta_tile.error,
                    )
                    return server.error(config, 502, "Error while generate the tile, see logs for details")

                # Don't fetch the just generated tile
                tiles: dict[TileCoord, Tile] = cast("dict[TileCoord, Tile]", meta_tile.metadata["tiles"])
                try:
                    fetched_tile = tiles[tile.tilecoord]
                except KeyError:
                    _LOG.exception(
                        "Try to get the tile %s %s, from the available: '%s'",
                        tile.tilecoord,
                        tile.formated_metadata,
                        ", ".join([str(e) for e in tiles]),
                    )
                    return server.error(config, 500, "Error while getting the tile, see logs for details")

    response_headers = {
        "Expires": (
            datetime.datetime.now(tz=datetime.timezone.utc)
            + datetime.timedelta(hours=server.get_expires_hours(config))
        ).isoformat(),
        "Cache-Control": f"max-age={3600 * server.get_expires_hours(config)}",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
        "Tile-Backend": backend,
    }
    if fetched_tile.content_encoding:
        response_headers["Content-Encoding"] = fetched_tile.content_encoding
    if fetched_tile.content_type:
        response_headers["Content-Type"] = fetched_tile.content_type
    assert fetched_tile.data is not None
    return Response(
        content=fetched_tile.data,
        media_type=fetched_tile.content_type,
        headers=response_headers,
    )
