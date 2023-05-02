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

import logging

import pyramid.config
from pyramid.config import PHASE0_CONFIG, Configurator

_LOG = logging.getLogger(__name__)


def includeme(config: Configurator) -> None:
    """Include OGC API interface."""

    config.include("pyramid_openapi3")
    apiname = "ogcapi_tiles"
    config.pyramid_openapi3_spec("/app/ogcapi-tiles-bundled-filtered.json", apiname=apiname)
    config.pyramid_openapi3_add_explorer(apiname=apiname)

    def add_routes() -> None:
        class OgcType:
            def __init__(self, val: str, config: pyramid.config.Configurator):
                del config
                self.val = val

            def phash(self):
                return f"ogc_type = {self.val}"

            def __call__(self, context, request):
                if request.params.get("f") in ["html", "json"]:
                    _LOG.error(request.params["f"].lower() == self.val)
                    return request.params["f"].lower() == self.val
                _LOG.error(dict(request.headers))
                if request.headers.get("Accept", "*/*") == "*/*":
                    return self.val == "json"
                return request.accept.best_match(["text/html", "application/json"]).split("/")[1] == self.val

        config.add_route_predicate("ogc_type", OgcType)
        spec = config.registry.settings[apiname]["spec"]
        for pattern in spec["paths"].keys():
            if pattern == "/":
                config.add_route(
                    "landing_page_html",
                    pattern,
                    request_method="GET",
                    ogc_type="html",
                )
                config.add_route(
                    "landing_page_json",
                    pattern,
                    request_method="GET",
                    ogc_type="json",
                )
            else:
                config.add_route(
                    pattern.lstrip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_"),
                    pattern,
                    request_method="GET",
                )

    config.action((f"{apiname}_routes",), add_routes, order=PHASE0_CONFIG)

    config.scan("tilecloud_chain.ogcapi.views")
