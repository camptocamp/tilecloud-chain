from c2cwsgiutils import stats
from tilecloud import TileStore


class TimedTileStoreWrapper(TileStore):
    """
    A wrapper around a TileStore that adds timer metrics.
    """
    def __init__(self, tile_store, stats_name):
        super().__init__()
        self._tile_store = tile_store
        self._stats_name = stats_name

    def _get_stats_name(self, func_name, tile=None):
        if tile and 'layer' in tile.metadata:
            return [self._stats_name, tile.metadata['layer'], func_name]
        else:
            return [self._stats_name, func_name]

    def _time_iteration(self, generator, func_name):
        while True:  # will exit when next(generator) raises StopIteration
            timer = stats.timer()
            tile = next(generator)
            timer.stop(self._get_stats_name(func_name, tile))
            yield tile

    def __contains__(self, tile):
        with stats.timer_context(self._get_stats_name('contains', tile)):
            return self._tile_store.__contains__(tile)

    def __len__(self):
        with stats.timer_context(self._get_stats_name('len')):
            return self._tile_store.__len__()

    def delete(self, tiles):
        return self._time_iteration(self._tile_store.delete(tiles), 'delete')

    def delete_one(self, tile):
        with stats.timer_context(self._get_stats_name('delete_one', tile)):
            return self._tile_store.delete_one(tile)

    def list(self):
        return self._time_iteration(self._tile_store.list(), 'list')

    def get(self, tiles):
        return self._time_iteration(self._tile_store.get(tiles), 'get')

    def get_all(self):
        return self._time_iteration(self._tile_store.get_all(), 'get_all')

    def get_one(self, tile):
        with stats.timer_context(self._get_stats_name('get_one', tile)):
            return self._tile_store.get_one(tile)

    def put(self, tiles):
        return self._time_iteration(self._tile_store.put(tiles), 'put')

    def put_one(self, tile):
        with stats.timer_context(self._get_stats_name('put_one', tile)):
            return self._tile_store.put_one(tile)

    def get_bounding_pyramid(self):
        return self._tile_store.get_bounding_pyramid()

    def get_cheap_bounding_pyramid(self):
        return self._tile_store.get_cheap_bounding_pyramid()
