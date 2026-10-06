# Copyright (c) 2026 by Camptocamp
"""Tests that configuration errors are propagated and displayed instead of 'No configuration found'."""

import os
from pathlib import Path

import pytest
from anyio import Path as AnyioPath
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from tilecloud_chain import DatedConfig, TileGeneration, server
from tilecloud_chain.settings import settings
from tilecloud_chain.views import admin

TILE_URL = "/tiles/1.0.0/point_hash/default/swissgrid_5/1/11/14.png"
HOSTS_CONTENT = """sources:
  tests:
    invalid.example.com: tilegeneration/wrong_type.yaml
"""


class TestConfigErrors:
    @classmethod
    def setup_class(cls) -> None:
        os.chdir(Path(__file__).parent)

    @classmethod
    def teardown_class(cls) -> None:
        os.chdir(Path(__file__).parent.parent.parent)

    @pytest.mark.asyncio
    async def test_schema_errors_are_kept(self) -> None:
        gene = TileGeneration(configure_logging=False)
        config = await gene.get_config(AnyioPath("tilegeneration/wrong_type.yaml"))
        assert not config
        assert config.errors
        assert any("grids.swissgrid_2.srs" in error for error in config.errors)

    @pytest.mark.asyncio
    async def test_yaml_syntax_error(self) -> None:
        gene = TileGeneration(configure_logging=False)
        config = await gene.get_config(AnyioPath("tilegeneration/wrong_yaml_syntax.yaml"))
        assert not config
        assert len(config.errors) == 1
        assert config.errors[0].startswith(
            "-- tilegeneration/wrong_yaml_syntax.yaml Unable to parse the YAML file:"
        )

    @pytest.mark.asyncio
    async def test_yaml_not_a_mapping(self) -> None:
        gene = TileGeneration(configure_logging=False)
        config = await gene.get_config(AnyioPath("tilegeneration/wrong_root_type.yaml"))
        assert not config
        assert config.errors == ["-- tilegeneration/wrong_root_type.yaml The config file must be a YAML mapping"]

    @pytest.mark.asyncio
    async def test_missing_config_file(self) -> None:
        gene = TileGeneration(configure_logging=False)
        config = await gene.get_config(AnyioPath("tilegeneration/does-not-exist.yaml"))
        assert not config
        assert config.errors == ["Missing config file tilegeneration/does-not-exist.yaml"]

    @pytest.mark.asyncio
    async def test_valid_config_has_no_errors(self) -> None:
        gene = TileGeneration(configure_logging=False)
        config = await gene.get_config(AnyioPath("tilegeneration/test-serve.yaml"))
        assert config
        assert config.errors == []

    def _setup_hosts(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        hosts_file = tmp_path / "hosts.yaml"
        hosts_file.write_text(HOSTS_CONTENT, encoding="utf-8")
        monkeypatch.setattr(settings, "hosts_file", AnyioPath(str(hosts_file)))
        server._TILEGENERATION = TileGeneration(configure_logging=False)

    def test_server_invalid_config_is_hidden(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._setup_hosts(monkeypatch, tmp_path)
        app = FastAPI()
        app.include_router(server.router)
        client = TestClient(app)

        response = client.get(TILE_URL, headers={"Host": "invalid.example.com"})
        assert response.status_code == 500
        assert response.json()["detail"] == (
            "The configuration of host 'invalid.example.com' is invalid, "
            "see the logs or the admin page for details"
        )

    def test_server_unknown_host(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._setup_hosts(monkeypatch, tmp_path)
        app = FastAPI()
        app.include_router(server.router)
        client = TestClient(app)

        response = client.get(TILE_URL, headers={"Host": "unknown.example.com"})
        assert response.status_code == 404
        assert response.json()["detail"] == "No configuration found for host 'unknown.example.com'"

    def test_admin_test_displays_errors(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._setup_hosts(monkeypatch, tmp_path)
        client = TestClient(admin.app)

        response = client.get("/test", headers={"Host": "invalid.example.com"})
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail.startswith("The configuration of host 'invalid.example.com' is invalid:\n")
        assert "grids.swissgrid_2.srs" in detail

    def test_admin_test_unknown_host(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._setup_hosts(monkeypatch, tmp_path)
        client = TestClient(admin.app)

        response = client.get("/test", headers={"Host": "unknown.example.com"})
        assert response.status_code == 404
        assert response.json()["detail"] == "No configuration found for host 'unknown.example.com'"

    @pytest.mark.asyncio
    async def test_serve_invalid_config(self) -> None:
        config = DatedConfig({}, 0.0, AnyioPath(), errors=["-- config.yaml grids: 'test' is not valid"])
        with pytest.raises(HTTPException) as exc_info:
            await server.server.serve({}, config, "invalid.example.com", None)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == (
            "The configuration of host 'invalid.example.com' is invalid, "
            "see the logs or the admin page for details"
        )

    @pytest.mark.asyncio
    async def test_get_static_invalid_config(self) -> None:
        config = DatedConfig({}, 0.0, AnyioPath(), errors=["-- config.yaml grids: 'test' is not valid"])
        with pytest.raises(HTTPException) as exc_info:
            await server.get_static("test.png", config)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == (
            "The configuration of the host is invalid, see the logs or the admin page for details"
        )
