import collections
import contextlib
import datetime
import json
import logging
import os
import struct
import threading
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, TypeVar, cast

import redis.sentinel

from tilecloud import Tile, TileCoord, TileStore
from tilecloud_chain import Run
import tilecloud_chain.configuration
from tilecloud_chain.generate import Generate

if TYPE_CHECKING:
    from tilecloud_chain.server import Server

MAX_GENERATION_TIME = 60
LOG = logging.getLogger(__name__)
lock = threading.Lock()
executing_lock = threading.Lock()
_generator = None


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
        if "socket_timeout" in config:
            connection_kwargs["socket_timeout"] = config["socket_timeout"]
        if "db" in config:
            connection_kwargs["db"] = config["db"]
        if "url" in config:
            self._master = redis.Redis.from_url(config["url"], **connection_kwargs)  # type: ignore
            self._slave = self._master
        else:
            sentinel = redis.sentinel.Sentinel(config["sentinels"], **connection_kwargs)
            self._master = sentinel.master_for(config.get("service_name", "mymaster"))
            self._slave = sentinel.slave_for(config.get("service_name", "mymaster"))
        self._prefix = config["prefix"]
        self._expiration = config["expiration"]

    def get_one(self, tile: Tile) -> Optional[Tile]:
        """See in superclass."""
        key = self._get_key(tile)
        data = self._slave.get(key)
        if data is None:
            LOG.debug("Tile not found: %s/%s", tile.metadata["layer"], tile.tilecoord)
            return None
        _decode_tile(data, tile)
        LOG.debug("Tile found: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        key = self._get_key(tile)
        self._master.set(key, _encode_tile(tile), ex=self._expiration)
        LOG.info("Tile saved: %s/%s", tile.metadata["layer"], tile.tilecoord)
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
        with self._master.lock(key, timeout=MAX_GENERATION_TIME):
            yield


class Generator:
    """Get the tile from the cache (Redis) or generated it on the WMS server."""

    def __init__(self, tilegeneration: tilecloud_chain.TileGeneration) -> None:
        """Initialize."""
        redis_config = tilegeneration.get_main_config().config["redis"]
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
            server=True,
        )
        generator._generate_tiles()
        self.run = Run(tilegeneration, tilegeneration.functions_metatiles)

    def read_from_cache(self, tile: Tile) -> Optional[Tile]:
        """Get the tile from the cache (Redis)."""
        return self._cache_store.get_one(tile)

    def compute_tile(self, tile: Tile) -> None:
        """Create the tile."""
        self.run(tile)
        for tile_ in tile.metadata["tiles"].values():  # type: ignore
            self._cache_store.put_one(tile_)

    @contextlib.contextmanager
    def lock(self, tile: Tile) -> Iterator[None]:
        """Lock the tile."""
        with self._cache_store.lock(tile):
            yield


def _get_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    if _generator is None:
        return _init_generator(tilegeneration)
    return _generator


def _init_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    with lock:
        global _generator  # pylint: disable=global-statement
        if _generator is None:
            _generator = Generator(tilegeneration)
        return _generator


Response = TypeVar("Response")


def fetch(
    config: tilecloud_chain.DatedConfig,
    server: "Server[Response]",
    tilegeneration: tilecloud_chain.TileGeneration,
    layer: tilecloud_chain.configuration.Layer,
    tile: Tile,
    kwargs: Dict[str, Any],
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
                tilecoord=tile.tilecoord.metatilecoord(layer["meta_size"]), metadata=tile.metadata
            )

        with generator.lock(meta_tile):
            fetched_tile = generator.read_from_cache(tile)
            if fetched_tile is None:
                backend = "wms-generate"
                generator.compute_tile(meta_tile)

                if meta_tile.error:
                    LOG.error("Tile '%s' in error: %s", meta_tile.tilecoord, meta_tile.error)
                    return server.error(config, 500, "Error while generate the tile, see logs for details")

                # Don't fetch the just generated tile
                tiles: Dict[TileCoord, Tile] = cast(Dict[TileCoord, Tile], meta_tile.metadata["tiles"])
                try:
                    fetched_tile = tiles[tile.tilecoord]
                except KeyError:
                    LOG.exception(
                        "Try to get the tile '%s', from the available: '%s'",
                        tile.tilecoord,
                        ", ".join([str(e) for e in tiles.keys()]),
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
