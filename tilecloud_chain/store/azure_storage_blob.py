import logging
from collections.abc import AsyncIterator

from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from tilecloud import Tile, TileLayout

from tilecloud_chain.settings import settings
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)


class AzureStorageBlobTileStore(AsyncTileStore):
    """Tiles stored in Azure storage blob."""

    def __init__(
        self,
        tilelayout: TileLayout,
        container: str | None = None,
        dry_run: bool = False,
        cache_control: str | None = None,
        container_client: ContainerClient | None = None,
    ) -> None:
        """Initialize."""
        if container_client is None:
            if settings.azure.storage_connection_string:
                assert container is not None
                self.container_client = BlobServiceClient.from_connection_string(
                    settings.azure.storage_connection_string,
                ).get_container_client(container=container)
            elif settings.azure.storage_blob_container_url:
                self.container_client = ContainerClient.from_container_url(
                    settings.azure.storage_blob_container_url,
                )
                if settings.azure.storage_blob_validate_container_name:
                    assert container == self.container_client.container_name
            else:
                assert container is not None
                if not settings.azure.storage_account_url:
                    message = "TILECLOUD_CHAIN__AZURE__STORAGE_ACCOUNT_URL is not configured"
                    raise ValueError(message)
                self.container_client = BlobServiceClient(
                    account_url=settings.azure.storage_account_url,
                    credential=DefaultAzureCredential(),  # type: ignore[arg-type]
                ).get_container_client(container=container)
        else:
            self.container_client = container_client

        self.tilelayout = tilelayout
        self.dry_run = dry_run
        self.cache_control = cache_control

    async def __contains__(self, tile: Tile) -> bool:
        """Return true if this store contains ``tile``."""
        if not tile:
            return False
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        blob = self.container_client.get_blob_client(blob=key_name)
        return await blob.exists()

    async def delete_one(self, tile: Tile) -> Tile:
        """Delete a tile from the store."""
        try:
            key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
            if not self.dry_run:
                blob = self.container_client.get_blob_client(blob=key_name)
                if blob.exists():
                    blob.delete_blob()
        except Exception as exc:  # pylint: disable=broad-except # noqa: BLE001
            _LOGGER.warning("Failed to delete tile %s", tile.tilecoord, exc_info=exc)
            tile.error = exc
        return tile

    async def get_one(self, tile: Tile) -> Tile | None:
        """Get a tile from the store."""
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        try:
            blob = self.container_client.get_blob_client(blob=key_name)
            if not await blob.exists():
                return None
            download_result = await blob.download_blob()
            data = await download_result.readall()
            assert isinstance(data, bytes) or data is None, type(data)
            tile.data = data
            properties = await blob.get_blob_properties()
            tile.content_encoding = properties.content_settings.content_encoding
            tile.content_type = properties.content_settings.content_type
        except Exception as exc:  # pylint: disable=broad-except # noqa: BLE001
            _LOGGER.warning("Failed to get tile %s", tile.tilecoord, exc_info=exc)
            tile.error = exc
        return tile

    async def get(self, tiles: AsyncIterator[Tile]) -> AsyncIterator[Tile | None]:
        """Get tiles from the store."""
        async for tile in tiles:
            yield await self.get_one(tile)

    async def list(self) -> AsyncIterator[Tile]:
        """List all the tiles in the store."""
        prefix = getattr(self.tilelayout, "prefix", "")

        async for blob in self.container_client.list_blobs(name_starts_with=prefix):
            try:
                assert isinstance(blob.name, str)
                tilecoord = self.tilelayout.tilecoord(blob.name)
            except ValueError:
                continue
            blob_data = self.container_client.get_blob_client(blob=blob.name)
            yield Tile(tilecoord, data=await (await blob_data.download_blob()).readall())

    async def put_one(self, tile: Tile) -> Tile:
        """Store ``tile`` in the store."""
        assert tile.data is not None
        key_name = self.tilelayout.filename(tile.tilecoord, tile.metadata)
        if not self.dry_run:
            try:
                blob = self.container_client.get_blob_client(blob=key_name)
                await blob.upload_blob(
                    tile.data,
                    overwrite=True,
                    content_settings=ContentSettings(
                        content_type=tile.content_type,
                        content_encoding=tile.content_encoding,
                        cache_control=self.cache_control,
                    ),
                )
            except Exception as exc:  # pylint: disable=broad-except # noqa: BLE001
                _LOGGER.warning("Failed to put tile %s", tile.tilecoord, exc_info=exc)
                tile.error = exc

        return tile
