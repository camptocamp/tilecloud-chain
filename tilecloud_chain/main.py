# Copyright (c) 2025-2026 by Stéphane Brunner
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
import os
import resource
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager

# Using pathlib.Path here instead of anyio.Path because this is used at module level
# for static file directory configuration, which doesn't require async I/O operations
from pathlib import Path

import c2casgiutils
import c2cwsgiutils.prometheus
import prometheus_client
import prometheus_client.core
import prometheus_client.registry
import psutil
import sentry_sdk
from c2casgiutils import config, headers, health_checks
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import start_http_server
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from tilecloud_chain import server
from tilecloud_chain.views import admin

_LOGGER = logging.getLogger(__name__)

# Initialize Sentry if the URL is provided
if config.settings.sentry.dsn or "SENTRY_DSN" in os.environ:
    _LOGGER.info("Sentry is enabled with URL: %s", config.settings.sentry.dsn or os.environ.get("SENTRY_DSN"))
    sentry_sdk.init(**config.settings.sentry.model_dump())


@asynccontextmanager
async def _lifespan(main_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application lifespan events."""

    _LOGGER.info("Starting the application")
    await c2casgiutils.startup(main_app)
    await server.startup(main_app)
    await admin.startup(main_app)

    yield


# Core Application Instance
app = FastAPI(title="TileCloud-chain WMTS API", lifespan=_lifespan)

# Add TrustedHostMiddleware (should be first)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure with specific hosts in production
)

http = os.environ.get("HTTP", "False").lower() in ["true", "1"]
# Add HTTPSRedirectMiddleware
if not http:
    app.add_middleware(HTTPSRedirectMiddleware)

# Add GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Set all CORS origins enabled
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    headers.ArmorHeaderMiddleware,
    headers_config={
        "http": {"headers": {"Strict-Transport-Security": None} if not http else {}},
        "admin": {
            "path_match": r"^admin/?$",
            "headers": {
                "Content-Security-Policy": {
                    "default-src": ["'self'"],
                    "script-src-elem": [
                        "'self'",
                        "'unsafe-inline'",  # TODO: remove this: https://github.com/camptocamp/tilecloud-chain/issues/3053
                        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/",
                        "https://cdnjs.cloudflare.com/ajax/libs/jquery/",
                        "https://cdnjs.cloudflare.com/ajax/libs/popper.js/",
                    ],
                    "style-src-elem": [
                        "'self'",
                        "'unsafe-inline'",  # TODO: remove this: https://github.com/camptocamp/tilecloud-chain/issues/3053
                        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap/",
                    ],
                    "style-src-attr": [
                        "'self'",
                        "'unsafe-inline'",  # TODO: remove this: https://github.com/camptocamp/tilecloud-chain/issues/3053
                    ],
                },
            },
        },
        "admin-test": {
            "path_match": r"^admin/test/?$",
            "headers": {
                "Content-Security-Policy": {
                    "default-src": ["'self'"],
                    "script-src-elem": [
                        "'self'",
                        "'unsafe-inline'",  # TODO: remove this: https://github.com/camptocamp/tilecloud-chain/issues/3053
                        "https://cdn.jsdelivr.net/npm/ol@10.8.0/",
                        "https://unpkg.com/ol-layerswitcher@4.1.2/",
                        "https://cdnjs.cloudflare.com/ajax/libs/proj4js/",
                    ],
                    "style-src-elem": [
                        "'self'",
                        "'unsafe-inline'",  # TODO: remove this: https://github.com/camptocamp/tilecloud-chain/issues/3053
                        "https://cdn.jsdelivr.net/npm/ol@10.8.0/",
                        "https://unpkg.com/ol-layerswitcher@4.1.2/",
                    ],
                },
            },
        },
    },
)


class RootResponse(BaseModel):
    """Response of the root endpoint."""

    message: str


# Add Health Checks
health_checks.FACTORY.add(health_checks.Redis(tags=["redis", "all"]))

# Add Routers
# Mount the most specific routes first to ensure correct routing precedence.
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(server.router, tags=["wmts"])  # WMTS routes
app.mount("/c2c", c2casgiutils.app)  # C2C utility routes
app.mount("/admin", admin.app)  # Admin routes

# Get Prometheus HTTP server port from environment variable 9000 by default
start_http_server(config.settings.prometheus.port)

instrumentator = Instrumentator(should_instrument_requests_inprogress=True)
instrumentator.instrument(app)


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


# Set up Prometheus metrics
prometheus_client.core.REGISTRY.register(_ResourceCollector())
prometheus_client.core.REGISTRY.register(_MemoryInfoCollector())
