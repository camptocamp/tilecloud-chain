# Copyright (c) 2013 by Stéphane Brunner
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

import collections
import datetime
import logging
import mimetypes
import os
import time
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar, Union, cast
from urllib.parse import parse_qs, urlencode

from azure.core.exceptions import ResourceNotFoundError
import botocore.exceptions
from c2cwsgiutils import health_check
import c2cwsgiutils.pyramid
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPException, exception_response
from pyramid.request import Request
import pyramid.response
from pyramid.router import Router
from pyramid_mako import add_mako_renderer
import requests

from tilecloud import Tile, TileCoord
import tilecloud.store.s3
from tilecloud_chain import TileGeneration, controller, internal_mapcache
import tilecloud_chain.configuration
from tilecloud_chain.controller import get_azure_client

logger = logging.getLogger(__name__)

tilegeneration = None


def init_tilegeneration(config_file: Optional[str]) -> None:
    """Initialize the tile generation."""
    global tilegeneration  # pylint: disable=global-statement
    if tilegeneration is None:
        logger.info("Config file: '%s'", config_file)
        log_level = os.environ.get("TILE_SERVER_LOGLEVEL")
        tilegeneration = TileGeneration(
            config_file,
            collections.namedtuple(  # type: ignore
                "Options",
                ["verbose", "debug", "quiet", "bbox", "zoom", "test", "near", "time", "geom", "ignore_error"],
            )(
                log_level == "verbose",  # type: ignore
                log_level == "debug",
                log_level == "quiet",
                None,
                None,
                None,
                None,
                None,
                True,
                False,
            ),
            configure_logging=False,
            multi_thread=False,
            maxconsecutive_errors=False,
        )


Response = TypeVar("Response")


class DatedStore:
    """Store with timestamp to be able to invalidate it on configuration change."""

    def __init__(self, store: tilecloud.TileStore, mtime: float) -> None:
        """Initialise."""
        self.store = store
        self.mtime = mtime


class DatedFilter:
    """Filter with timestamp to be able to invalidate it on configuration change."""

    def __init__(self, layer_filter: Optional[tilecloud_chain.IntersectGeometryFilter], mtime: float) -> None:
        """Initialise."""
        self.filter = layer_filter
        self.mtime = mtime


