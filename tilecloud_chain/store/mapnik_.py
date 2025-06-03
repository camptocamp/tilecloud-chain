"""MapnikTileStore with drop action if the generated tile is empty."""

import logging
from collections.abc import AsyncGenerator, Callable
from json import dumps
from typing import Any

import mapnik  # pylint: disable=import-error
from tilecloud import Tile, TileCoord, TileGrid

from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


class MapnikTileStore(AsyncTileStore):
    """
    Tile store that renders tiles with Mapnik.

    requires mapnik: https://python-mapnik.readthedocs.io/
    """

    def __init__(
        self,
        tilegrid: TileGrid,
        mapfile: str,
        data_buffer: int = 128,
        image_buffer: int = 0,
        output_format: str = "png256",
        resolution: int = 2,
        layers_fields: dict[str, list[str]] | None = None,
        drop_empty_utfgrid: bool = False,
        proj4_literal: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Construct a MapnikTileStore.

            tilegrid: the tilegrid.
            mapfile: the file used to render the tiles.
            buffer_size: the image buffer size default is 128.
            output_format: the output format,
            possible values 'jpeg', 'png', 'png256', 'grid',
            default is 'png256'
            layers_fields: the layers and fields used in the grid generation,
            example: { 'my_layer': ['my_first_field', 'my_segonf_field']},
            default is {}.
            **kwargs: for extended class.
        """
        if layers_fields is None:
            layers_fields = {}

        AsyncTileStore.__init__(self, **kwargs)
        self.tilegrid = tilegrid
        self.buffer = image_buffer
        self.output_format = output_format
        self.resolution = resolution
        self.layers_fields = layers_fields
        self.drop_empty_utfgrid = drop_empty_utfgrid

        self.mapnik = mapnik.Map(tilegrid.tile_size, tilegrid.tile_size)  # pylint: disable=no-member
        mapnik.load_map(self.mapnik, mapfile, True)  # noqa: FBT003 # pylint: disable=no-member
        self.mapnik.buffer_size = data_buffer
        if proj4_literal is not None:
            self.mapnik.srs = proj4_literal

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        bbox = self.tilegrid.extent(tile.tilecoord, self.buffer)
        bbox2d = mapnik.Box2d(bbox[0], bbox[1], bbox[2], bbox[3])  # pylint: disable=no-member

        size = tile.tilecoord.n * self.tilegrid.tile_size + 2 * self.buffer
        self.mapnik.resize(size, size)
        self.mapnik.zoom_to_box(bbox2d)

        if self.output_format == "grid":
            grid = mapnik.Grid(self.tilegrid.tile_size, self.tilegrid.tile_size)  # pylint: disable=no-member
            for number, layer in enumerate(self.mapnik.layers):
                if layer.name in self.layers_fields:
                    mapnik.render_layer(  # pylint: disable=no-member
                        self.mapnik,
                        grid,
                        layer=number,
                        fields=self.layers_fields[layer.name],
                    )

            encode = grid.encode("utf", resolution=self.resolution)
            if self.drop_empty_utfgrid and len(encode["data"].keys()) == 0:
                return None
            tile.data = dumps(encode).encode()
        else:
            # Render image with default Agg renderer
            image = mapnik.Image(size, size)  # pylint: disable=no-member
            mapnik.render(self.mapnik, image)  # pylint: disable=no-member
            tile.data = image.tostring(self.output_format)

        return tile

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        raise NotImplementedError

    async def list(self) -> AsyncGenerator[Tile]:
        """See in superclass."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable


class MapnikDropActionTileStore(MapnikTileStore):
    """MapnikTileStore with drop action if the generated tile is empty."""

    def __init__(
        self,
        store: AsyncTileStore | None = None,
        queue_store: AsyncTileStore | None = None,
        count: list[Callable[[Tile | None], Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize."""
        self.store = store
        self.queue_store = queue_store
        self.count = count or []
        MapnikTileStore.__init__(self, **kwargs)

    async def get_one(self, tile: Tile) -> Tile | None:
        """See in superclass."""
        result = await MapnikTileStore.get_one(self, tile)
        if result is None:
            if self.store is not None:
                if tile.tilecoord.n != 1:
                    for tilecoord in tile.tilecoord:
                        await self.store.delete_one(Tile(tilecoord))
                else:
                    await self.store.delete_one(tile)
            _LOGGER.info("The tile %s %s is dropped", tile.tilecoord, tile.formated_metadata)
            if hasattr(tile, "metatile"):
                metatile: Tile = tile.metatile
                metatile.elapsed_togenerate -= 1  # type: ignore[attr-defined]
                if metatile.elapsed_togenerate == 0 and self.queue_store is not None:  # type: ignore[attr-defined]
                    await self.queue_store.delete_one(metatile)
            elif self.queue_store is not None:
                await self.queue_store.delete_one(tile)

            for count in self.count:
                count(None)
        return result

    async def __contains__(self, tile: Tile) -> bool:
        """See in superclass."""
        raise NotImplementedError

    async def put_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def delete_one(self, tile: Tile) -> Tile:
        """See in superclass."""
        raise NotImplementedError

    async def list(self) -> AsyncGenerator[Tile]:
        """See in superclass."""
        raise NotImplementedError
        yield Tile(TileCoord(0, 0, 0))  # pylint: disable=unreachable
