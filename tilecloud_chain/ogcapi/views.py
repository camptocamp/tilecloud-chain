# Copyright (c) 2023 by Camptocamp
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
import logging
import math
import re
from typing import Any, Dict, List, Tuple, Union, cast
from urllib.parse import urljoin

import pyproj
import pyramid.httpexceptions
import pyramid.request
import pyramid.response
import pyramid.session
from pyramid.view import view_config

import tilecloud_chain.configuration
from tilecloud import Tile, TileCoord
from tilecloud_chain import get_expires_hours, internal_mapcache
from tilecloud_chain.server import PyramidServer, get_max_zoom_seed, init_tilegeneration

_LOG = logging.getLogger(__name__)

_JSON = Union[int, float, str, None, List["_JSON"], Dict[str, "_JSON"]]
_JSONDict = Dict[str, _JSON]


def _copy(base: _JSONDict, sources: List[Tuple[Any, str, str]]) -> _JSONDict:
    for source_, source_key, dest_key in sources:
        source = cast(_JSONDict, source_)
        if source_key in source:
            base[dest_key] = source[source_key]
    return base


@view_config(route_name="landing_page_html", renderer="tilecloud_chain:templates/openlayers.html")  # type: ignore
def landing_page_html(request: pyramid.request.Request) -> _JSON:
    """Get the landing page."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host)
    main_config = tilegeneration.get_main_config()

    return {
        "proj4js_def": re.sub(
            r"\s+",
            " ",
            config.config["openlayers"]["proj4js_def"],
        ),
        "srs": config.config["openlayers"]["srs"],
        "center_x": config.config["openlayers"]["center_x"],
        "center_y": config.config["openlayers"]["center_y"],
        "zoom": config.config["openlayers"]["zoom"],
        "http_url": urljoin(
            request.current_route_url(),
            "/" + main_config.config["server"].get("wmts_path", "wmts") + "/"
            if "server" in config.config
            else "/",
        ),
    }


@view_config(route_name="landing_page_json", renderer="fast_json")  # type: ignore
def landing_page_json(request: pyramid.request.Request) -> _JSON:
    """Get the landing page."""

    return {
        "title": "TileCloud-chain",
        "description": "Access to the tiles via a Web API that conforms to the OGC API Tiles specification.",
        "links": [
            {
                "href": request.current_route_url(),
                "rel": "self",
                "type": "application/json",
                "title": "this document",
            },
            {
                "href": request.route_url("api"),
                "rel": "service-desc",
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "the API definition",
            },
            {
                "href": request.route_url("api"),
                "rel": "service-doc",
                "type": "text/html",
                "title": "the API documentation",
            },
            {
                "href": request.route_url("conformance"),
                "rel": "conformance",
                "type": "application/json",
                "title": "OGC API conformance classes implemented by this service",
            },
            {
                "href": request.route_url("collections"),
                "rel": "data",
                "type": "application/json",
                "title": "Information about the collections",
            },
        ],
    }


@view_config(route_name="conformance", openapi=True, renderer="fast_json")  # type: ignore
def conformance(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about the server implementation."""
    del request

    return {
        "conformsTo": [
            "https://www.opengis.net/spec/ogcapi-common-1/1.0/conf/core",
            "https://www.opengis.net/spec/ogcapi-common-1/1.0/conf/json",
            "https://www.opengis.net/spec/ogcapi-common-1/1.0/conf/html",
            "https://www.opengis.net/spec/ogcapi-common-1/1.0/conf/oas30",
            # "https://www.opengis.net/spec/ogcapi-common-2/1.0/conf/collections",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/core",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/tileset",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/tilesets-list",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/geodata-tilesets",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/dataset-tilesets",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/geodata-selection",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/jpeg",
            "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/png",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/mvt",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/geojson",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/tiff",
            # "https://www.opengis.net/spec/ogcapi-tiles-1/1.0/conf/netcdf"
        ]
    }


