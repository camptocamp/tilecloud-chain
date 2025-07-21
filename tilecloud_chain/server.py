"""The server to serve the tiles."""

# Copyright (c) 2013-2025 by Stéphane Brunner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 3. Neither the name of Camptocamp nor the names of its contributors may
# be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
import html
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Annotated, Any, ClassVar, NamedTuple, cast
from urllib.parse import urlencode

import aiofiles
import aiohttp
import botocore.exceptions
import fastapi
import html_sanitizer
import tilecloud.store.s3
from azure.core.exceptions import ResourceNotFoundError
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import Summary
from tilecloud import Tile, TileCoord

import tilecloud_chain
import tilecloud_chain.configuration
from tilecloud_chain import (
    TileGeneration,
    configuration,
    controller,
    get_azure_container_client,
    internal_mapcache,
)
from tilecloud_chain.store import AsyncTileStore

_LOGGER = logging.getLogger(__name__)

_GET_TILE = Summary("tilecloud_chain_get_tile", "Time to get the tiles", ["storage"])

_TILEGENERATION: TileGeneration | None = None

_SANITIZER = html_sanitizer.Sanitizer(
    {
        "tags": {
            "unexisting",
        },
        "attributes": {},
        "empty": set(),
        "separate": set(),
        "keep_typographic_whitespace": True,
    },
)


async def init_tilegeneration(config_file: Path | None) -> None:
    """Initialize the tile generation."""
    global _TILEGENERATION  # pylint: disable=global-statement
    if _TILEGENERATION is None:
        if config_file is not None:
            _LOGGER.info("Use config file: '%s'", config_file)
        log_level = os.environ.get("TILE_SERVER_LOGLEVEL")

        class Options(NamedTuple):
            verbose: bool
            debug: bool
            quiet: bool
            bbox: None
            zoom: None
            test: None
            near: None
            time: None
            geom: bool
            ignore_error: bool

        _TILEGENERATION = TileGeneration(
            config_file,
            Options(  # type: ignore[arg-type]
                log_level == "verbose",
                log_level == "debug",
                log_level == "quiet",
                None,
                None,
                None,
                None,
                None,
                geom=True,
                ignore_error=False,
            ),
            configure_logging=False,
            multi_task=False,
            maxconsecutive_errors=False,
        )
        await _TILEGENERATION.ainit()


class DatedStore:
    """Store with timestamp to be able to invalidate it on configuration change."""

    def __init__(self, store: AsyncTileStore, mtime: float) -> None:
        """Initialize."""
        self.store = store
        self.mtime = mtime


class DatedFilter:
    """Filter with timestamp to be able to invalidate it on configuration change."""

    def __init__(self, layer_filter: tilecloud_chain.IntersectGeometryFilter | None, mtime: float) -> None:
        """Initialize."""
        self.filter = layer_filter
        self.mtime = mtime


