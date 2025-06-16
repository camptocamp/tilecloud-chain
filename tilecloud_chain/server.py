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
import json
import logging
import mimetypes
import os
import resource
import time
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic, NamedTuple, TypeVar, cast
from urllib.parse import parse_qs, urlencode

import aiofiles
import botocore.exceptions
import c2cwsgiutils.prometheus
import c2cwsgiutils.pyramid
import prometheus_client
import prometheus_client.core
import prometheus_client.registry
import psutil
import pyramid.response
import pyramid.session
import requests
import tilecloud.store.s3
from azure.core.exceptions import ResourceNotFoundError
from c2cwsgiutils import health_check
from prometheus_client import REGISTRY, Summary
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPException, exception_response
from pyramid.request import Request
from pyramid.router import Router
from pyramid_mako import add_mako_renderer
from tilecloud import Tile, TileCoord

import tilecloud_chain
import tilecloud_chain.configuration
import tilecloud_chain.security
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

_TILEGENERATION = None


def init_tilegeneration(config_file: Path | None) -> None:
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


Response = TypeVar("Response")


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


class Server(Generic[Response]):
    """The generic implementation of the WMTS server."""

    def __init__(self) -> None:
        """Initialize."""
        try:
            self.filter_cache: dict[Path, dict[str, DatedFilter]] = {}
            self.s3_client_cache: dict[str, botocore.client.S3] = {}  # pylint: disable=no-member
            self.store_cache: dict[Path, dict[str, DatedStore]] = {}

            assert _TILEGENERATION

            self.wmts_path = (
                _TILEGENERATION.get_main_config()
                .config["server"]
                .get("wmts_path", configuration.WMTS_PATH_DEFAULT)
            )
            self.static_path = (
                _TILEGENERATION.get_main_config()
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

    def _read(
        self,
        key_name: str,
        headers: dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> Response:
        cache = self.get_cache(config)
        try:
            cache_s3 = cast("tilecloud_chain.configuration.CacheS3", cache)
            bucket = cache_s3
            response = self.get_s3_client(config).get_object(Bucket=bucket, Key=key_name)
            body = response["Body"]
            try:
                headers["Content-Type"] = response.get("ContentType")
                return self.response(config, body.read(), headers, **kwargs)
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
                    return self._read(str(key_name), headers, config, **kwargs)
            except Exception:  # pylint: disable=broad-exception-caught
                del self.s3_client_cache[cache_s3.get("host", "aws")]
                with _GET_TILE.labels(storage="s3").time():
                    return self._read(str(key_name), headers, config, **kwargs)
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
                return self.response(
                    config,
                    data,
                    {
                        "Content-Encoding": cast("str", properties.content_settings.content_encoding),
                        "Content-Type": cast("str", properties.content_settings.content_type),
                    },
                    **kwargs,
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
            return self.response(config, data, headers, **kwargs)

    def __call__(
        self,
        config: tilecloud_chain.DatedConfig,
        config_file: str,
        environ: dict[str, str],
        start_response: bytes,
    ) -> Response:
        """Build the response on request."""
        params = {}
        for key, value in parse_qs(environ["QUERY_STRING"], keep_blank_values=True).items():
            params[key.upper()] = value[0]

        path = None if len(params) > 0 else environ["PATH_INFO"][1:].split("/")

        return self.serve(path, params, config=config, config_file=config_file, start_response=start_response)

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def serve(
        self,
        path: list[str] | None,
        params: dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> Response:
        """Serve the WMTS requests."""
        if not config or not config.config:
            return self.error(
                config,
                404,
                "No configuration file found for the host or the configuration has an error, see logs for details",
                **kwargs,
            )

        try:
            dimensions = []
            metadata = {}
            assert _TILEGENERATION

            if path:
                if tuple(path[: len(self.static_path)]) == tuple(self.static_path):
                    return self._get_event_loop().run_until_complete(
                        self._get(
                            "/".join(path[len(self.static_path) :]),
                            {
                                "Expires": (
                                    datetime.datetime.now(tz=datetime.timezone.utc)
                                    + datetime.timedelta(hours=self.get_expires_hours(config))
                                ).isoformat(),
                                "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Allow-Methods": "GET",
                            },
                            config=config,
                            **kwargs,
                        ),
                    )
                if len(path) >= 1 and path[0] != self.wmts_path:
                    return self.error(
                        config,
                        404,
                        f"Type '{path[0]}' don't exists, allows values: '{self.wmts_path}' or "
                        f"'{'/'.join(self.static_path)}'",
                        **kwargs,
                    )
                path = path[1:]  # remove type

            if path:
                if len(path) == 2 and path[0] == "1.0.0" and path[1].lower() == "wmtscapabilities.xml":
                    params["SERVICE"] = "WMTS"
                    params["VERSION"] = "1.0.0"
                    params["REQUEST"] = "GetCapabilities"
                elif len(path) < 7:
                    return self.error(config, 400, "Not enough path", **kwargs)
                else:
                    params["SERVICE"] = "WMTS"
                    params["VERSION"] = path[0]

                    params["LAYER"] = path[1]
                    params["STYLE"] = path[2]

                    if params["LAYER"] in self.get_layers(config):
                        layer = cast(
                            "tilecloud_chain.configuration.LayerWms",
                            config.config["layers"][params["LAYER"]],
                        )
                    else:
                        return self.error(config, 400, f"Wrong Layer '{params['LAYER']}'", **kwargs)

                    index = 3
                    dimensions = path[index : index + len(layer.get("dimensions", {}))]
                    for dimension in layer.get("dimensions", {}):
                        metadata["dimension_" + dimension["name"]] = path[index]
                        params[dimension["name"].upper()] = path[index]
                        index += 1

                    last = path[-1].split(".")
                    if len(path) < index + 4:
                        return self.error(config, 400, "Not enough path", **kwargs)
                    params["TILEMATRIXSET"] = path[index]
                    params["TILEMATRIX"] = path[index + 1]
                    params["TILEROW"] = path[index + 2]
                    if len(path) == index + 4:
                        params["REQUEST"] = "GetTile"
                        params["TILECOL"] = last[0]
                        if last[1] != layer["extension"]:
                            return self.error(config, 400, f"Wrong extension '{last[1]}'", **kwargs)
                    elif len(path) == index + 6:
                        params["REQUEST"] = "GetFeatureInfo"
                        params["TILECOL"] = path[index + 3]
                        params["I"] = path[index + 4]
                        params["J"] = last[0]
                        params["INFO_FORMAT"] = layer.get("info_formats", ["application/vnd.ogc.gml"])[0]
                    else:
                        return self.error(config, 400, "Wrong path length", **kwargs)

                    params["FORMAT"] = layer["mime_type"]
            elif "SERVICE" not in params or "REQUEST" not in params or "VERSION" not in params:
                return self.error(config, 400, "Not all required parameters are present", **kwargs)

            if params["SERVICE"] != "WMTS":
                return self.error(config, 400, f"Wrong Service '{params['SERVICE']}'", **kwargs)
            if params["VERSION"] != "1.0.0":
                return self.error(config, 400, f"Wrong Version '{params['VERSION']}'", **kwargs)

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
                    return self._get_event_loop().run_until_complete(
                        self._get(wmtscapabilities_file, headers, config=config, **kwargs),
                    )
                body = self._get_event_loop().run_until_complete(
                    controller.get_wmts_capabilities(
                        _TILEGENERATION,
                        self.get_cache_name(config),
                        config=config,
                    ),
                )
                assert body
                headers["Content-Type"] = "application/xml"
                return self.response(config, body.encode("utf-8"), headers=headers, **kwargs)

            if (
                "FORMAT" not in params
                or "LAYER" not in params
                or "TILEMATRIXSET" not in params
                or "TILEMATRIX" not in params
                or "TILEROW" not in params
                or "TILECOL" not in params
            ):
                return self.error(config, 400, "Not all required parameters are present", **kwargs)

            if not path:
                if params["LAYER"] in self.get_layers(config):
                    layer = cast(
                        "tilecloud_chain.configuration.LayerWms",
                        config.config["layers"][params["LAYER"]],
                    )
                else:
                    return self.error(config, 400, f"Wrong Layer '{params['LAYER']}'", **kwargs)

                for dimension in layer.get("dimensions", []):
                    value = (
                        params[dimension["name"].upper()]
                        if dimension["name"].upper() in params
                        else dimension["default"]
                    )
                    dimensions.append(value)
                    metadata["dimension_" + dimension["name"]] = value

            if params["STYLE"] != layer["wmts_style"]:
                return self.error(config, 400, f"Wrong Style '{params['STYLE']}'", **kwargs)
            grids = tilecloud_chain.get_grid_names(config, params["LAYER"])
            if params["TILEMATRIXSET"] not in grids:
                grids_string = "'" + "', '".join(grids) + "'"
                return self.error(
                    config,
                    400,
                    f"Wrong TileMatrixSet '{params['TILEMATRIXSET']}' should be in {grids_string}",
                    **kwargs,
                )
            grid = config.config["grids"][params["TILEMATRIXSET"]]

            metadata["layer"] = params["LAYER"]
            metadata["config_file"] = str(config.file)
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
                    return self.error(config, 400, "Not all required parameters are present", **kwargs)
                if "query_layers" in layer:
                    return self.forward(
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
                        **kwargs,
                    )
                return self.error(config, 400, f"Layer '{params['LAYER']}' not queryable", **kwargs)

            if params["REQUEST"] != "GetTile":
                return self.error(config, 400, f"Wrong Request '{params['REQUEST']}'", **kwargs)

            if params["FORMAT"] != layer["mime_type"]:
                return self.error(config, 400, f"Wrong Format '{params['FORMAT']}'", **kwargs)

            return self._get_event_loop().run_until_complete(
                self._get_tile(config, layer, tile, params, **kwargs),
            )

        except HTTPException:
            raise
        except Exception:
            _LOGGER.exception("An unknown error occurred")
            raise

    async def _get_tile(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
        params: dict[str, str],
        **kwargs: Any,
    ) -> Response:
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
                return self._get_event_loop().run_until_complete(self._map_cache(config, layer, tile, kwargs))

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
            return self.response(
                config,
                tile2.data,
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
                **kwargs,
            )
        return self.error(config, 204, **kwargs)

    async def _map_cache(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
        kwargs: dict[str, Any],
    ) -> Response:
        """Get the tile on a cache of tile."""
        assert _TILEGENERATION
        return await internal_mapcache.fetch(config, self, _TILEGENERATION, layer, tile, kwargs)

    def forward(
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

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
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
            return self.response(config, response.content, headers=response_headers, **kwargs)
        message = (
            f"The URL '{url}' return '{response.status_code} {response.reason}', content:\n{response.text}"
        )
        _LOGGER.warning(message)
        return self.error(config, 502, message=message, **kwargs)

    def error(
        self,
        config: tilecloud_chain.DatedConfig,
        code: int,
        message: Exception | str | None = "",
        **kwargs: Any,
    ) -> Response:
        """Build the error, should be implemented in a sub class."""
        raise NotImplementedError

    def response(
        self,
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Build the response, should be implemented in a sub class."""
        raise NotImplementedError

    def get_host(self, **kwargs: Any) -> str:
        """Get the host used in Prometheus stats and in the JSON logs, should be implemented in a sub class."""
        del kwargs
        return "localhost"


if TYPE_CHECKING:
    WsgiServerBase = Server[list[bytes]]
else:
    WsgiServerBase = Server


class WsgiServer(WsgiServerBase):
    """Convert the error and response for the WSGI server."""

    HTTP_MESSAGES: ClassVar[dict[int, str]] = {
        204: "204 No Content",
        400: "400 Bad Request",
        403: "403 Forbidden",
        404: "404 Not Found",
        502: "502 Bad Gateway",
    }

    def error(
        self,
        config: tilecloud_chain.DatedConfig,
        code: int,
        message: Exception | str | None = "",
        **kwargs: Any,
    ) -> list[bytes]:
        """Build the error."""
        del config  # Unused
        assert message is not None
        kwargs["start_response"](self.HTTP_MESSAGES[code], [])
        return [str(message).encode()]

    def response(
        self,
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> list[bytes]:
        """Build the response."""
        del config  # Unused
        if headers is None:
            headers = {}
        headers["Content-Length"] = str(len(data))
        kwargs["start_response"]("200 OK", headers.items())
        return [data]


def app_factory(
    global_config: Any,
    configfile: str | None = os.environ.get("TILEGENERATION_CONFIGFILE"),
    **local_conf: Any,
) -> WsgiServer:
    """Create the WSGI server."""
    del global_config
    del local_conf

    init_tilegeneration(Path(configfile) if configfile is not None else None)

    return WsgiServer()


if TYPE_CHECKING:
    PyramidServerBase = Server[pyramid.response.Response]
else:
    PyramidServerBase = Server


class PyramidServer(PyramidServerBase):
    """Convert the error and response for Pyramid."""

    def error(
        self,
        config: tilecloud_chain.DatedConfig,
        code: int,
        message: Exception | str | None = None,
        **kwargs: Any,
    ) -> pyramid.response.Response:
        """Build the Pyramid response on error."""
        del kwargs  # Unused
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
            return exception_response(code, detail=message, headers=headers)

        raise exception_response(code, detail=message, headers=headers)

    def response(
        self,
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> pyramid.response.Response:
        """Build the Pyramid response."""
        del config
        if headers is None:
            headers = {}
        request: pyramid.request.Request = kwargs["request"]
        request.response.headers = headers
        if isinstance(data, memoryview):
            request.response.body_file = data
        else:
            request.response.body = data
        return request.response

    def get_host(self, **kwargs: Any) -> str:
        """Get the host used in Prometheus stats and in the JSON logs."""
        request: pyramid.request.Request = kwargs["request"]
        assert isinstance(request.host, str)
        return request.host


_PYRAMID_SERVER = None


class PyramidView:
    """The Pyramid view."""

    def __init__(self, request: Request) -> None:
        """Init the Pyramid view."""
        self.request = request

        global _PYRAMID_SERVER  # pylint: disable=global-statement

        init_tilegeneration(Path(request.registry.settings.get("tilegeneration_configfile")))

        if _PYRAMID_SERVER is None:
            _PYRAMID_SERVER = PyramidServer()

        self.server = _PYRAMID_SERVER

    def __call__(self) -> pyramid.response.Response:
        """Call the Pyramid view."""
        params = {}
        path = None

        if "path" in self.request.matchdict:
            path = self.request.matchdict["path"]

        for param, value in self.request.params.items():
            params[param.upper()] = value

        assert _TILEGENERATION
        return self.server.serve(
            path,
            params,
            host=self.request.host,
            config=_TILEGENERATION.get_host_config(self.request.host),
            request=self.request,
        )


def forbidden(request: pyramid.request.Request) -> pyramid.response.Response:
    """Return a 403 Forbidden response."""
    is_auth = c2cwsgiutils.auth.is_auth(request)

    if is_auth:
        return pyramid.httpexceptions.HTTPForbidden(request.exception.message)
    return pyramid.httpexceptions.HTTPFound(
        location=request.route_url(
            "c2c_github_login",
            _query={"came_from": request.current_route_url()},
        ),
    )


class _ResourceCollector(prometheus_client.registry.Collector):
    """Collect the resources used by Python."""

    def collect(self) -> Generator[prometheus_client.core.GaugeMetricFamily, None, None]:
        """Get the gauge from smap file."""
        gauge = prometheus_client.core.GaugeMetricFamily(
            c2cwsgiutils.prometheus.build_metric_name("python_resource"),
            "Python resources",
            labels=["name"],
        )
        r = resource.getrusage(resource.RUSAGE_SELF)
        for field in dir(r):
            if field.startswith("ru_"):
                gauge.add_metric([field[3:]], getattr(r, field))
        yield gauge


class _MemoryInfoCollector(prometheus_client.registry.Collector):
    """Collect the resources used by Python."""

    process = psutil.Process(os.getpid())

    def collect(self) -> Generator[prometheus_client.core.GaugeMetricFamily, None, None]:
        """Get the gauge from smap file."""
        gauge = prometheus_client.core.GaugeMetricFamily(
            c2cwsgiutils.prometheus.build_metric_name("python_memory_info"),
            "Python memory info",
            labels=["name"],
        )
        memory_info = self.process.memory_info()
        gauge.add_metric(["rss"], memory_info.rss)
        gauge.add_metric(["vms"], memory_info.vms)
        gauge.add_metric(["shared"], memory_info.shared)
        gauge.add_metric(["text"], memory_info.text)
        gauge.add_metric(["lib"], memory_info.lib)
        gauge.add_metric(["data"], memory_info.data)
        gauge.add_metric(["dirty"], memory_info.dirty)
        yield gauge


def main(global_config: Any, **settings: Any) -> Router:
    """Start the server in Pyramid."""
    del global_config  # unused

    REGISTRY.register(c2cwsgiutils.prometheus.MemoryMapCollector("pss"))
    if os.environ.get("TILECLOUD_CHAIN_PROMETHEUS_MEMORY_MAP", "false").lower() in ("true", "1", "on"):
        REGISTRY.register(c2cwsgiutils.prometheus.MemoryMapCollector("rss"))
        REGISTRY.register(c2cwsgiutils.prometheus.MemoryMapCollector("size"))
    REGISTRY.register(_ResourceCollector())
    REGISTRY.register(_MemoryInfoCollector())
    prometheus_client.start_http_server(int(os.environ["C2C_PROMETHEUS_PORT"]))

    config = Configurator(settings=settings)

    config.set_session_factory(
        pyramid.session.BaseCookieSessionFactory(json)
        if os.environ.get("TILECLOUD_CHAIN_DEBUG_SESSION", "false").lower() == "true"
        else pyramid.session.SignedCookieSessionFactory(
            os.environ["TILECLOUD_CHAIN_SESSION_SECRET"],
            salt=os.environ["TILECLOUD_CHAIN_SESSION_SALT"],
        ),
    )

    init_tilegeneration(
        Path(settings["tilegeneration_configfile"]) if "tilegeneration_configfile" in settings else None,
    )
    assert _TILEGENERATION

    config.include(c2cwsgiutils.pyramid.includeme)
    health_check.HealthCheck(config)
    add_mako_renderer(config, ".html")
    config.set_security_policy(tilecloud_chain.security.SecurityPolicy())
    config.add_forbidden_view(forbidden)

    config.add_route(
        "admin",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}",
        request_method="GET",
    )
    config.add_route(
        "admin_slash",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/",
        request_method="GET",
    )
    config.add_route(
        "admin_run",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/run",
        request_method="POST",
    )
    config.add_route(
        "admin_create_job",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/create_job",
        request_method="POST",
    )
    config.add_route(
        "admin_cancel_job",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/cancel_job",
        request_method="POST",
    )
    config.add_route(
        "admin_retry_job",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/retry_job",
        request_method="POST",
    )
    config.add_route(
        "admin_test",
        f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/test",
        request_method="GET",
    )

    config.add_static_view(
        name=f"/{_TILEGENERATION.get_main_config().config['server'].get('admin_path', configuration.ADMIN_PATH_DEFAULT)}/static",
        path="/app/tilecloud_chain/static",
    )

    config.add_route("tiles", "/*path", request_method="GET")
    config.add_view(PyramidView, route_name="tiles")

    config.scan("tilecloud_chain.views")

    return config.make_wsgi_app()
