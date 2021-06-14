import collections
import contextlib
import datetime
import json
import logging
import os
import queue
import struct
import threading
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, Optional, TypeVar, cast

import redis.sentinel  # type: ignore

from tilecloud import Tile, TileCoord, TileStore
from tilecloud_chain import Run
import tilecloud_chain.configuration
from tilecloud_chain.generate import Generate
from tilecloud_chain.server import Server

MAX_GENERATION_TIME = 60
LOG = logging.getLogger(__name__)
lock = threading.Lock()
executing_lock = threading.Lock()
_generator = None


class InputStore(TileStore):
    run = True

    def __init__(self) -> None:
        super().__init__()
        if TYPE_CHECKING:
            self._queue: queue.Queue[Tile] = queue.Queue()  # pylint: disable=unsubscriptable-object
        else:
            self._queue = queue.Queue()

    def get_one(self, _: Any) -> Tile:
        return self._queue.get()

    def list(self) -> Iterable[Tile]:
        while self.run:
            yield self.get_one(None)

    def put_one(self, tile: Tile) -> Tile:
        self._queue.put(tile)
        return tile

    def delete_one(self, tile: Tile) -> Tile:
        return tile


def _decode_tile(data: bytes, tile: Tile) -> None:
    image_len = struct.unpack("q", data[:8])[0]
    tile.data = data[8 : (image_len + 8)]
    other = json.loads((data[(8 + image_len) :]).decode("utf-8"))
    tile.content_encoding = other["content_encoding"]
    tile.content_type = other["content_type"]


def _encode_tile(tile: Tile) -> bytes:
    other = {"content_encoding": tile.content_encoding, "content_type": tile.content_type}
    assert tile.data
    data = struct.pack("q", len(tile.data)) + tile.data + json.dumps(other).encode("utf-8")
    return data


