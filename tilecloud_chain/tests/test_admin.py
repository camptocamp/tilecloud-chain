# Copyright (c) 2026 by Camptocamp
from types import SimpleNamespace
from typing import IO, Any
from unittest.mock import AsyncMock, Mock

import pytest
from c2casgiutils.config import GitHubAccessType

from tilecloud_chain import DatedConfig
from tilecloud_chain.views import admin


@pytest.mark.asyncio
async def test_run_returns_exception_message_when_output_is_empty() -> None:
    async def main(_args: list[str], _out: IO[str]) -> None:
        raise ValueError("Invalid grid 'unknown_grid'")

    result: dict[str, Any] = {}
    await admin._run(["generate-tiles", "--grid=unknown_grid"], main, result)

    assert result["error"] is True
    assert result["out"] == "Error while running the command: Invalid grid &#x27;unknown_grid&#x27;"


@pytest.mark.asyncio
async def test_run_keeps_command_output_on_error() -> None:
    async def main(_args: list[str], out: IO[str]) -> None:
        out.write("A detailed error message from command output")
        raise RuntimeError("should not replace output")

    result: dict[str, Any] = {}
    await admin._run(["generate-tiles"], main, result)

    assert result["error"] is True
    assert result["out"] == "A detailed error message from command output"


@pytest.mark.asyncio
async def test_run_escapes_fallback_exception_message() -> None:
    async def main(_args: list[str], _out: IO[str]) -> None:
        raise ValueError("<script>alert('xss')</script>")

    result: dict[str, Any] = {}
    await admin._run(["generate-tiles"], main, result)

    assert result["error"] is True
    assert "<script>" not in result["out"]
    assert "&lt;script&gt;" in result["out"]


@pytest.mark.asyncio
async def test_run_truncates_fallback_exception_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def main(_args: list[str], _out: IO[str]) -> None:
        raise ValueError("x" * 200)

    monkeypatch.setattr(admin.settings, "max_output_length", 40)

    result: dict[str, Any] = {}
    await admin._run(["generate-tiles"], main, result)

    assert result["error"] is True
    assert result["out"].endswith("\n...")
    assert len(result["out"]) <= 41


@pytest.mark.asyncio
async def test_validate_config_file_warns_about_reserved_wms_params(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tilecloud_chain.views.admin.jsonschema_validator.validate",
        Mock(return_value=([], None)),
    )
    config = DatedConfig(
        config={
            "layers": {
                "test_layer": {
                    "type": "wms",
                    "url": "http://example.com/wms",
                    "params": {
                        "SRS": "EPSG:2056",
                        "BBOX": "0,0,1,1",
                        "CUSTOM": "valid_param",
                    },
                },
                "good_layer": {
                    "type": "wms",
                    "url": "http://example.com/wms",
                    "params": {
                        "CUSTOM": "valid_param",
                    },
                },
            },
        },
        mtime=0.0,
        file=Mock(),
    )

    structure_errors, deprecation_warnings = await admin._validate_config_file(config)

    assert structure_errors == []
    assert len(deprecation_warnings) == 2
    assert "test_layer" in deprecation_warnings[0]
    assert "SRS" in deprecation_warnings[0]
    assert "BBOX" in deprecation_warnings[1]


@pytest.mark.asyncio
async def test_validate_config_file_skips_non_wms_layers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tilecloud_chain.views.admin.jsonschema_validator.validate",
        Mock(return_value=([], None)),
    )
    config = DatedConfig(
        config={
            "layers": {
                "mapnik_layer": {
                    "type": "mapnik",
                    "params": {"SRS": "EPSG:2056"},
                },
            },
        },
        mtime=0.0,
        file=Mock(),
    )

    structure_errors, deprecation_warnings = await admin._validate_config_file(config)

    assert structure_errors == []
    assert deprecation_warnings == []


def _patch_access(
    monkeypatch: pytest.MonkeyPatch,
    *,
    username: str | None = None,
    admin_access: bool = False,
    check_results: list[bool] | None = None,
) -> AsyncMock:
    monkeypatch.setattr(
        admin.c2c_config,
        "settings",
        SimpleNamespace(auth=SimpleNamespace(test=SimpleNamespace(username=username))),
    )
    monkeypatch.setattr(admin.auth, "check_admin_access", AsyncMock(return_value=admin_access))
    check_mock = AsyncMock(side_effect=check_results or [])
    monkeypatch.setattr(admin.auth, "check_access_config", check_mock)
    return check_mock


@pytest.mark.asyncio
async def test_access_level_test_user(monkeypatch: pytest.MonkeyPatch) -> None:
    check = _patch_access(monkeypatch, username="tester")
    config = DatedConfig(config={}, mtime=0.0, file=Mock())

    assert await admin._get_access_level(config, Mock()) is admin.AccessLevel.READ_WRITE
    check.assert_not_awaited()


@pytest.mark.asyncio
async def test_access_level_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    check = _patch_access(monkeypatch, admin_access=True)
    config = DatedConfig(config={}, mtime=0.0, file=Mock())

    assert await admin._get_access_level(config, Mock()) is admin.AccessLevel.READ_WRITE
    check.assert_not_awaited()


@pytest.mark.asyncio
async def test_access_level_read_write(monkeypatch: pytest.MonkeyPatch) -> None:
    check = _patch_access(monkeypatch, check_results=[True])
    config = DatedConfig(
        config={"authentication": {"github_repository": "org/repo", "github_access_type": "push"}},
        mtime=0.0,
        file=Mock(),
    )

    assert await admin._get_access_level(config, Mock()) is admin.AccessLevel.READ_WRITE
    assert check.await_count == 1
    auth_config = check.await_args_list[0].args[1]
    assert auth_config.github_repository == "org/repo"
    assert auth_config.github_access_type_read_write is GitHubAccessType.PUSH
    assert auth_config.github_access_type_read_only is None


@pytest.mark.asyncio
async def test_access_level_read_only_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    check = _patch_access(monkeypatch, check_results=[False, True])
    config = DatedConfig(
        config={"authentication": {"github_repository": "org/repo", "github_access_type": "push"}},
        mtime=0.0,
        file=Mock(),
    )

    assert await admin._get_access_level(config, Mock()) is admin.AccessLevel.READ_ONLY
    assert check.await_count == 2
    read_only_config = check.await_args_list[1].args[1]
    assert read_only_config.github_access_type_read_only is GitHubAccessType.PULL
    assert read_only_config.github_access_type_read_write is None


@pytest.mark.asyncio
async def test_access_level_no_access(monkeypatch: pytest.MonkeyPatch) -> None:
    check = _patch_access(monkeypatch, check_results=[False, False])
    config = DatedConfig(
        config={"authentication": {"github_repository": "org/repo", "github_access_type": "push"}},
        mtime=0.0,
        file=Mock(),
    )

    assert await admin._get_access_level(config, Mock()) is admin.AccessLevel.NO_ACCESS
    assert check.await_count == 2