class FastAPIServer:
    """The FastAPI implementation of the WMTS server."""

    wmts_path: str = ""
    static_path: ClassVar[list[str]] = []

    def __init__(self) -> None:
        """Initialize."""
        self.filter_cache: dict[Path, dict[str, DatedFilter]] = {}
        self.s3_client_cache: dict[str, botocore.client.S3] = {}  # pylint: disable=no-member
        self.store_cache: dict[Path, dict[str, DatedStore]] = {}

    async def init(self) -> None:
        """Initialize the server."""
        try:
            assert _TILEGENERATION

            self.wmts_path = (
                await _TILEGENERATION.get_main_config()
                .config["server"]
                .get("wmts_path", configuration.WMTS_PATH_DEFAULT)
            )
            self.static_path = (
                await _TILEGENERATION.get_main_config()
                .config["server"]
                .get("static_path", configuration.STATIC_PATH_DEFAULT)
                .split("/")
            )
        except Exception:
            _LOGGER.exception("Initialization error")
            raise

    @staticmethod
    def get_expires_hours(config: tilecloud_chain.DatedConfig) -> float:
        """Get the expiration time in hours."""
        return config.config.get("server", {}).get("expires", tilecloud_chain.configuration.EXPIRES_DEFAULT)

    @staticmethod
    def get_static_allow_extension(config: tilecloud_chain.DatedConfig) -> list[str]:
        """Get the allowed extensions in the static view."""
        return config.config["server"].get(
            "static_allow_extension",
            ["jpeg", "png", "xml", "js", "html", "css"],
        )

    @staticmethod
    def get_cache_name(config: tilecloud_chain.DatedConfig) -> str:
        """Get the cache name."""
        return config.config["server"].get(
            "cache",
            config.config["generation"].get("default_cache", configuration.DEFAULT_CACHE_DEFAULT),
        )

    def get_s3_client(self, config: tilecloud_chain.DatedConfig) -> "botocore.client.S3":
        """Get the AWS S3 client."""
        cache_s3 = cast("tilecloud_chain.configuration.CacheS3", self.get_cache(config))
        if cache_s3.get("host", "aws") in self.s3_client_cache:
            return self.s3_client_cache[cache_s3.get("host", "aws")]
        for n in range(10):
            try:
                client = tilecloud.store.s3.get_client(cache_s3.get("host"))
                self.s3_client_cache[cache_s3.get("host", "aws")] = client
            except KeyError as e:
                _LOGGER.warning("Error while getting the S3 client: %s", e, exc_info=True)
                error = e
            else:
                return client
            time.sleep(n * 10)
        raise error

    def get_cache(self, config: tilecloud_chain.DatedConfig) -> tilecloud_chain.configuration.Cache:
        """Get the cache from the config."""
        return config.config["caches"][self.get_cache_name(config)]

    @staticmethod
    def get_layers(config: tilecloud_chain.DatedConfig) -> list[str]:
        """Get the layer from the config."""
        layers: list[str] = cast("list[str]", config.config.get("layers", {}).keys())
        return config.config["server"].get("layers", layers)

    def get_filter(
        self,
        config: tilecloud_chain.DatedConfig,
        layer_name: str,
    ) -> tilecloud_chain.IntersectGeometryFilter | None:
        """Get the filter from the config."""
        dated_filter = self.filter_cache.get(config.file, {}).get(layer_name)

        if dated_filter is not None and dated_filter.mtime == config.mtime:
            return dated_filter.filter

        assert _TILEGENERATION

        layer_filter = (
            tilecloud_chain.IntersectGeometryFilter(gene=_TILEGENERATION)
            if config.config["server"].get("geoms_redirect", configuration.GEOMETRIES_REDIRECT_DEFAULT)
            else None
        )

        self.filter_cache.setdefault(config.file, {})[layer_name] = DatedFilter(layer_filter, config.mtime)
        return layer_filter

    def get_store(
        self,
        config: tilecloud_chain.DatedConfig,
        layer_name: str,
        grid_name: str,
    ) -> AsyncTileStore | None:
        """Get the store from the config."""
        dated_store = self.store_cache.get(config.file, {}).get(layer_name)

        if dated_store is not None and dated_store.mtime == config.mtime:
            return dated_store.store

        assert _TILEGENERATION

        store = _TILEGENERATION.get_store(
            config,
            self.get_cache(config),
            layer_name,
            grid_name,
            read_only=True,
        )
        if store is None:
            return None
        self.store_cache.setdefault(config.file, {})[layer_name] = DatedStore(store, config.mtime)
        return store

    @staticmethod
    def get_max_zoom_seed(config: tilecloud_chain.DatedConfig, layer_name: str, grid_name: str | None) -> int:
        """Get the max zoom to be bet in the stored cache."""
        if layer_name not in config.config.get("layers", {}):
            _LOGGER.warning("Layer '%s' not found in the configuration file '%s'", layer_name, config.file)
            return 999999
        layer = config.config["layers"][layer_name]
        if "min_resolution_seed" in layer:
            grid = tilecloud_chain.get_grid_config(config, layer_name, grid_name)
            max_zoom_seed = -1
            for zoom, resolution in enumerate(grid["resolutions"]):
                if resolution >= layer["min_resolution_seed"]:
                    max_zoom_seed = zoom
            return max_zoom_seed
        return 999999

    def _s3_read(
        self,
        key_name: str,
        headers: dict[str, str],
        config: tilecloud_chain.DatedConfig,
    ) -> FastAPIResponse:
        cache = self.get_cache(config)
        try:
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            bucket = cache_s3
            response = self.get_s3_client(config).get_object(Bucket=bucket, Key=key_name)
            body = response["Body"]
            try:
                headers["Content-Type"] = response.get("ContentType")
                return FastAPIResponse(content=body.read(), headers=headers)
            finally:
                body.close()
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return self.error(config, 404, key_name + " not found")
            raise

    async def _get(
        self,
        path: str,
        headers: dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> FastAPIResponse:
        """Get capabilities or other static files."""
        assert _TILEGENERATION
        cache = self.get_cache(config)

        if cache["type"] == "s3":
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            key_name = Path(cache_s3["folder"]) / path
            try:
                with _GET_TILE.labels(storage="s3").time():
                    return self._s3_read(str(key_name), headers, config, **kwargs)
            except Exception:  # pylint: disable=broad-exception-caught
                del self.s3_client_cache[cache_s3.get("host", "aws")]
                with _GET_TILE.labels(storage="s3").time():
                    return self._s3_read(str(key_name), headers, config, **kwargs)
        if cache["type"] == "azure":
            cache_azure = cast("tilecloud_chain.configuration.CacheAzure", cache)
            key_name = Path(cache_azure["folder"]) / path
            try:
                with _GET_TILE.labels(storage="azure").time():
                    blob = get_azure_container_client(container=cache_azure["container"]).get_blob_client(
                        blob=str(key_name),
                    )
                properties = await blob.get_blob_properties()
                data = await (await blob.download_blob()).readall()
                return FastAPIResponse(
                    content=data,
                    headers={
                        "Content-Encoding": cast("str", properties.content_settings.content_encoding),
                        "Content-Type": cast("str", properties.content_settings.content_type),
                    },
                )
            except ResourceNotFoundError:
                return self.error(config, 404, f"{path} not found", **kwargs)
        else:
            cache_filesystem = cast("tilecloud_chain.configuration.CacheFilesystem", cache)
            folder = Path(cache_filesystem["folder"] or "")
            if path.split(".")[-1] not in self.get_static_allow_extension(config):
                return self.error(config, 403, "Extension not allowed", **kwargs)
            p = folder / path
            if not p.is_file():
                return self.error(config, 404, f"{path} not found", **kwargs)
            async with aiofiles.open(p, "rb") as file:
                data = await file.read()
            content_type = mimetypes.guess_type(p)[0]
            if content_type:
                headers["Content-Type"] = content_type
            return FastAPIResponse(content=data, headers=headers)

    async def serve(self, params: dict[str, str], config: tilecloud_chain.DatedConfig) -> FastAPIResponse:
        """Async serve method for FastAPI."""
        if not config or not config.config:
            raise HTTPException(
                status_code=404,
                detail="No configuration file found for the host or the configuration has an error, see logs for details",
            )

        try:
            dimensions = []
            metadata = {}
            assert _TILEGENERATION

            if params["SERVICE"] != "WMTS":
                raise HTTPException(status_code=400, detail=f"Wrong Service '{params['SERVICE']}'")  # noqa: TRY301
            if params["VERSION"] != "1.0.0":
                raise HTTPException(status_code=400, detail=f"Wrong Version '{params['VERSION']}'")  # noqa: TRY301

            if params["REQUEST"] == "GetCapabilities":
                headers = {
                    "Content-Type": "application/xml",
                    "Expires": (
                        datetime.datetime.now(tz=datetime.timezone.utc)
                        + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                }
                cache = self.get_cache(config)
                if "wmtscapabilities_file" in cache:
                    wmtscapabilities_file = cache["wmtscapabilities_file"]
                    return await self._get(wmtscapabilities_file, headers, config=config)
                body = await controller.get_wmts_capabilities(
                    _TILEGENERATION,
                    self.get_cache_name(config),
                    config=config,
                )
                assert body
                headers["Content-Type"] = "application/xml"
                return FastAPIResponse(content=body.encode("utf-8"), headers=headers)

            if (
                "FORMAT" not in params
                or "LAYER" not in params
                or "TILEMATRIXSET" not in params
                or "TILEMATRIX" not in params
                or "TILEROW" not in params
                or "TILECOL" not in params
            ):
                raise HTTPException(status_code=400, detail="Not all required parameters are present")  # noqa: TRY301

            if params["LAYER"] in self.get_layers(config):
                layer = cast(
                    "tilecloud_chain.configuration.LayerWms",
                    config.config["layers"][params["LAYER"]],
                )
            else:
                raise HTTPException(status_code=400, detail=f"Wrong Layer '{params['LAYER']}'")  # noqa: TRY301

            for dimension in layer.get("dimensions", []):
                value = (
                    params[dimension["name"].upper()]
                    if dimension["name"].upper() in params
                    else dimension["default"]
                )
                dimensions.append(value)
                metadata["dimension_" + dimension["name"]] = value

            if params["STYLE"] != layer["wmts_style"]:
                raise HTTPException(status_code=400, detail=f"Wrong Style '{params['STYLE']}'")  # noqa: TRY301
            grids = tilecloud_chain.get_grid_names(config, params["LAYER"])
            if params["TILEMATRIXSET"] not in grids:
                grids_string = "'" + "', '".join(grids) + "'"
                raise HTTPException(  # noqa: TRY301
                    status_code=400,
                    detail=f"Wrong TileMatrixSet '{params['TILEMATRIXSET']}' should be in {grids_string}",
                )
            grid = config.config["grids"][params["TILEMATRIXSET"]]

            metadata["layer"] = params["LAYER"]
            metadata["config_file"] = str(config.file)
            metadata["grid"] = params["TILEMATRIXSET"]
            tile = Tile(
                TileCoord(
                    # TODO: fix for matrix_identifier = resolution # noqa: TD003
                    int(params["TILEMATRIX"]),
                    int(params["TILECOL"]),
                    int(params["TILEROW"]),
                ),
                metadata=metadata,
            )

            if params["REQUEST"] == "GetFeatureInfo":
                if "I" not in params or "J" not in params or "INFO_FORMAT" not in params:
                    raise HTTPException(status_code=400, detail="Not all required parameters are present")  # noqa: TRY301
                if "query_layers" in layer:
                    return await self.forward(
                        config,
                        layer["url"]
                        + "?"
                        + urlencode(
                            {
                                "SERVICE": "WMS",
                                "VERSION": layer.get("version", "1.1.1"),
                                "REQUEST": "GetFeatureInfo",
                                "LAYERS": layer.get("layers", ""),
                                "QUERY_LAYERS": layer.get("query_layers", layer.get("layers", "")),
                                "STYLES": params["STYLE"],
                                "FORMAT": params["FORMAT"],
                                "INFO_FORMAT": params["INFO_FORMAT"],
                                "WIDTH": grid.get(
                                    "tile_size",
                                    configuration.TILE_SIZE_DEFAULT,
                                ),
                                "HEIGHT": grid.get(
                                    "tile_size",
                                    configuration.TILE_SIZE_DEFAULT,
                                ),
                                "SRS": grid.get(
                                    "srs",
                                    configuration.SRS_DEFAULT,
                                ),
                                "BBOX": _TILEGENERATION.get_grid(config, params["TILEMATRIXSET"]).extent(
                                    tile.tilecoord,
                                ),
                                "X": params["I"],
                                "Y": params["J"],
                            },
                        ),
                        no_cache=True,
                    )
                raise HTTPException(status_code=400, detail=f"Layer '{params['LAYER']}' not queryable")  # noqa: TRY301

            if params["REQUEST"] != "GetTile":
                raise HTTPException(status_code=400, detail=f"Wrong Request '{params['REQUEST']}'")  # noqa: TRY301

            if params["FORMAT"] != layer["mime_type"]:
                raise HTTPException(status_code=400, detail=f"Wrong Format '{params['FORMAT']}'")  # noqa: TRY301

            return await self._get_tile(config, layer, tile, params)

        except HTTPException:
            raise
        except Exception:
            _LOGGER.exception("An unknown error occurred")
            raise HTTPException(status_code=500, detail="An unknown error occurred")  # noqa: B904

    async def _get_tile(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
        params: dict[str, str],
        **kwargs: Any,
    ) -> FastAPIResponse:
        if tile.tilecoord.z > self.get_max_zoom_seed(config, params["LAYER"], params["TILEMATRIXSET"]):
            return await self._map_cache(config, layer, tile, kwargs)

        layer_filter = self.get_filter(config, params["LAYER"])
        if layer_filter:
            meta_size = layer.get("meta_size", configuration.LAYER_META_SIZE_DEFAULT)
            meta_tilecoord = (
                TileCoord(
                    # TODO: fix for matrix_identifier = resolution # noqa: TD003
                    tile.tilecoord.z,
                    round(tile.tilecoord.x / meta_size * meta_size),
                    round(tile.tilecoord.y / meta_size * meta_size),
                    meta_size,
                )
                if meta_size != 1
                else tile.tilecoord
            )
            if not layer_filter.filter_tilecoord(
                config,
                meta_tilecoord,
                params["LAYER"],
                params["TILEMATRIXSET"],
                host=self.get_host(**kwargs),
            ):
                return await self._map_cache(config, layer, tile, kwargs)

        store = self.get_store(config, params["LAYER"], params["TILEMATRIXSET"])
        if store is None:
            return self.error(
                config,
                400,
                f"No store found for layer '{params['LAYER']}'",
                **kwargs,
            )

        cache = self.get_cache(config)
        with _GET_TILE.labels(storage=cache["type"]).time():
            tile2 = await store.get_one(tile)

        if tile2 and tile2.data is not None:
            if tile2.error:
                return self.error(config, 500, tile2.error, **kwargs)

            assert tile2.content_type
            return FastAPIResponse(
                content=tile2.data,
                headers={
                    "Content-Type": tile2.content_type,
                    "Expires": (
                        datetime.datetime.now(tz=datetime.timezone.utc)
                        + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Tile-Backend": "Cache",
                },
            )
        return self.error(config, 204, **kwargs)

    async def _map_cache(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
        kwargs: dict[str, Any],
    ) -> FastAPIResponse:
        """Get the tile on a cache of tile."""
        assert _TILEGENERATION
        return await internal_mapcache.fetch(config, self, _TILEGENERATION, layer, tile, kwargs)

    async def forward(
        self,
        config: tilecloud_chain.DatedConfig,
        url: str,
        headers: Any | None = None,
        no_cache: bool = False,
        **kwargs: Any,
    ) -> FastAPIResponse:
        """Forward the request on a fallback WMS server."""
        if headers is None:
            headers = {}
        if no_cache:
            headers["Cache-Control"] = "no-cache"
            headers["Pragma"] = "no-cache"

        async with aiohttp.ClientSession() as session, session.get(url, headers=headers) as response:
            if response.status == 200:
                response_headers = dict(response.headers)
                if no_cache:
                    response_headers["Cache-Control"] = "no-cache, no-store"
                    response_headers["Pragma"] = "no-cache"
                else:
                    response_headers["Expires"] = (
                        datetime.datetime.now(tz=datetime.timezone.utc)
                        + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat()
                    response_headers["Cache-Control"] = f"max-age={3600 * self.get_expires_hours(config)}"
                    response_headers["Access-Control-Allow-Origin"] = "*"
                    response_headers["Access-Control-Allow-Methods"] = "GET"
                content = await response.read()
                return FastAPIResponse(content=content, headers=response_headers)
            safe_reason = html.escape(response.reason).replace("\n", " ").replace("\r", " ")[:100]
            safe_content = (
                html.escape(_SANITIZER.sanitize(await response.text())).replace("\n", " ").replace("\r", " ")[:1000]
                if response.content_type == "text/html"
                else html.escape(await response.text()).replace("\n", "<br>").replace("\r", "<br>")[:1000]
            )
            message = f"The URL '{url}' return '{response.status} {safe_reason}', content:\n{safe_content}"
            _LOGGER.warning(message)
            return self.error(config, 502, message=message, **kwargs)

    def error(
        self,
        config: tilecloud_chain.DatedConfig,
        code: int,
        message: Exception | str | None = "",
    ) -> FastAPIResponse:
        """Build the FastAPI error response."""
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
        }
        if code < 300:
            headers.update(
                {
                    "Expires": (
                        datetime.datetime.now(tz=datetime.timezone.utc)
                        + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                },
            )
        raise HTTPException(status_code=code, detail=str(message) if message else "", headers=headers)


server = FastAPIServer()
app = FastAPI(title="TileCloud-chain WMTS API")


async def startup(main_app: FastAPI) -> None:
    """Initialize the FastAPI app."""
    del main_app  # Unused parameter
    config_file_path = os.environ.get("TILEGENERATION_CONFIGFILE")
    config_file = Path(config_file_path) if config_file_path else None
    await init_tilegeneration(config_file)
    await server.init()


async def get_host_config(fastapi_request: Request) -> tilecloud_chain.DatedConfig:
    """Get the host configuration based on the request."""
    global _TILEGENERATION  # pylint: disable=global-statement,global-variable-not-assigned
    if _TILEGENERATION is None:
        raise HTTPException(status_code=500, detail="TileGeneration not initialized")

    host = fastapi_request.client.host if fastapi_request.client else "localhost"
    config = _TILEGENERATION.get_host_config(host)
    if not config:
        raise HTTPException(status_code=404, detail=f"No configuration found for host '{host}'")

    return config


@app.get("/{version}/wmtscapabilities.xml")
async def get_wmts_capabilities(
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
) -> FastAPIResponse:
    """Get the WMTS capabilities."""
    assert _TILEGENERATION

    params = {
        "SERVICE": "WMTS",
        "VERSION": version,
        "REQUEST": "GetCapabilities",
    }

    return await server.serve(params, config)


@app.get(
    "/{version}/{layer}/{style}/{dimensions_params:path}){tilematrixset}/{tilematrix}/{tilerow}/{tilecol}.{extension}",
)
async def get_wmts_tile(
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    layer: Annotated[str, fastapi.Path(..., description="Layer name")],
    style: Annotated[str, fastapi.Path(..., description="Style name")],
    dimensions_params: Annotated[str, fastapi.Path(..., description="Dimensions parameters")],
    tilematrixset: Annotated[str, fastapi.Path(..., description="Tile matrix set")],
    tilematrix: Annotated[str, fastapi.Path(..., description="Tile matrix")],
    tilerow: Annotated[str, fastapi.Path(..., description="Tile row")],
    tilecol: Annotated[str, fastapi.Path(..., description="Tile column")],
    extension: Annotated[str, fastapi.Path(..., description="File extension")],
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
) -> FastAPIResponse:
    """Get the WMTS."""

    del extension  # Needed for FastAPI documentation

    if layer in server.get_layers(config):
        layer = cast(
            "tilecloud_chain.configuration.LayerWms",
            config.config["layers"][layer],
        )
    else:
        raise HTTPException(status_code=400, detail=f"Wrong Layer '{layer}'")

    params = {
        "SERVICE": "WMTS",
        "VERSION": version,
        "REQUEST": "GetTile",
        "LAYER": layer,
        "STYLE": style,
        "TILEMATRIXSET": tilematrixset,
        "TILEMATRIX": tilematrix,
        "TILEROW": tilerow,
        "TILECOL": tilecol,
    }

    for index, dimension in enumerate(layer.get("dimensions", {})):
        params[dimension["name"].upper()] = dimensions_params[index]

    params["FORMAT"] = layer["mime_type"]

    return await server.serve(params, config)


@app.get(
    "/{version}/{layer}/{style}/{dimensions_params:path}){tilematrixset}/{tilematrix}/{tilerow}/{tilecol}/{i}/{j}",
)
async def get_wmts_feature_info(
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    layer: Annotated[str, fastapi.Path(..., description="Layer name")],
    style: Annotated[str, fastapi.Path(..., description="Style name")],
    dimensions_params: Annotated[str, fastapi.Path(..., description="Dimensions parameters")],
    tilematrixset: Annotated[str, fastapi.Path(..., description="Tile matrix set")],
    tilematrix: Annotated[str, fastapi.Path(..., description="Tile matrix")],
    tilerow: Annotated[str, fastapi.Path(..., description="Tile row")],
    tilecol: Annotated[str, fastapi.Path(..., description="Tile column")],
    i: Annotated[str, fastapi.Path(..., description="Pixel I coordinate")],
    j: Annotated[str, fastapi.Path(..., description="Pixel J coordinate")],
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
) -> FastAPIResponse:
    """Get the WMTS Feature Info."""

    if layer in server.get_layers(config):
        layer = cast(
            "tilecloud_chain.configuration.LayerWms",
            config.config["layers"][layer],
        )
    else:
        raise HTTPException(status_code=400, detail=f"Wrong Layer '{layer}'")

    params = {
        "SERVICE": "WMTS",
        "VERSION": version,
        "REQUEST": "GetFeatureInfo",
        "LAYER": layer,
        "STYLE": style,
        "TILEMATRIXSET": tilematrixset,
        "TILEMATRIX": tilematrix,
        "TILEROW": tilerow,
        "TILECOL": tilecol,
        "I": i,
        "J": j,
        "INFO_FORMAT": layer.get("info_formats", ["application/vnd.ogc.gml"])[0],
    }

    for index, dimension in enumerate(layer.get("dimensions", {})):
        params[dimension["name"].upper()] = dimensions_params[index]

    return await server.serve(params, config)


@app.get("/")
async def get_kvp(
    fastapi_request: Request,
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
    service: Annotated[str, Query(..., description="Service name")],
    version: Annotated[str, Query(..., description="WMTS version")],
    request: Annotated[str, Query(..., description="Request type")],
    layer: Annotated[str | None, Query(..., description="Layer name")] = None,
    style: Annotated[str | None, Query(..., description="Style name")] = None,
    dimensions: Annotated[str | None, Query(..., description="Dimensions")] = None,
    tilematrixset: Annotated[str | None, Query(..., description="Tile matrix set")] = None,
    tilematrix: Annotated[str | None, Query(..., description="Tile matrix")] = None,
    tilerow: Annotated[str | None, Query(..., description="Tile row")] = None,
    tilecol: Annotated[str | None, Query(..., description="Tile column")] = None,
    i: Annotated[str | None, Query(..., description="Pixel I coordinate")] = None,
    j: Annotated[str | None, Query(..., description="Pixel J coordinate")] = None,
) -> FastAPIResponse:
    """Get the KVP."""

    del (
        layer,
        style,
        dimensions,
        tilematrixset,
        tilematrix,
        tilerow,
        tilecol,
        i,
        j,
    )  # Needed for FastAPI documentation

    if not service or not version or not request:
        raise HTTPException(status_code=400, detail="Not all required parameters are present")

    return await server.serve(fastapi_request.params, config)