class Server(Generic[Response]):
    """The generic implementation of the WMTS server."""

    def __init__(self) -> None:
        """Initialise."""
        try:
            self.filter_cache: Dict[str, Dict[str, DatedFilter]] = {}
            self.s3_client_cache: Dict[str, "botocore.client.S3"] = {}
            self.store_cache: Dict[str, Dict[str, DatedStore]] = {}

            assert tilegeneration

            self.wmts_path = tilegeneration.get_main_config().config["server"]["wmts_path"]
            self.static_path = tilegeneration.get_main_config().config["server"]["static_path"].split("/")
        except Exception:
            logger.exception("Initialization error")
            raise

    @staticmethod
    def get_expires_hours(config: tilecloud_chain.DatedConfig) -> float:
        """Get the expiration time in hours."""
        return config.config["server"]["expires"]

    @staticmethod
    def get_static_allow_extension(config: tilecloud_chain.DatedConfig) -> List[str]:
        """Get the allowed extensions in the static view."""
        return config.config["server"].get(
            "static_allow_extension", ["jpeg", "png", "xml", "js", "html", "css"]
        )

    @staticmethod
    def get_cache_name(config: tilecloud_chain.DatedConfig) -> str:
        """Get the cache name."""
        return config.config["server"].get("cache", config.config["generation"]["default_cache"])

    def get_s3_client(self, config: tilecloud_chain.DatedConfig) -> "botocore.client.S3":
        """Get the AWS S3 client."""
        cache_s3 = cast(tilecloud_chain.configuration.CacheS3, self.get_cache(config))
        if cache_s3.get("host", "aws") in self.s3_client_cache:
            return self.s3_client_cache[cache_s3.get("host", "aws")]
        for n in range(10):
            try:
                client = tilecloud.store.s3.get_client(cache_s3.get("host"))
                self.s3_client_cache[cast(str, cache_s3.get("host", "aws"))] = client
                return client
            except KeyError as e:
                error = e
            time.sleep(n * 10)
        raise error

    def get_cache(self, config: tilecloud_chain.DatedConfig) -> tilecloud_chain.configuration.Cache:
        """Get the cache from the config."""
        return config.config["caches"][self.get_cache_name(config)]

    @staticmethod
    def get_layers(config: tilecloud_chain.DatedConfig) -> List[str]:
        """Get the layer from the config."""
        layers: List[str] = cast(List[str], config.config["layers"].keys())
        return config.config["server"].get("layers", layers)

    def get_filter(
        self, config: tilecloud_chain.DatedConfig, layer_name: str
    ) -> Optional[tilecloud_chain.IntersectGeometryFilter]:
        """Get the filter from the config."""
        dated_filter = self.filter_cache.get(config.file, {}).get(layer_name)

        if dated_filter is not None and dated_filter.mtime == config.mtime:
            return dated_filter.filter

        assert tilegeneration

        layer_filter = (
            tilecloud_chain.IntersectGeometryFilter(gene=tilegeneration)
            if config.config["server"]["geoms_redirect"]
            else None
        )

        self.filter_cache.setdefault(config.file, {})[layer_name] = DatedFilter(layer_filter, config.mtime)
        return layer_filter

    def get_store(self, config: tilecloud_chain.DatedConfig, layer_name: str) -> tilecloud.TileStore:
        """Get the store from the config."""
        dated_store = self.store_cache.get(config.file, {}).get(layer_name)

        if dated_store is not None and dated_store.mtime == config.mtime:
            return dated_store.store

        assert tilegeneration

        store = tilegeneration.get_store(config, self.get_cache(config), layer_name, read_only=True)
        self.store_cache.setdefault(config.file, {})[layer_name] = DatedStore(store, config.mtime)
        return store

    @staticmethod
    def get_max_zoom_seed(config: tilecloud_chain.DatedConfig, layer_name: str) -> int:
        """Get the max zoom to be bet in the stored cache."""
        layer = config.config["layers"][layer_name]
        if "min_resolution_seed" in layer:
            max_zoom_seed = -1
            for zoom, resolution in enumerate(config.config["grids"][layer["grid"]]["resolutions"]):
                if resolution > layer["min_resolution_seed"]:
                    max_zoom_seed = zoom
            return max_zoom_seed
        else:
            return 999999

    def _read(
        self,
        key_name: str,
        headers: Dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> Response:
        cache = self.get_cache(config)
        try:
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
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
            else:
                raise

    def _get(
        self,
        path: str,
        headers: Dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> Response:
        """Get capabilities or other static files."""
        assert tilegeneration
        cache = self.get_cache(config)

        if cache["type"] == "s3":
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, cache)
            key_name = os.path.join(cache_s3["folder"], path)
            try:
                return self._read(key_name, headers, config, **kwargs)
            except Exception:
                del self.s3_client_cache[cache_s3.get("host", "aws")]
                return self._read(key_name, headers, config, **kwargs)
        if cache["type"] == "azure":
            cache_azure = cast(tilecloud_chain.configuration.CacheAzure, cache)
            key_name = os.path.join(cache_azure["folder"], path)
            try:
                blob = get_azure_client().get_blob_client(container=cache_azure["container"], blob=key_name)
                properties = blob.get_blob_properties()
                return self.response(
                    config,
                    blob.download_blob().readall(),
                    {
                        "Content-Encoding": cast(str, properties.content_settings.content_encoding),
                        "Content-Type": cast(str, properties.content_settings.content_type),
                    },
                    **kwargs,
                )
            except ResourceNotFoundError:
                return self.error(config, 404, path + " not found", **kwargs)
        else:
            cache_filesystem = cast(tilecloud_chain.configuration.CacheFilesystem, cache)
            folder = cache_filesystem["folder"] or ""
            if path.split(".")[-1] not in self.get_static_allow_extension(config):
                return self.error(config, 403, "Extension not allowed", **kwargs)
            p = os.path.join(folder, path)
            if not os.path.isfile(p):
                return self.error(config, 404, path + " not found", **kwargs)
            with open(p, "rb") as file:
                data = file.read()
            content_type = mimetypes.guess_type(p)[0]
            if content_type:
                headers["Content-Type"] = content_type
            return self.response(config, data, headers, **kwargs)

    def __call__(
        self,
        config: tilecloud_chain.DatedConfig,
        config_file: str,
        environ: Dict[str, str],
        start_response: bytes,
    ) -> Response:
        """Build the response on request."""
        params = {}
        for key, value in parse_qs(environ["QUERY_STRING"], True).items():
            params[key.upper()] = value[0]

        path = None if len(params) > 0 else environ["PATH_INFO"][1:].split("/")

        return self.serve(path, params, config=config, config_file=config_file, start_response=start_response)

    def serve(
        self,
        path: Optional[List[str]],
        params: Dict[str, str],
        config: tilecloud_chain.DatedConfig,
        **kwargs: Any,
    ) -> Response:
        """Serve the WMTS requests."""
        try:
            dimensions = []
            metadata = {}
            assert tilegeneration

            if path:
                if tuple(path[: len(self.static_path)]) == tuple(self.static_path):
                    return self._get(
                        "/".join(path[len(self.static_path) :]),
                        {
                            "Expires": (
                                datetime.datetime.utcnow()
                                + datetime.timedelta(hours=self.get_expires_hours(config))
                            ).isoformat(),
                            "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET",
                        },
                        config=config,
                        **kwargs,
                    )
                elif len(path) >= 1 and path[0] != self.wmts_path:
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
                            tilecloud_chain.configuration.LayerWms,
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
            else:
                if "SERVICE" not in params or "REQUEST" not in params or "VERSION" not in params:
                    return self.error(config, 400, "Not all required parameters are present", **kwargs)

            if params["SERVICE"] != "WMTS":
                return self.error(config, 400, f"Wrong Service '{params['SERVICE']}'", **kwargs)
            if params["VERSION"] != "1.0.0":
                return self.error(config, 400, f"Wrong Version '{params['VERSION']}'", **kwargs)

            if params["REQUEST"] == "GetCapabilities":
                headers = {
                    "Content-Type": "application/xml",
                    "Expires": (
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                }
                cache = self.get_cache(config)
                if "wmtscapabilities_file" in cache:
                    wmtscapabilities_file = cache["wmtscapabilities_file"]
                    return self._get(wmtscapabilities_file, headers, config=config, **kwargs)
                else:
                    body = controller.get_wmts_capabilities(
                        tilegeneration, self.get_cache_name(config), config=config
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
                        tilecloud_chain.configuration.LayerWms,
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
            if params["TILEMATRIXSET"] != layer["grid"]:
                return self.error(config, 400, f"Wrong TileMatrixSet '{params['TILEMATRIXSET']}'", **kwargs)

            metadata["layer"] = params["LAYER"]
            metadata["config_file"] = config.file
            tile = Tile(
                TileCoord(
                    # TODO fix for matrix_identifier = resolution
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
                                "LAYERS": layer["layers"],
                                "QUERY_LAYERS": layer["query_layers"],
                                "STYLES": params["STYLE"],
                                "FORMAT": params["FORMAT"],
                                "INFO_FORMAT": params["INFO_FORMAT"],
                                "WIDTH": config.config["grids"][layer["grid"]]["tile_size"],
                                "HEIGHT": config.config["grids"][layer["grid"]]["tile_size"],
                                "SRS": config.config["grids"][layer["grid"]]["srs"],
                                "BBOX": tilegeneration.get_grid(config, layer["grid"]).extent(tile.tilecoord),
                                "X": params["I"],
                                "Y": params["J"],
                            }
                        ),
                        no_cache=True,
                        **kwargs,
                    )
                else:
                    return self.error(config, 400, f"Layer '{params['LAYER']}' not queryable", **kwargs)

            if params["REQUEST"] != "GetTile":
                return self.error(config, 400, f"Wrong Request '{params['REQUEST']}'", **kwargs)

            if params["FORMAT"] != layer["mime_type"]:
                return self.error(config, 400, f"Wrong Format '{params['FORMAT']}'", **kwargs)

            if tile.tilecoord.z > self.get_max_zoom_seed(config, params["LAYER"]):
                return self._map_cache(config, layer, tile, kwargs)

            layer_filter = self.get_filter(config, params["LAYER"])
            if layer_filter:
                meta_size = layer["meta_size"]
                meta_tilecoord = (
                    TileCoord(
                        # TODO fix for matrix_identifier = resolution
                        tile.tilecoord.z,
                        round(tile.tilecoord.x / meta_size * meta_size),
                        round(tile.tilecoord.y / meta_size * meta_size),
                        meta_size,
                    )
                    if meta_size != 1
                    else tile.tilecoord
                )
                if not layer_filter.filter_tilecoord(config, meta_tilecoord, params["LAYER"]):
                    return self._map_cache(config, layer, tile, kwargs)

            store = self.get_store(config, params["LAYER"])
            if store is None:
                return self.error(
                    config,
                    400,
                    f"No store found for layer '{params['LAYER']}'",
                    **kwargs,
                )

            tile2 = store.get_one(tile)
            if tile2:
                if tile2.error:
                    return self.error(config, 500, tile2.error, **kwargs)

                assert tile2.data
                assert tile2.content_type
                return self.response(
                    config,
                    tile2.data,
                    headers={
                        "Content-Type": tile2.content_type,
                        "Expires": (
                            datetime.datetime.utcnow()
                            + datetime.timedelta(hours=self.get_expires_hours(config))
                        ).isoformat(),
                        "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET",
                        "Tile-Backend": "Cache",
                    },
                    **kwargs,
                )
            else:
                return self.error(config, 204, **kwargs)
        except HTTPException:
            raise
        except Exception:
            logger.exception("An unknown error occurred")
            raise

    def _map_cache(
        self,
        config: tilecloud_chain.DatedConfig,
        layer: tilecloud_chain.configuration.Layer,
        tile: Tile,
        kwargs: Dict[str, Any],
    ) -> Response:
        """Get the tile on a cache of tile."""
        assert tilegeneration
        return internal_mapcache.fetch(config, self, tilegeneration, layer, tile, kwargs)

    def forward(
        self,
        config: tilecloud_chain.DatedConfig,
        url: str,
        headers: Optional[Any] = None,
        no_cache: bool = False,
        **kwargs: Any,
    ) -> Response:
        """Forward the seqest on a fallback WMS server."""
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
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.get_expires_hours(config))
                ).isoformat()
                response_headers["Cache-Control"] = f"max-age={3600 * self.get_expires_hours(config)}"
                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Allow-Methods"] = "GET"
            return self.response(config, response.content, headers=response_headers, **kwargs)
        else:
            message = (
                f"The URL '{url}' return '{response.status_code} {response.reason}', "
                f"content:\n{response.text}"
            )
            logger.warning(message)
            return self.error(config, 502, message=message, **kwargs)

    def error(
        self,
        config: tilecloud_chain.DatedConfig,
        code: int,
        message: Optional[Union[Exception, str]] = "",
        **kwargs: Any,
    ) -> Response:
        """Build the error, should be implemented in a sub class."""
        raise NotImplementedError

    def response(
        self,
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Build the response, should be implemented in a sub class."""
        raise NotImplementedError


if TYPE_CHECKING:
    WsgiServerBase = Server[List[bytes]]
else:
    WsgiServerBase = Server


class WsgiServer(WsgiServerBase):
    """Convert the error and response for the WSGI server."""

    HTTP_MESSAGES = {
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
        message: Optional[Union[Exception, str]] = "",
        **kwargs: Any,
    ) -> List[bytes]:
        """Build the error."""
        assert message is not None
        kwargs["start_response"](self.HTTP_MESSAGES[code], [])
        return [str(message).encode()]

    @staticmethod
    def response(
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[bytes]:
        """Build the response."""
        if headers is None:
            headers = {}
        headers["Content-Length"] = str(len(data))
        kwargs["start_response"]("200 OK", headers.items())
        return [data]


def app_factory(
    global_config: Any,
    configfile: Optional[str] = os.environ.get("TILEGENERATION_CONFIGFILE"),
    **local_conf: Any,
) -> WsgiServer:
    """Create the WSGI server."""
    del global_config
    del local_conf

    init_tilegeneration(configfile)

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
        message: Optional[Union[Exception, str]] = None,
        **kwargs: Any,
    ) -> pyramid.response.Response:
        """Build the Pyramid response on error."""
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
        }
        if code < 300:
            headers.update(
                {
                    "Expires": (
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.get_expires_hours(config))
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.get_expires_hours(config)}",
                }
            )
            return exception_response(code, detail=message, headers=headers)

        raise exception_response(code, detail=message, headers=headers)

    def response(
        self,
        config: tilecloud_chain.DatedConfig,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> pyramid.response.Response:
        """Build the Pyramid response."""
        if headers is None:
            headers = {}
        request: pyramid.request.Request = kwargs["request"]
        request.response.headers = headers
        if isinstance(data, memoryview):
            request.response.body_file = data
        else:
            request.response.body = data
        return request.response


pyramid_server = None


class PyramidView:
    """The Pyramid view."""

    def __init__(self, request: Request) -> None:
        """Init the Pyramid view."""
        self.request = request

        global pyramid_server  # pylint: disable=global-statement

        init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))

        if pyramid_server is None:
            pyramid_server = PyramidServer()

        self.server = pyramid_server

    def __call__(self) -> pyramid.response.Response:
        """Call the Pyramid view."""
        params = {}
        path = None

        if "path" in self.request.matchdict:
            path = self.request.matchdict["path"]

        for param, value in self.request.params.items():
            params[param.upper()] = value

        assert tilegeneration
        return self.server.serve(
            path,
            params,
            host=self.request.host,
            config=tilegeneration.get_host_config(self.request.host),
            request=self.request,
        )


def main(global_config: Any, **settings: Any) -> Router:
    """Start the server in Pyramid."""
    del global_config  # unused

    config = Configurator(settings=settings)

    init_tilegeneration(settings.get("tilegeneration_configfile"))
    assert tilegeneration

    config.include(c2cwsgiutils.pyramid.includeme)
    health_check.HealthCheck(config)

    add_mako_renderer(config, ".html")

    config.add_route(
        "admin",
        f"/{tilegeneration.get_main_config().config['server']['admin_path']}/",
        request_method="GET",
    )
    config.add_route(
        "admin_run",
        f"/{tilegeneration.get_main_config().config['server']['admin_path']}/run",
        request_method="POST",
    )
    config.add_route(
        "admin_test",
        f"/{tilegeneration.get_main_config().config['server']['admin_path']}/test",
        request_method="GET",
    )

    config.add_route("tiles", "/*path", request_method="GET")
    config.add_view(PyramidView, route_name="tiles")

    config.scan("tilecloud_chain.views")

    return config.make_wsgi_app()
