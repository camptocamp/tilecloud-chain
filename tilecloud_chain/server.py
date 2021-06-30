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

import botocore.exceptions
from c2cwsgiutils import health_check
import c2cwsgiutils.pyramid
from pyramid.config import Configurator
from pyramid.httpexceptions import exception_response
import pyramid.response
from pyramid.router import Router
from pyramid.testing import DummyRequest
from pyramid_mako import add_mako_renderer
import requests
from typing_extensions import TypedDict

from tilecloud import Tile, TileCoord
import tilecloud.store.s3
from tilecloud_chain import TileGeneration, controller, internal_mapcache
import tilecloud_chain.configuration

logger = logging.getLogger(__name__)

tilegeneration = None


class StoreDefinition(TypedDict):
    ref: List[str]
    dimensions: Dict[str, str]


def init_tilegeneration(config_file: str) -> None:
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


class Server(Generic[Response]):
    def __init__(self) -> None:
        try:
            self.filters = {}
            self.max_zoom_seed = {}

            global tilegeneration  # pylint: disable=global-statement
            assert tilegeneration

            self.expires_hours = tilegeneration.config["server"]["expires"]
            self.static_allow_extension = tilegeneration.config["server"].get(
                "static_allow_extension", ["jpeg", "png", "xml", "js", "html", "css"]
            )

            self.cache_name = tilegeneration.config["server"].get(
                "cache", tilegeneration.config["generation"]["default_cache"]
            )
            self.cache = tilegeneration.caches[self.cache_name]

            if self.cache["type"] == "s3":
                cache_s3 = cast(tilecloud_chain.configuration.CacheS3, self.cache)
                error = None
                success = False
                for n in range(10):
                    time.sleep(n * 10)
                    try:
                        self.s3_client = tilecloud.store.s3.get_client(cache_s3.get("host"))
                        success = True
                        break
                    except KeyError as e:
                        error = e
                if not success and error:
                    raise error

            if tilegeneration.config["server"]["mapcache_internal"]:
                self.mapcache_baseurl = None
                self.mapcache_header = {}
            else:
                mapcache_base = tilegeneration.config["server"]["mapcache_base"].rstrip("/")
                mapcache_location = tilegeneration.config["mapcache"]["location"].strip("/")
                if mapcache_location == "":
                    self.mapcache_baseurl = mapcache_base + "/wmts"
                else:
                    self.mapcache_baseurl = f"{mapcache_base}/{mapcache_location}/wmts"
                self.mapcache_header = tilegeneration.config["server"].get("mapcache_headers", {})

            geoms_redirect = tilegeneration.config["server"]["geoms_redirect"]

            self.layers = tilegeneration.config["server"].get("layers", tilegeneration.layers.keys())
            self.stores: Dict[str, tilecloud.TileStore] = {}
            for layer_name in tilegeneration.layers.keys():
                layer = tilegeneration.layers[layer_name]

                # Build geoms redirect
                if geoms_redirect:
                    self.filters[layer_name] = tilegeneration.get_geoms_filter(
                        layer=layer,
                        grid_name=layer["grid"],
                        geoms={
                            layer_name: tilegeneration.get_geoms(
                                layer_name,
                                extent=layer["bbox"]
                                if "bbox" in layer
                                else tilegeneration.config["grids"][layer["grid"]]["bbox"],
                            )
                        },
                    )
                mapcache_location = tilegeneration.config["mapcache"].get("location", "/mapcache").strip("/")
                if mapcache_location == "":
                    self.mapcache_baseurl = mapcache_base + "/wmts"
                else:
                    self.mapcache_baseurl = f"{mapcache_base}/{mapcache_location}/wmts"
                self.mapcache_header = tilegeneration.config["server"].get("mapcache_headers", {})

                if "min_resolution_seed" in layer:
                    max_zoom_seed = -1
                    for zoom, resolution in enumerate(
                        tilegeneration.config["grids"][layer["grid"]]["resolutions"]
                    ):
                        if resolution > layer["min_resolution_seed"]:
                            max_zoom_seed = zoom
                    self.max_zoom_seed[layer_name] = max_zoom_seed
                else:
                    self.max_zoom_seed[layer_name] = 999999

                # Build stores
                store_defs: List[StoreDefinition] = [{"ref": [layer_name], "dimensions": {}}]
                for dimension in layer["dimensions"]:
                    new_store_defs: List[StoreDefinition] = []
                    for store_def in store_defs:
                        for value in dimension["values"]:
                            dimensions: Dict[str, str] = {}
                            dimensions.update(store_def["dimensions"])
                            dimensions[dimension["name"]] = value
                            new_store_defs.append(
                                {"ref": store_def["ref"] + [value], "dimensions": dimensions}
                            )
                    store_defs = new_store_defs
                for store_def in store_defs:
                    self.stores["/".join(store_def["ref"])] = tilegeneration.get_store(
                        self.cache, layer_name, read_only=True
                    )

            self.wmts_path = tilegeneration.config["server"]["wmts_path"]
            self.static_path = tilegeneration.config["server"]["static_path"].split("/")
        except Exception:
            logger.exception("Initialization error")
            raise

    def _read(self, key_name: str, headers: Dict[str, str], **kwargs: Any) -> Response:
        try:
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, self.cache)
            bucket = cache_s3
            response = self.s3_client.get_object(Bucket=bucket, Key=key_name)
            body = response["Body"]
            try:
                headers["Content-Type"] = response.get("ContentType")
                return self.response(body.read(), headers, **kwargs)
            finally:
                body.close()
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return self.error(404, key_name + " not found")
            else:
                raise

    def _get(self, path: str, headers: Dict[str, str], **kwargs: Any) -> Response:
        """
        Get capabilities or other static files
        """
        if self.cache["type"] == "s3":
            cache_s3 = cast(tilecloud_chain.configuration.CacheS3, self.cache)
            key_name = os.path.join(cache_s3["folder"], path)
            try:
                return self._read(key_name, headers, **kwargs)
            except Exception:
                self.s3_client = tilecloud.store.s3.get_client(cache_s3.get("host"))
                return self._read(key_name, headers, **kwargs)
        else:
            cache_filesystem = cast(tilecloud_chain.configuration.CacheFilesystem, self.cache)
            folder = cache_filesystem["folder"] or ""
            if path.split(".")[-1] not in self.static_allow_extension:
                return self.error(403, "Extension not allowed", **kwargs)
            p = os.path.join(folder, path)
            if not os.path.isfile(p):
                return self.error(404, path + " not found", **kwargs)
            with open(p, "rb") as file:
                data = file.read()
            content_type = mimetypes.guess_type(p)[0]
            if content_type:
                headers["Content-Type"] = content_type
            return self.response(data, headers, **kwargs)

    def __call__(self, environ: Dict[str, str], start_response: bytes) -> Response:
        params = {}
        for key, value in parse_qs(environ["QUERY_STRING"], True).items():
            params[key.upper()] = value[0]

        path = None if len(params) > 0 else environ["PATH_INFO"][1:].split("/")

        return self.serve(path, params, start_response=start_response)

    def serve(self, path: Optional[List[str]], params: Dict[str, str], **kwargs: Any) -> Response:
        dimensions = []
        metadata = {}
        assert tilegeneration

        if path:
            if tuple(path[: len(self.static_path)]) == tuple(self.static_path):
                return self._get(  # pylint: disable=not-callable
                    "/".join(path[len(self.static_path) :]),
                    {
                        "Expires": (
                            datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                        ).isoformat(),
                        "Cache-Control": f"max-age={3600 * self.expires_hours}",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET",
                    },
                    **kwargs,
                )
            elif len(path) >= 1 and path[0] != self.wmts_path:
                return self.error(
                    404,
                    "Type '{}' don't exists, allows values: '{}' or '{}'".format(
                        path[0], self.wmts_path, "/".join(self.static_path)
                    ),
                    **kwargs,
                )
            path = path[1:]  # remove type

        if path:
            if len(path) == 2 and path[0] == "1.0.0" and path[1].lower() == "wmtscapabilities.xml":
                params["SERVICE"] = "WMTS"
                params["VERSION"] = "1.0.0"
                params["REQUEST"] = "GetCapabilities"
            elif len(path) < 7:
                return self.error(400, "Not enough path", **kwargs)
            else:
                params["SERVICE"] = "WMTS"
                params["VERSION"] = path[0]

                params["LAYER"] = path[1]
                params["STYLE"] = path[2]

                if params["LAYER"] in self.layers:
                    layer = cast(
                        tilecloud_chain.configuration.LayerWms, tilegeneration.layers[params["LAYER"]]
                    )
                else:
                    return self.error(400, "Wrong Layer '{}'".format(params["LAYER"]), **kwargs)

                index = 3
                dimensions = path[index : index + len(layer["dimensions"])]
                for dimension in layer["dimensions"]:
                    metadata["dimension_" + dimension["name"]] = path[index]
                    params[dimension["name"].upper()] = path[index]
                    index += 1

                last = path[-1].split(".")
                if len(path) < index + 4:
                    return self.error(400, "Not enough path", **kwargs)
                params["TILEMATRIXSET"] = path[index]
                params["TILEMATRIX"] = path[index + 1]
                params["TILEROW"] = path[index + 2]
                if len(path) == index + 4:
                    params["REQUEST"] = "GetTile"
                    params["TILECOL"] = last[0]
                    if last[1] != layer["extension"]:
                        return self.error(400, f"Wrong extension '{last[1]}'", **kwargs)
                elif len(path) == index + 6:
                    params["REQUEST"] = "GetFeatureInfo"
                    params["TILECOL"] = path[index + 3]
                    params["I"] = path[index + 4]
                    params["J"] = last[0]
                    params["INFO_FORMAT"] = layer.get("info_formats", ["application/vnd.ogc.gml"])[0]
                else:
                    return self.error(400, "Wrong path length", **kwargs)

                params["FORMAT"] = layer["mime_type"]
        else:
            if "SERVICE" not in params or "REQUEST" not in params or "VERSION" not in params:
                return self.error(400, "Not all required parameters are present", **kwargs)

        if params["SERVICE"] != "WMTS":
            return self.error(400, "Wrong Service '{}'".format(params["SERVICE"]), **kwargs)
        if params["VERSION"] != "1.0.0":
            return self.error(400, "Wrong Version '{}'".format(params["VERSION"]), **kwargs)

        if params["REQUEST"] == "GetCapabilities":
            headers = {
                "Content-Type": "application/xml",
                "Expires": (
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                ).isoformat(),
                "Cache-Control": f"max-age={3600 * self.expires_hours}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
            }
            if "wmtscapabilities_file" in self.cache:
                wmtscapabilities_file = self.cache["wmtscapabilities_file"]
                return self._get(wmtscapabilities_file, headers, **kwargs)  # pylint: disable=not-callable
            else:
                body = controller.get_wmts_capabilities(tilegeneration, self.cache_name)
                assert body
                headers["Content-Type"] = "application/xml"
                return self.response(body.encode("utf-8"), headers=headers, **kwargs)

        if (
            "FORMAT" not in params
            or "LAYER" not in params
            or "TILEMATRIXSET" not in params
            or "TILEMATRIX" not in params
            or "TILEROW" not in params
            or "TILECOL" not in params
        ):
            return self.error(400, "Not all required parameters are present", **kwargs)

        if not path:
            if params["LAYER"] in self.layers:
                layer = cast(tilecloud_chain.configuration.LayerWms, tilegeneration.layers[params["LAYER"]])
            else:
                return self.error(400, "Wrong Layer '{}'".format(params["LAYER"]), **kwargs)

            for dimension in layer["dimensions"]:
                value = (
                    params[dimension["name"].upper()]
                    if dimension["name"].upper() in params
                    else dimension["default"]
                )
                dimensions.append(value)
                metadata["dimension_" + dimension["name"]] = value

        if params["STYLE"] != layer["wmts_style"]:
            return self.error(400, "Wrong Style '{}'".format(params["STYLE"]), **kwargs)
        if params["TILEMATRIXSET"] != layer["grid"]:
            return self.error(400, "Wrong TileMatrixSet '{}'".format(params["TILEMATRIXSET"]), **kwargs)

        metadata["layer"] = params["LAYER"]
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
                return self.error(400, "Not all required parameters are present", **kwargs)
            if "query_layers" in layer:
                return self.forward(
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
                            "WIDTH": tilegeneration.config["grids"][layer["grid"]]["tile_size"],
                            "HEIGHT": tilegeneration.config["grids"][layer["grid"]]["tile_size"],
                            "SRS": tilegeneration.config["grids"][layer["grid"]]["srs"],
                            "BBOX": tilegeneration.grid_obj[layer["grid"]].extent(tile.tilecoord),
                            "X": params["I"],
                            "Y": params["J"],
                        }
                    ),
                    no_cache=True,
                    **kwargs,
                )
            else:
                return self.error(400, "Layer '{}' not queryable".format(params["LAYER"]), **kwargs)

        if params["REQUEST"] != "GetTile":
            return self.error(400, "Wrong Request '{}'".format(params["REQUEST"]), **kwargs)

        if params["FORMAT"] != layer["mime_type"]:
            return self.error(400, "Wrong Format '{}'".format(params["FORMAT"]), **kwargs)

        if tile.tilecoord.z > self.max_zoom_seed[params["LAYER"]]:
            return self._map_cache(layer, tile, params, kwargs)

        if params["LAYER"] in self.filters:
            layer_filter = self.filters[params["LAYER"]]
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
            if not layer_filter.filter_tilecoord(meta_tilecoord, params["LAYER"]):
                return self._map_cache(layer, tile, params, kwargs)

        store_ref = "/".join([params["LAYER"]] + list(dimensions))
        if store_ref in self.stores:
            store = self.stores[store_ref]
        else:
            return self.error(
                400,
                "No store found for layer '{}' and dimensions {}".format(
                    params["LAYER"], ", ".join(dimensions)
                ),
                **kwargs,
            )

        tile2 = store.get_one(tile)
        if tile2:
            if tile2.error:
                return self.error(500, tile2.error, **kwargs)

            assert tile2.data
            assert tile2.content_type
            return self.response(
                tile2.data,
                headers={
                    "Content-Type": tile2.content_type,
                    "Expires": (
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.expires_hours}",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Tile-Backend": "Cache",
                },
                **kwargs,
            )
        else:
            return self.error(204, **kwargs)

    def _map_cache(
        self,
        layer: tilecloud_chain.configuration.Layer,
        tile: Optional[Tile],
        params: Dict[str, str],
        kwargs: Dict[str, Any],
    ) -> Response:
        if self.mapcache_baseurl is not None:
            return self.forward(
                self.mapcache_baseurl + "?" + urlencode(params), headers=self.mapcache_header, **kwargs
            )
        else:
            global tilegeneration  # pylint: disable=global-statement
            assert tilegeneration
            assert tile

            return internal_mapcache.fetch(self, tilegeneration, layer, tile, kwargs)

    def forward(
        self, url: str, headers: Optional[Any] = None, no_cache: bool = False, **kwargs: Any
    ) -> Response:
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
                    datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                ).isoformat()
                response_headers["Cache-Control"] = f"max-age={3600 * self.expires_hours}"
                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Allow-Methods"] = "GET"
            return self.response(response.content, headers=response_headers, **kwargs)
        else:
            message = "The URL '{}' return '{} {}', content:\n{}".format(
                url, response.status_code, response.reason, response.text
            )
            logger.warning(message)
            return self.error(502, message=message, **kwargs)

    def error(self, code: int, message: Optional[Union[Exception, str]] = "", **kwargs: Any) -> Response:
        raise NotImplementedError

    def response(self, data: bytes, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> Response:
        raise NotImplementedError


if TYPE_CHECKING:
    WsgiServerBase = Server[List[bytes]]
else:
    WsgiServerBase = Server


class WsgiServer(WsgiServerBase):
    HTTP_MESSAGES = {
        204: "204 No Content",
        400: "400 Bad Request",
        403: "403 Forbidden",
        404: "404 Not Found",
        502: "502 Bad Gateway",
    }

    def error(self, code: int, message: Optional[Union[Exception, str]] = "", **kwargs: Any) -> List[bytes]:
        assert message is not None
        kwargs["start_response"](self.HTTP_MESSAGES[code], [])
        return [str(message).encode()]

    @staticmethod
    def response(data: bytes, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> List[bytes]:
        if headers is None:
            headers = {}
        headers["Content-Length"] = str(len(data))
        kwargs["start_response"]("200 OK", headers.items())
        return [data]


def app_factory(
    global_config: Any,
    configfile: str = os.environ.get("TILEGENERATION_CONFIGFILE", "tilegeneration/config.yaml"),
    **local_conf: Any,
) -> WsgiServer:
    del global_config
    del local_conf

    init_tilegeneration(configfile)

    return WsgiServer()


if TYPE_CHECKING:
    PyramidServerBase = Server[pyramid.response.Response]
else:
    PyramidServerBase = Server


class PyramidServer(PyramidServerBase):
    def error(
        self, code: int, message: Optional[Union[Exception, str]] = None, **kwargs: Any
    ) -> pyramid.response.Response:
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
        }
        if code == 204:
            headers.update(
                {
                    "Expires": (
                        datetime.datetime.utcnow() + datetime.timedelta(hours=self.expires_hours)
                    ).isoformat(),
                    "Cache-Control": f"max-age={3600 * self.expires_hours}",
                }
            )
            return exception_response(code, detail=message, headers=headers)

        raise exception_response(code, detail=message, headers=headers)

    def response(
        self, data: bytes, headers: Optional[Dict[str, str]] = None, **kwargs: Any
    ) -> pyramid.response.Response:
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
    def __init__(self, request: DummyRequest) -> None:
        self.request = request

        global pyramid_server  # pylint: disable=global-statement

        init_tilegeneration(request.registry.settings["tilegeneration_configfile"])

        if pyramid_server is None:
            pyramid_server = PyramidServer()

        self.server = pyramid_server

    def __call__(self) -> pyramid.response.Response:
        params = {}
        path = None

        if "path" in self.request.matchdict:
            path = self.request.matchdict["path"]

        for param, value in self.request.params.items():
            params[param.upper()] = value

        return self.server.serve(path, params, request=self.request)


def main(global_config: Any, **settings: Any) -> Router:
    del global_config  # unused

    config = Configurator(settings=settings)

    init_tilegeneration(settings["tilegeneration_configfile"])
    global tilegeneration  # pylint: disable=global-statement
    assert tilegeneration

    config.include(c2cwsgiutils.pyramid.includeme)
    health_check.HealthCheck(config)

    add_mako_renderer(config, ".html")

    config.add_route(
        "admin",
        "/{}/".format(tilegeneration.config["server"]["admin_path"]),
        request_method="GET",
    )
    config.add_route(
        "admin_run",
        "/{}/run".format(tilegeneration.config["server"]["admin_path"]),
        request_method="POST",
    )

    config.add_route("tiles", "/*path", request_method="GET")
    config.add_view(PyramidView, route_name="tiles")

    config.scan("tilecloud_chain.views")

    return config.make_wsgi_app()
