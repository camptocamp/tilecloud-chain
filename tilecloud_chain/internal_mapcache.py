"""Internal Mapcache."""

import collections
import contextlib
import datetime
import json
import logging
import os
import struct
import sys
import threading
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, TypeVar, cast

import redis.sentinel
from prometheus_client import Summary
from tilecloud import Tile, TileCoord, TileStore

import tilecloud_chain.configuration
from tilecloud_chain import Run, configuration
from tilecloud_chain.generate import Generate

if TYPE_CHECKING:
    from tilecloud_chain.server import Server

_MAX_GENERATION_TIME = int(os.environ.get("TILEGENERATION_MAX_GENERATION_TIME", "60"))
_LOG = logging.getLogger(__name__)
_lock = threading.Lock()
_executing_lock = threading.Lock()
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
    data = struct.pack("q", len(tile.data)) + tile.data + json.dumps(other).encode("utf-8")
    return data


class RedisStore(TileStore):
    """A store based on Redis."""

    def __init__(self, config: tilecloud_chain.configuration.Redis, **kwargs: Any):
        """Initialize."""
        super().__init__(**kwargs)

        connection_kwargs = {}
        socket_timeout = os.environ.get("TILECLOUD_CHAIN_REDIS_SOCKET_TIMEOUT", config.get("socket_timeout"))
        if socket_timeout is not None:
            connection_kwargs["socket_timeout"] = int(socket_timeout)
        db = os.environ.get("TILECLOUD_CHAIN_REDIS_DB", config.get("db"))
        if db is not None:
            connection_kwargs["db"] = int(db)
        url = os.environ.get("TILECLOUD_CHAIN_REDIS_URL", config.get("url"))
        if url is not None:
            self._master = redis.Redis.from_url(url, **connection_kwargs)  # type: ignore
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
            sentinel = redis.sentinel.Sentinel(sentinels, **connection_kwargs)  # type: ignore
            service_name = os.environ.get(
                "TILECLOUD_CHAIN_REDIS_SERVICE_NAME",
                config.get("service_name", tilecloud_chain.configuration.SERVICE_NAME_DEFAULT),
            )
            self._master = sentinel.master_for(service_name)
            self._slave = sentinel.slave_for(service_name)
        self._prefix = config.get("prefix", tilecloud_chain.configuration.PREFIX_DEFAULT)
        self._expiration = config.get("expiration", tilecloud_chain.configuration.EXPIRATION_DEFAULT)

    def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        key = self._get_key(tile)
        data = self._slave.get(key)
        if data is None:
            _LOG.debug("Tile not found: %s/%s", tile.metadata["layer"], tile.tilecoord)
            return None
        _decode_tile(data, tile)
        _LOG.debug("Tile found: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        key = self._get_key(tile)
        self._master.set(key, _encode_tile(tile), ex=self._expiration)
        _LOG.info("Tile saved: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        key = self._get_key(tile)
        self._master.delete(key)
        return tile

    def _get_key(self, tile: Tile) -> str:
        return (
            f"{self._prefix}_{tile.metadata['config_file']}_{tile.metadata['layer']}_"
            f"{tile.tilecoord.z}_{tile.tilecoord.x}_{tile.tilecoord.y}"
        )

    @contextlib.contextmanager
    def lock(self, tile: Tile) -> Iterator[None]:
        """Lock a tile."""
        key = self._get_key(tile) + "_l"
        with self._master.lock(key, timeout=_MAX_GENERATION_TIME):
            yield


class Generator:
    """Get the tile from the cache (Redis) or generated it on the WMS server."""

    def __init__(self, tilegeneration: tilecloud_chain.TileGeneration) -> None:
        """Initialize."""
        redis_config = tilegeneration.get_main_config().config.get("redis", {})
        self._cache_store = RedisStore(redis_config)
        log_level = os.environ.get("TILE_MAPCACHE_LOGLEVEL")
        generator = Generate(
            collections.namedtuple(  # type: ignore
                "Options",
                [
                    "verbose",
                    "debug",
                    "quiet",
                    "role",
                    "near",
                    "time",
                    "daemon",
                    "local_process_number",
                    "tiles",
                ],
            )(
                log_level == "verbose",  # type: ignore
                log_level == "debug",
                log_level == "quiet",
                "server",
                True,
                False,
                True,
                None,
                None,
            ),
            tilegeneration,
            out=sys.stdout,
            server=True,
        )
        generator._generate_tiles()
        self.run = Run(tilegeneration, tilegeneration.functions_metatiles)

    def read_from_cache(self, tile: Tile) -> Tile | None:
        """Get the tile from the cache (Redis)."""
        with _GET_TILE.labels("redis").time():
            return self._cache_store.get_one(tile)

    def compute_tile(self, tile: Tile) -> None:
        """Create the tile."""
        with _GET_TILE.labels("wms").time():
            self.run(tile)
        if tile.error:
            _LOG.error("Tile %s %s in error: %s", tile.tilecoord, tile.formated_metadata, tile.error)
            return
        for tile_ in tile.metadata["tiles"].values():  # type: ignore
            if tile_.error:
                _LOG.error("Tile %s %s in error: %s", tile_.tilecoord, tile_.formated_metadata, tile_.error)
                return
            if tile_.data is None:
                _LOG.error("Tile %s %s in error: no data", tile_.tilecoord, tile_.formated_metadata)
                return
            self._cache_store.put_one(tile_)

    @contextlib.contextmanager
    def lock(self, tile: Tile) -> Iterator[None]:
        """Lock the tile."""
        with self._cache_store.lock(tile):
            yield


def _get_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    if _GENERATOR is None:
        return _init_generator(tilegeneration)
    return _GENERATOR


def _init_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    with _lock:
        global _GENERATOR  # pylint: disable=global-statement
        if _GENERATOR is None:
            _GENERATOR = Generator(tilegeneration)
        return _GENERATOR


Response = TypeVar("Response")


def fetch(
    config: tilecloud_chain.DatedConfig,
    server: "Server[Response]",
    tilegeneration: tilecloud_chain.TileGeneration,
    layer: tilecloud_chain.configuration.Layer,
    tile: Tile,
    kwargs: dict[str, Any],
) -> Response:
    """Fetch a time in the cache (redis) or get it on the WMS server."""
    generator = _get_generator(tilegeneration)
    fetched_tile = generator.read_from_cache(tile)
    backend = "redis"
    if fetched_tile is None:
        backend = "wms-wait"

        tile.metadata.setdefault("tiles", {})  # type: ignore
        meta_tile = tile
        if layer["meta"]:
            meta_tile = Tile(
                tilecoord=tile.tilecoord.metatilecoord(
                    layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT)
                ),
                metadata=tile.metadata,
            )

        with generator.lock(meta_tile):
            fetched_tile = generator.read_from_cache(tile)
            if fetched_tile is None:
                backend = "wms-generate"
                generator.compute_tile(meta_tile)

                if meta_tile.error:
                    _LOG.error(
                        "Tile %s %s in error: %s",
                        meta_tile.tilecoord,
                        meta_tile.formated_metadata,
                        meta_tile.error,
                    )
                    return server.error(config, 502, "Error while generate the tile, see logs for details")

                # Don't fetch the just generated tile
                tiles: dict[TileCoord, Tile] = cast(dict[TileCoord, Tile], meta_tile.metadata["tiles"])
                try:
                    fetched_tile = tiles[tile.tilecoord]
                except KeyError:
                    _LOG.exception(
                        "Try to get the tile %s %s, from the available: '%s'",
                        tile.tilecoord,
                        tile.formated_metadata,
                        ", ".join([str(e) for e in tiles]),
                    )
                    raise

    response_headers = {
        "Expires": (
            datetime.datetime.utcnow() + datetime.timedelta(hours=server.get_expires_hours(config))
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
    return server.response(config, fetched_tile.data, headers=response_headers, **kwargs)
