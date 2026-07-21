from typing import IO, Any
from unittest.mock import Mock

import pytest

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