@view_config(route_name="api", openapi=True, renderer="fast_json")  # type: ignore
def api(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about the API."""
    del request
    return {}


@view_config(route_name="api_all_collections", openapi=True, renderer="fast_json")  # type: ignore
def api_all_collections(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all collections."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    return {"type": "enum", "enum": list(config.get("layers", {}).keys())}


@view_config(route_name="api_coverage_collections", openapi=True, renderer="fast_json")  # type: ignore
def api_coverage_collections(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all coverage collections."""
    del request

    return {"type": "enum", "enum": []}


@view_config(route_name="api_vectorTiles_collections", openapi=True, renderer="fast_json")  # type: ignore
def api_vector_tiles_collections(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all vector tiles collections."""
    del request

    return {"type": "enum", "enum": []}


@view_config(route_name="api_tileMatrixSets", openapi=True, renderer="fast_json")  # type: ignore
def api_tile_matrix_sets(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all tile matrix sets."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    return {"type": "enum", "enum": list(config.get("grids", {}).keys())}


@view_config(route_name="api_styles", openapi=True, renderer="fast_json")  # type: ignore
def api_styles(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all styles."""

    return {"type": "enum", "enum": []}


def _collections_collection_id(config: tilecloud_chain.configuration.Configuration, name: str) -> _JSON:
    layer = config.get("layers", {}).get(name)
    assert layer is not None
    matrix_set = config.get("grids", {}).get(layer["grid"])
    assert matrix_set is not None

    return _copy(
        {
            "id": name,
            "extent": {"spatial": {"bbox": [_wgs84_bbox(_proj(matrix_set["srs"]), matrix_set["bbox"])]}},
            "grid": [{"resolution": resolution} for resolution in matrix_set["resolutions"]],
            "links": [],
        },
        [
            (layer, "title", "title"),
            (layer, "description", "description"),
        ],
    )


@view_config(route_name="collections", openapi=True, renderer="fast_json")  # type: ignore
def collections(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all collections."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    return {
        "links": [
            {
                "href": request.current_route_url(),
                "rel": "self",
                "type": "application/json",
                "title": "this document",
            },
            {
                "href": request.route_url("collections"),
                "rel": "alternate",
                "type": "text/html",
                "title": "this document as HTML",
            },
        ],
        "collections": [_collections_collection_id(config, name) for name in config.get("layers", {}).keys()],
    }


@view_config(route_name="collections_collectionId", openapi=True, renderer="fast_json")  # type: ignore
def collections_collection_id(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about a collection."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config

    return _collections_collection_id(config, request.matchdict["collectionId"])


def _tile_matrix_set_id(name: str, matrix_set: tilecloud_chain.configuration.Grid) -> _JSON:
    return _copy(
        {
            "id": name,
            "crs": matrix_set["srs"],
            "links": [],
        },
        [(matrix_set, "title", "title")],
    )


@view_config(route_name="tileMatrixSets", openapi=True, renderer="fast_json")  # type: ignore
def tile_matrix_sets(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about all tile matrix sets."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    return {
        "tileMatrixSets": [
            _tile_matrix_set_id(name, matrix_set) for name, matrix_set in config.get("grids", {}).items()
        ]
    }


def _proj(crs: str) -> pyproj.CRS:
    return pyproj.CRS.from_string(crs)


def _lower_left(proj: pyproj.CRS, bbox: List[float]) -> List[float]:
    if proj.axis_info[0].direction == "east":
        return [bbox[0], bbox[1]]
    else:
        return [bbox[1], bbox[0]]


def _upper_right(proj: pyproj.CRS, bbox: List[float]) -> List[float]:
    if proj.axis_info[0].direction == "east":
        return [bbox[2], bbox[3]]
    else:
        return [bbox[3], bbox[2]]


def _top_left(proj: pyproj.CRS, bbox: List[float]) -> List[float]:
    if proj.axis_info[0].direction == "east":
        return [bbox[0], bbox[3]]
    else:
        return [bbox[3], bbox[0]]


def _ordered_axes(proj: pyproj.CRS) -> List[str]:
    if proj.axis_info[0].direction == "east":
        return ["easting", "northing"]
    else:
        return ["northing", "easting"]


def _bbox(proj: pyproj.CRS, bbox: List[Union[int, float]]) -> List[Union[int, float]]:
    return bbox if proj.axis_info[0].direction == "east" else [bbox[1], bbox[0], bbox[3], bbox[2]]


def _wgs84_bbox(proj: pyproj.CRS, bbox: List[Union[int, float]]) -> List[Union[int, float]]:
    bbox = _bbox(proj, bbox)

    transformer = pyproj.Transformer.from_crs(proj, pyproj.CRS.from_epsg(4326))
    return [*transformer.transform(bbox[0], bbox[1]), *transformer.transform(bbox[2], bbox[3])]


@view_config(route_name="tileMatrixSets_tileMatrixSetId", openapi=True, renderer="fast_json")  # type: ignore
def tile_matrix_set_id(request: pyramid.request.Request) -> _JSON:
    """Retrieve information about the tile matrix set."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    matrix_set = config.get("grids", {}).get(request.matchdict["tileMatrixSetId"])
    assert matrix_set is not None
    proj = _proj(matrix_set["srs"])

    return _copy(
        {
            "id": request.matchdict["tileMatrixSetId"],
            # "uri": "string",
            "orderedAxes": _ordered_axes(proj),
            "crs": matrix_set["srs"],
            # "wellKnownScaleSet": "string",
            "boundingBox": {
                "lowerLeft": _lower_left(proj, matrix_set["bbox"]),
                "upperRight": _upper_right(proj, matrix_set["bbox"]),
                "crs": matrix_set["srs"],
                "orderedAxes": _ordered_axes(proj),
            },
            "tileMatrices": [
                {
                    # "title": "string",
                    # "description": "string",
                    # "keywords": ["string"],
                    "id": str(pos),
                    "scaleDenominator": resolution / 0.00028,
                    "cellSize": 0,  # What's that?
                    "cornerOfOrigin": "topLeft",
                    "pointOfOrigin": _top_left(proj, matrix_set["bbox"]),
                    "tileWidth": matrix_set["tile_size"],
                    "tileHeight": matrix_set["tile_size"],
                    "matrixHeight": int(
                        math.ceil(
                            (matrix_set["bbox"][2] - matrix_set["bbox"][0])
                            / resolution
                            / matrix_set["tile_size"]
                        )
                    ),
                    "matrixWidth": int(
                        math.ceil(
                            (matrix_set["bbox"][3] - matrix_set["bbox"][1])
                            / resolution
                            / matrix_set["tile_size"]
                        )
                    ),
                    # "variableMatrixWidths": [{"coalesce": 2, "minTileRow": 0, "maxTileRow": 0}],
                }
                for pos, resolution in enumerate(matrix_set["resolutions"])
            ],
        },
        [
            (matrix_set, "title", "title"),
            (matrix_set, "description", "description"),
            (matrix_set, "keywords", "keywords"),
        ],
    )


@view_config(route_name="collections_collectionId_map_tiles", openapi=True, renderer="fast_json")  # type: ignore
def tiles_collection(request: pyramid.request.Request) -> _JSON:
    """Retrieve the list of all default map tile sets for the whole dataset."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    layer = config.get("layers", {}).get(request.matchdict["collectionId"])
    assert layer is not None
    matrix_set = config.get("grids", {}).get(layer["grid"])
    assert matrix_set is not None

    return {
        "tilesets": [
            {
                "title": layer.get("grid"),
                "dataType": "tiles",
                "crs": matrix_set.get("srs", ""),
                "tileMatrixSetURI": layer.get("grid"),
                "links": [],
            }
        ]
    }


@view_config(
    route_name="collections_collectionId_map_tiles_tileMatrixSetId", openapi=True, renderer="fast_json"
)  # type: ignore
def tiles_collection_tile_matrix_set_id(request: pyramid.request.Request) -> _JSON:
    """Retrieve a default map tile set of the whole dataset for the specified tiling scheme (tile matrix set)."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host).config
    layer = config.get("layers", {}).get(request.matchdict["collectionId"])
    assert layer is not None
    matrix_set = config.get("grids", {}).get(request.matchdict["tileMatrixSetId"])
    assert matrix_set is not None
    metadata = config.get("metadata", {})
    provider = config.get("provider", {})
    proj = _proj(matrix_set["srs"])

    return _copy(
        {
            "title": layer.get("title", ""),
            "description": layer.get("description", ""),
            "dataType": "map",
            "crs": matrix_set.get("srs", ""),
            "tileMatrixSetURI": request.matchdict["tileMatrixSetId"],
            # "tileMatrixSetLimits": [
            #     {
            #         "tileMatrix": request.matchdict["tileMatrixSetId"],
            #         "minTileRow": 0,
            #         "maxTileRow": 0,
            #         "minTileCol": 0,
            #         "maxTileCol": 0,
            #     }
            # ],
            # "epoch": 0,
            "layers": [
                _copy(
                    {
                        "id": request.matchdict["collectionId"],
                        "dataType": "map",
                        "crs": matrix_set["srs"],
                        # epoch": 0,
                        "boundingBox": {
                            "lowerLeft": _lower_left(proj, matrix_set["bbox"]),
                            "upperRight": _upper_right(proj, matrix_set["bbox"]),
                            "crs": matrix_set["srs"],
                            "orderedAxes": _ordered_axes(proj),
                        },
                        # "style": layer["wmts_style"],
                        # "geoDataClasses": ["map"],
                        # "propertiesSchema": {
                        #    "type": "object",
                        #    "properties": {},
                        # },
                    },
                    [
                        (layer, "title", "title"),
                        (layer, "description", "description"),
                        # (metadata, "keywords", "keywords"),
                        (metadata, "attribution", "attribution"),
                        (metadata, "license", "license"),
                        (provider, "pointOfContact", "pointOfContact"),
                        (provider, "name", "publisher"),
                        (layer, "theme", "theme"),
                        (layer, "created", "created"),
                        (layer, "updated", "updated"),
                    ],
                )
            ],
            "boundingBox": {
                "lowerLeft": _lower_left(proj, matrix_set["bbox"]),
                "upperRight": _upper_right(proj, matrix_set["bbox"]),
                "crs": matrix_set["srs"],
                "orderedAxes": _ordered_axes(proj),
            },
            "centerPoint": {
                "coordinates": _bbox(proj, matrix_set["bbox"]),
                "crs": matrix_set["srs"],
                "tileMatrix": request.matchdict["tileMatrixSetId"],
                # "scaleDenominator": ?,
                # "cellSize": ?,
            },
            "style": {
                "id": layer["wmts_style"],
                # "title": "",
                # "description": "",
                # "keywords": [],
            },
            "mediaTypes": [layer["mime_type"]],
            "links": []
            # "accessConstraints": "unclassified",
        },
        [
            (metadata, "attribution", "attribution"),
            (metadata, "license", "license"),
            (metadata, "keywords", "keywords"),
            (layer, "version", "version"),
            (layer, "created", "created"),
            (layer, "updated", "updated"),
            (provider, "pointOfContact", "pointOfContact"),
        ],
    )


_SERVER = PyramidServer()


@view_config(  # type: ignore
    route_name="collections_collectionId_map_tiles_tileMatrixSetId_tileMatrix_tileRow_tileCol", openapi=True
)
def tiles_collection_tile_matrix_set_id_row_col(
    request: pyramid.request.Request,
) -> pyramid.response.Response:
    """Retrieve a default map tile of the whole dataset."""

    tilegeneration = init_tilegeneration(request.registry.settings.get("tilegeneration_configfile"))
    config = tilegeneration.get_host_config(request.host)
    layer = config.config.get("layers", {}).get(request.matchdict["collectionId"])
    assert layer is not None

    kwargs = {"host": request.host, "request": request}
    tile = Tile(
        TileCoord(
            # TODO fix for matrix_identifier = resolution
            int(request.matchdict["tileMatrix"]),
            int(request.matchdict["tileCol"]),
            int(request.matchdict["tileRow"]),
        ),
        metadata={},
    )

    if tile.tilecoord.z > get_max_zoom_seed(config, request.matchdict["collectionId"]):
        return internal_mapcache.fetch(config, _SERVER, tilegeneration, layer, tile, kwargs)

    layer_filter = _SERVER.get_filter(config, request.matchdict["collectionId"])
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
        if not layer_filter.filter_tilecoord(config, meta_tilecoord, request.matchdict["collectionId"]):
            return internal_mapcache.fetch(config, _SERVER, tilegeneration, layer, tile, kwargs)

    store = _SERVER.get_store(config, request.matchdict["collectionId"])
    if store is None:
        layer_name = request.matchdict["collectionId"]
        return pyramid.httpexceptions.HTTPBadRequest(f"No store found for layer '{layer_name}'")

    tile2 = store.get_one(tile)
    if tile2:
        if tile2.error:
            return pyramid.httpexceptions.HTTPInternalServerError(tile2.error)

        assert tile2.data
        assert tile2.content_type
        request.response.headers.update(
            {
                "Content-Type": tile2.content_type,
                "Expires": (
                    datetime.datetime.utcnow() + datetime.timedelta(hours=get_expires_hours(config))
                ).isoformat(),
                "Cache-Control": f"max-age={3600 * get_expires_hours(config)}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Tile-Backend": "Cache",
            }
        )
        if isinstance(tile2.data, memoryview):
            request.response.body_file = tile2.data
        else:
            request.response.body = tile2.data
        return request.response
    else:
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Expires": (
                datetime.datetime.utcnow() + datetime.timedelta(hours=get_expires_hours(config))
            ).isoformat(),
            "Cache-Control": f"max-age={3600 * get_expires_hours(config)}",
        }

        return pyramid.httpexceptions.HTTPNoContent(headers=headers)
