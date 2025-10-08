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

import asyncio
import datetime
import html
import logging
import math
import mimetypes
import os
import time
from copy import copy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, NamedTuple, cast
from urllib.parse import urlencode

import aiofiles
import aiohttp
import botocore.exceptions
import fastapi
import html_sanitizer
import tilecloud.store.s3
import yaml
from azure.core.exceptions import ResourceNotFoundError
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from prometheus_client import Summary
from tilecloud import Tile, TileCoord

import tilecloud_chain
import tilecloud_chain.configuration
from tilecloud_chain import (
    DatedConfig,
    TileGeneration,
    configuration,
    get_azure_container_client,
    get_tile_matrix_identifier,
    internal_mapcache,
)
from tilecloud_chain.controller import validate_generate_wmts_capabilities
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
_TEMPLATES = Jinja2Templates(directory="tilecloud_chain/templates")

# Constants
_ONE_DAY_IN_SECONDS = 86400


# Memory cache for legend configurations (expiration set to _ONE_DAY_IN_SECONDS)
@dataclass
class LegendLayerCache:
    """Cache for legend layer configurations."""

    data: dict[str, Any]
    timestamp: float


_LEGEND_CONFIG_CACHE: dict[str, LegendLayerCache] = {}
_LEGEND_CONFIG_CACHE_LOCK: asyncio.Lock | None = None


async def init_tilegeneration(config_file: Path | None) -> None:
    """Initialize the tile generation."""
    global _TILEGENERATION  # noqa: PLW0603
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


