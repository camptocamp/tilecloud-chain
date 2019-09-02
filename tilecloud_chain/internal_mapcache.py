import contextlib
import datetime
import json
import logging
import queue
import struct
import threading

import redis

import redlock
from tilecloud import Tile, TileStore, consume
from tilecloud_chain.generate import Generate

MAX_GENERATION_TIME = 60
RETRY_DELAY = 0.05
LOG = logging.getLogger(__name__)
lock = threading.Lock()
generator = None


class FakeOptions:
    role = 'server'
    debug = False
    near = True
    time = False


class InputStore(TileStore):
    def __init__(self):
        super(InputStore, self).__init__()
        self._queue = queue.Queue()

    def get_one(self):
        return self._queue.get()

    def list(self):
        while True:
            tile = self.get_one()
            yield tile
            tile.metadata['lock'].release()

    def put_one(self, tile):
        self._queue.put(tile)

    def delete_one(self, tile):
        pass


def _decode_tile(data, tile):
    image_len = struct.unpack('q', data[:8])[0]
    tile.data = data[8:(image_len + 8)]
    other = json.loads((data[(8 + image_len):]).decode('utf-8'))
    tile.content_encoding = other['content_encoding']
    tile.content_type = other['content_type']


def _encode_tile(tile):
    other = {
        'content_encoding': tile.content_encoding,
        'content_type': tile.content_type
    }
    data = struct.pack('q', len(tile.data)) + tile.data + json.dumps(other).encode('utf-8')
    return data


class RedisStore(TileStore):
    def __init__(self, url, prefix, **kwargs):
        super(RedisStore, self).__init__(**kwargs)
        self._redis = redis.Redis.from_url(url)
        self._prefix = prefix
        self._redis_lock = redlock.Redlock([self._redis], retry_count=MAX_GENERATION_TIME / RETRY_DELAY,
                                           retry_delay=RETRY_DELAY)

    def get_one(self, tile):
        key = self._get_key(tile)
        data = self._redis.get(key)
        if data is None:
            LOG.warning("Tile not found: %s/%s", tile.metadata['layer'], tile.tilecoord)
            return None
        _decode_tile(data, tile)
        LOG.warning("Tile found: %s/%s", tile.metadata['layer'], tile.tilecoord)
        return tile

    def put(self, tiles):
        for tile in tiles:
            self.put_one(tile)
            yield tile

    def put_one(self, tile):
        key = self._get_key(tile)
        self._redis.set(key, _encode_tile(tile))
        LOG.warning("Tile saved: %s/%s", tile.metadata['layer'], tile.tilecoord)
        return tile

    def delete_one(self, tile):
        key = self._get_key(tile)
        self._redis.delete(key)

    def _get_key(self, tile):
        return "%s_%s_%d_%d_%d" % (self._prefix, tile.metadata['layer'], tile.tilecoord.z,
                                   tile.tilecoord.x, tile.tilecoord.y)

    @contextlib.contextmanager
    def lock(self, tile):
        key = self._get_key(tile) + "_l"
        lock_ = self._redis_lock.lock(key, MAX_GENERATION_TIME * 1000)
        try:
            yield
        finally:
            self._redis_lock.unlock(lock_)


class GeneratorThread(threading.Thread):
    def __init__(self, index, tilegeneration, input_store, cache_store):
        super(GeneratorThread, self).__init__(name="Generation thread #" + str(index), daemon=True)
        self._generator = Generate(FakeOptions(), tilegeneration)
        self._generator.server_init(input_store, cache_store)

    def run(self):
        consume(self._generator._gene.tilestream, n=None)


class Generator():
    def __init__(self, tilegeneration):
        self._input_store = InputStore()
        redis_config = tilegeneration.config['redis']
        self._cache_store = RedisStore(redis_config['url'], redis_config['prefix'])
        for i in range(10):
            thread = GeneratorThread(i, tilegeneration, self._input_store, self._cache_store)
            thread.start()

    def read_from_cache(self, tile):
        return self._cache_store.get_one(tile)

    def compute_tile(self, tile):
        tile.metadata['lock'] = threading.Lock()
        tile.metadata['lock'].acquire()
        self._input_store.put_one(tile)
        tile.metadata['lock'].acquire()
        del tile.metadata['lock']

    @contextlib.contextmanager
    def lock(self, tile):
        with self._cache_store.lock(tile):
            yield


def _get_generator(tilegeneration):
    global generator
    if generator is None:
        return _init_generator(tilegeneration)
    return generator


def _init_generator(tilegeneration):
    global generator, lock
    with lock:
        if generator is None:
            generator = Generator(tilegeneration)
        return generator


def fetch(server, tilegeneration, layer, tile, kwargs):
    generator = _get_generator(tilegeneration)
    fetched_tile = generator.read_from_cache(tile)
    if fetched_tile is None:
        meta_tile = tile
        if layer.get('meta', False):
            meta_tile = Tile(tilecoord=tile.tilecoord.metatilecoord(layer.get('meta_size', 1)),
                             metadata=tile.metadata)

        with generator.lock(meta_tile):
            fetched_tile = generator.read_from_cache(tile)
            if fetched_tile is None:
                generator.compute_tile(meta_tile)

                fetched_tile = generator.read_from_cache(tile)
                assert fetched_tile is not None

    response_headers = {
        'Expires': (datetime.datetime.utcnow() + datetime.timedelta(hours=server.expires_hours)).isoformat(),
        'Cache-Control': "max-age={}".format((3600 * server.expires_hours)),
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Tile-Backend': 'WMS'
    }
    if tile.content_encoding:
        response_headers['Content-Encoding'] = tile.content_encoding
    if tile.content_type:
        response_headers['Content-Type'] = tile.content_type
    return server.response(fetched_tile.data, headers=response_headers, **kwargs)