class RedisStore(TileStore):
    def __init__(self, config: tilecloud_chain.configuration.Redis, **kwargs: Any):
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
        key = self._get_key(tile)
        data = self._slave.get(key)
        if data is None:
            LOG.debug("Tile not found: %s/%s", tile.metadata["layer"], tile.tilecoord)
            return None
        _decode_tile(data, tile)
        LOG.debug("Tile found: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    def put(self, tiles: Iterable[Tile]) -> Iterator[Tile]:
        for tile in tiles:
            self.put_one(tile)
            yield tile

    def put_one(self, tile: Tile) -> Tile:
        key = self._get_key(tile)
        self._master.set(key, _encode_tile(tile), ex=self._expiration)
        LOG.info("Tile saved: %s/%s", tile.metadata["layer"], tile.tilecoord)
        return tile

    def delete_one(self, tile: Tile) -> Tile:
        key = self._get_key(tile)
        self._master.delete(key)
        return tile

    def _get_key(self, tile: Tile) -> str:
        return "%s_%s_%d_%d_%d" % (
            self._prefix,
            tile.metadata["layer"],
            tile.tilecoord.z,
            tile.tilecoord.x,
            tile.tilecoord.y,
        )

    @contextlib.contextmanager
    def lock(self, tile: Tile) -> Iterator[None]:
        key = self._get_key(tile) + "_l"
        with self._master.lock(key, timeout=MAX_GENERATION_TIME):
            yield


class GeneratorThread(threading.Thread):
    def __init__(self, index: int, generator: "Generate") -> None:
        super().__init__(name="Generation thread #" + str(index), daemon=True)
        self._generator = generator
        self._gene = self._generator._gene  # pylint: disable=protected-access

    def run(self) -> None:
        LOG.info("Start internal mapcache generator")
        try:
            run = Run(
                self._gene,
                self._gene.functions_metatiles,
            )
            while True:
                with executing_lock:
                    assert self._gene.tilestream
                    tile = next(self._gene.tilestream)
                if tile is not None:
                    run(tile)
                    tile.metadata["lock"].release()  # type: ignore
        except StopIteration:
            pass
        finally:
            LOG.info("End internal mapcache generator")


class Generator:
    def __init__(self, tilegeneration: tilecloud_chain.TileGeneration) -> None:
        self._input_store = InputStore()
        redis_config = tilegeneration.config["redis"]
        self._cache_store = RedisStore(redis_config)
        self.threads = []
        log_level = os.environ.get("TILE_MAPCACHE_LOGLEVEL")
        generator = Generate(
            collections.namedtuple(  # type: ignore
                "Options",
                ["verbose", "debug", "quiet", "role", "near", "time", "daemon", "local_process_number"],
            )(
                log_level == "verbose",  # type: ignore
                log_level == "debug",
                log_level == "quiet",
                "server",
                True,
                False,
                True,
                None,
            ),
            tilegeneration,
            server=True,
        )
        generator.server_init(self._input_store, self._cache_store)
        for i in range(int(os.environ.get("SERVER_NB_THREAD", 10))):
            thread = GeneratorThread(i, generator)
            thread.start()
            self.threads.append(thread)

    def __del__(self) -> None:
        self.stop()

    def stop(self) -> None:
        self._input_store.run = False
        self._input_store.put_one(cast(Tile, None))

    def read_from_cache(self, tile: Tile) -> Optional[Tile]:
        return self._cache_store.get_one(tile)

    def compute_tile(self, tile: Tile) -> None:
        tile.metadata["lock"] = threading.Lock()  # type: ignore
        tile.metadata["lock"].acquire()  # type: ignore
        self._input_store.put_one(tile)
        tile.metadata["lock"].acquire()  # type: ignore
        del tile.metadata["lock"]

    @contextlib.contextmanager
    def lock(self, tile: Tile) -> Iterator[None]:
        with self._cache_store.lock(tile):
            yield


def _get_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    global _generator  # pylint: disable=global-statement
    if _generator is None:
        return _init_generator(tilegeneration)
    return _generator


def _init_generator(tilegeneration: tilecloud_chain.TileGeneration) -> Generator:
    global _generator, lock  # pylint: disable=global-statement
    with lock:
        if _generator is None:
            _generator = Generator(tilegeneration)
        return _generator


Response = TypeVar("Response")


def fetch(
    server: Server[Response],
    tilegeneration: tilecloud_chain.TileGeneration,
    layer: tilecloud_chain.configuration.Layer,
    tile: Tile,
    kwargs: Dict[str, Any],
) -> Response:
    generator = _get_generator(tilegeneration)
    fetched_tile = generator.read_from_cache(tile)
    if fetched_tile is None:

        tile.metadata.setdefault("tiles", {})  # type: ignore
        meta_tile = tile
        if layer["meta"]:
            meta_tile = Tile(
                tilecoord=tile.tilecoord.metatilecoord(layer["meta_size"]), metadata=tile.metadata
            )

        with generator.lock(meta_tile):
            fetched_tile = generator.read_from_cache(tile)
            if fetched_tile is None:
                generator.compute_tile(meta_tile)

                if meta_tile.error:
                    LOG.error("Tile '%s' in error: %s", meta_tile.tilecoord, meta_tile.error)
                    return server.error(500, "Error while generate the tile, see logs for details")

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
        "Expires": (datetime.datetime.utcnow() + datetime.timedelta(hours=server.expires_hours)).isoformat(),
        "Cache-Control": "max-age={}".format((3600 * server.expires_hours)),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
        "Tile-Backend": "WMS",
    }
    if tile.content_encoding:
        response_headers["Content-Encoding"] = tile.content_encoding
    if tile.content_type:
        response_headers["Content-Type"] = tile.content_type
    assert fetched_tile
    assert fetched_tile.data
    return server.response(fetched_tile.data, headers=response_headers, **kwargs)


def stop(tilegeneration: tilecloud_chain.TileGeneration) -> None:
    _get_generator(tilegeneration).stop()