class Server:
    """The FastAPI implementation of the WMTS server."""

    def __init__(self) -> None:
        """Initialize."""
        self.filter_cache: dict[Path, dict[str, DatedFilter]] = {}
        self.s3_client_cache: dict[str, botocore.client.S3] = {}  # pylint: disable=no-member
        self.store_cache: dict[Path, dict[str, DatedStore]] = {}

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
    ) -> Response:
        cache = self.get_cache(config)
        try:
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            bucket = cache_s3
            response = self.get_s3_client(config).get_object(Bucket=bucket, Key=key_name)
            body = response["Body"]
            try:
                headers["Content-Type"] = response.get("ContentType")
                return Response(content=body.read(), headers=headers)
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
    ) -> Response:
        """Get capabilities or other static files."""
        assert _TILEGENERATION
        cache = self.get_cache(config)

        if cache["type"] == "s3":
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            key_name = Path(cache_s3["folder"]) / path
            try:
                with _GET_TILE.labels(storage="s3").time():
                    return self._s3_read(str(key_name), headers, config, **kwargs)
            except Exception:  # noqa: BLE001
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
                headers = {
                    **headers,
                    **(
                        {"Content-Type": properties.content_settings.content_type}
                        if properties.content_settings.content_type
                        else {}
                    ),
                    **(
                        {"Content-Encoding": properties.content_settings.content_encoding}
                        if properties.content_settings.content_encoding
                        else {}
                    ),
                }
                return Response(
                    content=data,
                    headers=headers,
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
            headers = {
                **headers,
                **({"Content-Type": content_type} if content_type else {}),
            }
            return Response(content=data, headers=headers)

    async def serve(
        self,
        params: dict[str, str],
        config: tilecloud_chain.DatedConfig,
        host: str,
        request: Request,
    ) -> Response:
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

                cache_name: str = self.get_cache_name(config)
                if config is None:
                    assert _TILEGENERATION.config_file
                    config = await _TILEGENERATION.get_config(_TILEGENERATION.config_file)

                cache = config.config["caches"][cache_name]
                if not validate_generate_wmts_capabilities(cache, cache_name, exit_=False):
                    raise HTTPException(  # noqa: TRY301
                        status_code=500,
                        detail="Failed to generate WMTS capabilities, invalid configuration",
                    )
                server_config = (await _TILEGENERATION.get_main_config()).config.get("server")

                base_urls = _get_base_urls(cache)

                def ending_slash(url: str) -> str:
                    """Ensure the URL ends with a slash."""
                    return url if url.endswith("/") else url + "/"

                base_urls = [ending_slash(url) for url in base_urls]

                await _fill_legend(cache, base_urls[0], config=config)

                wmts_path = ""
                if server_config is not None:
                    wmts_path = server_config.get(
                        "wmts_path",
                        tilecloud_chain.configuration.WMTS_PATH_DEFAULT,
                    )
                    if wmts_path and not wmts_path.endswith("/"):
                        wmts_path += "/"

                return _TEMPLATES.TemplateResponse(
                    "wmts_get_capabilities.jinja",
                    {
                        "request": request,
                        "config": config,
                        "layers": config.config.get("layers", {}),
                        "layer_legends": _TILEGENERATION.layer_legends,
                        "grids": config.config["grids"],
                        "base_urls": base_urls,
                        "base_url_postfix": wmts_path,
                        "get_tile_matrix_identifier": get_tile_matrix_identifier,
                        "server": server_config is not None,
                        "has_metadata": "metadata" in config.config,
                        "metadata": config.config.get("metadata"),
                        "has_provider": "provider" in config.config,
                        "provider": config.config.get("provider"),
                        "get_grid_names": tilecloud_chain.get_grid_names,
                        "enumerate": enumerate,
                        "ceil": math.ceil,
                        "int": int,
                        "sorted": sorted,
                        "configuration": configuration,
                    },
                    headers=headers,
                )

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

            return await self._get_tile(config, layer, tile, params, host)

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
        host: str,
    ) -> Response:
        if tile.tilecoord.z > self.get_max_zoom_seed(config, params["LAYER"], params["TILEMATRIXSET"]):
            return await self._map_cache(config, layer, tile)

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
                host=host,
            ):
                return await self._map_cache(config, layer, tile)

        store = self.get_store(config, params["LAYER"], params["TILEMATRIXSET"])
        if store is None:
            return self.error(
                config,
                400,
                f"No store found for layer '{params['LAYER']}'",
            )

        cache = self.get_cache(config)
        with _GET_TILE.labels(storage=cache["type"]).time():
            tile2 = await store.get_one(tile)

        if tile2 and tile2.data is not None:
            if tile2.error:
                return self.error(config, 500, tile2.error)

            assert tile2.content_type
            return Response(
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
        return self.error(config, 204)

    async def _map_cache(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
    ) -> Response:
        """Get the tile on a cache of tile."""
        assert _TILEGENERATION
        return await internal_mapcache.fetch(config, self, _TILEGENERATION, layer, tile)

    async def forward(
        self,
        config: tilecloud_chain.DatedConfig,
        url: str,
        headers: Any | None = None,
        no_cache: bool = False,
        **kwargs: Any,
    ) -> Response:
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
                return Response(content=content, headers=response_headers)
            safe_reason = (
                html.escape(response.reason).replace("\n", " ").replace("\r", " ")[:100]
                if response.reason
                else ""
            )
            safe_content = (
                html.escape(_SANITIZER.sanitize(await response.text()))
                .replace("\n", " ")
                .replace("\r", " ")[:1000]
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
    ) -> Response:
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


server = Server()
router = fastapi.APIRouter()


async def startup(_main_app: FastAPI) -> None:
    """Initialize the FastAPI app."""
    config_file_path = os.environ.get("TILEGENERATION_CONFIGFILE")
    config_file = Path(config_file_path) if config_file_path else None
    await init_tilegeneration(config_file)


def get_host_name(request: Request) -> str:
    """Get the host name from the request."""
    # Get the Host header
    host = request.headers.get("Host")

    # Get the X-Forwarded-Host header
    x_forwarded_host = request.headers.get("X-Forwarded-Host")

    # Get the Forwarded header
    forwarded = request.headers.get("Forwarded")

    # Determine the host name
    if forwarded:
        # Parse the Forwarded header to get the host
        # The Forwarded header can have multiple pieces of information
        # Example: Forwarded: host=example.com;proto=https
        forwarded_parts = forwarded.split(";")
        for part in forwarded_parts:
            if part.strip().startswith("host="):
                host_name: str | None = part.strip().split("=")[1]
                break
    elif x_forwarded_host:
        host_name = x_forwarded_host.split(",")[0]  # In case of multiple values
    else:
        host_name = host

    if not host_name:
        raise HTTPException(status_code=400, detail="Host name not found in request headers")

    return host_name


async def get_host_config(
    host: Annotated[str, fastapi.Depends(get_host_name)],
) -> tilecloud_chain.DatedConfig:
    """Get the host configuration based on the request."""
    global _TILEGENERATION  # noqa: PLW0602
    if _TILEGENERATION is None:
        raise HTTPException(status_code=500, detail="TileGeneration not initialized")

    config = await _TILEGENERATION.get_host_config(host)
    if not config:
        raise HTTPException(status_code=404, detail=f"No configuration found for host '{host}'")

    return config


@router.get("/{version}/WMTSCapabilities.xml", summary="Get the WMTS capabilities.")
async def wmts_capabilities(
    request: Request,
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
    host: Annotated[str, fastapi.Depends(get_host_name)],
) -> Response:
    """Get the WMTS capabilities."""
    assert _TILEGENERATION

    params = {
        "SERVICE": "WMTS",
        "VERSION": version,
        "REQUEST": "GetCapabilities",
    }

    return await server.serve(params, config, host, request)


@router.get(
    "/{version}/{layer}/{style}/{dimensions_parameters:path}/{tilematrixset}/{tilematrix}/{tilerow}/{tilecol}.{extension}",
    summary="Get the WMTS tile.",
)
async def wmts_tile(
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    layer: Annotated[str, fastapi.Path(..., description="Layer name")],
    style: Annotated[str, fastapi.Path(..., description="Style name")],
    dimensions_parameters: Annotated[str, fastapi.Path(..., description="Dimensions parameters")],
    tilematrixset: Annotated[str, fastapi.Path(..., description="Tile matrix set")],
    tilematrix: Annotated[str, fastapi.Path(..., description="Tile matrix")],
    tilerow: Annotated[str, fastapi.Path(..., description="Tile row")],
    tilecol: Annotated[str, fastapi.Path(..., description="Tile column")],
    extension: Annotated[str, fastapi.Path(..., description="File extension")],
    request: Request,
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
    host: Annotated[str, fastapi.Depends(get_host_name)],
) -> Response:
    """
    Get the WMTS tile.

    For low zoom levels, the tile is served from the static cache (filesystem or object storage like S3 or Azure).

    For high zoom levels, the tile is generated dynamically:
    - From dynamic cache (Redis).
    - Generate from WMS if it does not exist in the cache.
    """

    del extension  # Needed for FastAPI documentation

    if layer in server.get_layers(config):
        layer_obj = cast(
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

    for index, dimension in enumerate(layer_obj.get("dimensions", {})):
        params[dimension["name"].upper()] = dimensions_parameters[index]

    params["FORMAT"] = layer_obj["mime_type"]

    return await server.serve(params, config, host, request)


@router.get(
    "/{version}/{layer}/{style}/{dimensions_parameters:path}/{tilematrixset}/{tilematrix}/{tilerow}/{tilecol}/{i}/{j}",
    summary="Get the WMTS Feature Info.",
)
async def wmts_feature_info(
    version: Annotated[str, fastapi.Path(..., description="WMTS version")],
    layer: Annotated[str, fastapi.Path(..., description="Layer name")],
    style: Annotated[str, fastapi.Path(..., description="Style name")],
    dimensions_parameters: Annotated[str, fastapi.Path(..., description="Dimensions parameters")],
    tilematrixset: Annotated[str, fastapi.Path(..., description="Tile matrix set")],
    tilematrix: Annotated[str, fastapi.Path(..., description="Tile matrix")],
    tilerow: Annotated[str, fastapi.Path(..., description="Tile row")],
    tilecol: Annotated[str, fastapi.Path(..., description="Tile column")],
    i: Annotated[str, fastapi.Path(..., description="Pixel I coordinate")],
    j: Annotated[str, fastapi.Path(..., description="Pixel J coordinate")],
    request: Request,
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
    host: Annotated[str, fastapi.Depends(get_host_name)],
) -> Response:
    """
    Get the WMTS Feature Info.

    This is a proxy to a WMS GetFeatureInfo.
    """

    if layer in server.get_layers(config):
        layer_obj = cast(
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
        "INFO_FORMAT": layer_obj.get("info_formats", ["application/vnd.ogc.gml"])[0],
    }

    for index, dimension in enumerate(layer_obj.get("dimensions", {})):
        params[dimension["name"].upper()] = dimensions_parameters[index]

    return await server.serve(params, config, host, request)


@router.get("/", summary="KVP interface.")
async def wmts_kvp(
    fastapi_request: Request,
    config: Annotated[tilecloud_chain.DatedConfig, fastapi.Depends(get_host_config)],
    host: Annotated[str, fastapi.Depends(get_host_name)],
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
) -> Response:
    """Get the tiles using the KVP (Key-Value Parameters) interface."""

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

    return await server.serve(dict(fastapi_request.query_params), config, host, fastapi_request)


def _get_base_urls(cache: tilecloud_chain.configuration.Cache) -> list[str]:
    base_urls = []
    if "http_url" in cache:
        if "hosts" in cache:
            cc = copy(cache)
            for host in cache["hosts"]:
                cc["host"] = host  # type: ignore[typeddict-unknown-key]
                base_urls.append(cache["http_url"] % cc)
        else:
            base_urls = [cache["http_url"] % cache]
    if "http_urls" in cache:
        base_urls = [url % cache for url in cache["http_urls"]]
    return [url + "/" if url[-1] != "/" else url for url in base_urls]


async def _get(path: str, cache: tilecloud_chain.configuration.Cache) -> bytes | None:
    if cache["type"] == "s3":
        cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
        client = tilecloud.store.s3.get_client(cache_s3.get("host"))
        key_name = Path(cache["folder"]) / path
        bucket = cache_s3["bucket"]
        try:
            response = client.get_object(Bucket=bucket, Key=str(key_name))
            return cast("bytes", response["Body"].read())
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise
    if cache["type"] == "azure":
        cache_azure = cast("tilecloud_chain.configuration.CacheAzure", cache)
        key_name = Path(cache["folder"]) / path
        try:
            blob = get_azure_container_client(container=cache_azure["container"]).get_blob_client(
                blob=str(key_name),
            )
            return await (await blob.download_blob()).readall()
        except ResourceNotFoundError:
            return None
    else:
        cache_filesystem = cast("tilecloud_chain.configuration.CacheFilesystem", cache)
        p = Path(cache_filesystem["folder"]) / path
        if not p.is_file():
            return None
        return p.read_bytes()


async def _get_layer_legend(
    layer_name: str,
    layer: tilecloud_chain.configuration.Layer,
    cache: tilecloud_chain.configuration.Cache,
    base_url: str,
    config: DatedConfig,
    current_time: float,
) -> list[tilecloud_chain.Legend] | None:
    """Get legend configuration for a layer."""
    cache_key = f"{config.file}:{layer_name}"
    legend_config = None

    assert _LEGEND_CONFIG_CACHE_LOCK

    # If not in memory cache or expired, fetch from storage
    async with _LEGEND_CONFIG_CACHE_LOCK:
        if cache_key in _LEGEND_CONFIG_CACHE:
            cache_entry = _LEGEND_CONFIG_CACHE[cache_key]
            cache_timestamp = cache_entry.timestamp
            # Check if cache is less than one day old
            if current_time - cache_timestamp < _ONE_DAY_IN_SECONDS:
                legend_config = cache_entry.data

    if legend_config is None:
        legend_config_str = await _get(
            f"1.0.0/{layer_name}/{layer['wmts_style']}/legend.yaml",
            cache,
        )
        if legend_config_str is not None:
            legend_config_io = BytesIO(legend_config_str)
            legend_config = yaml.load(legend_config_io, Loader=yaml.SafeLoader)
            async with _LEGEND_CONFIG_CACHE_LOCK:
                _LEGEND_CONFIG_CACHE[cache_key] = LegendLayerCache(
                    data=legend_config or {},
                    timestamp=current_time,
                )

    if legend_config:
        return [
            tilecloud_chain.Legend(
                mime_type=legend_metadata["mime_type"],
                href=str(
                    Path(base_url)
                    / "1.0.0"
                    / layer_name
                    / layer["wmts_style"]
                    / f"legend-{legend_metadata['resolution']}.{layer.get('legend_extension', configuration.LAYER_LEGEND_EXTENSION_DEFAULT)}",
                ),
                min_resolution=legend_metadata.get("min_resolution"),
                max_resolution=legend_metadata.get("max_resolution"),
                width=legend_metadata["width"],
                height=legend_metadata["height"],
            )
            for legend_metadata in legend_config["metadata"]
        ]
    return None


async def _fill_legend(
    cache: tilecloud_chain.configuration.Cache,
    base_url: str,
    config: DatedConfig | None = None,
) -> None:
    assert _TILEGENERATION
    if config is None:
        assert _TILEGENERATION.config_file
        config = await _TILEGENERATION.get_config(_TILEGENERATION.config_file)

    current_time = time.time()

    global _LEGEND_CONFIG_CACHE_LOCK  # noqa: PLW0603
    if _LEGEND_CONFIG_CACHE_LOCK is None:
        _LEGEND_CONFIG_CACHE_LOCK = asyncio.Lock()

    # clean up old entries in the cache
    async with _LEGEND_CONFIG_CACHE_LOCK:
        for key, cache_entry in list(_LEGEND_CONFIG_CACHE.items()):
            if cache_entry.timestamp < current_time - _ONE_DAY_IN_SECONDS:
                del _LEGEND_CONFIG_CACHE[key]

    # Collect tasks for layers that need legend retrieval
    tasks = []
    layer_names = []
    for layer_name, layer in config.config.get("layers", {}).items():
        if layer_name not in _TILEGENERATION.layer_legends:
            tasks.append(_get_layer_legend(layer_name, layer, cache, base_url, config, current_time))
            layer_names.append(layer_name)

    # Run all legend retrievals concurrently
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for layer_name, result in zip(layer_names, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.warning("Failed to get legend for layer '%s': %s", layer_name, result)
            elif result is not None:
                _TILEGENERATION.layer_legends[layer_name] = result
