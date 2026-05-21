from typing import IO, Any

import pytest

from tilecloud_chain.views import admin


@pytest.mark.asyncio
async def test_run_returns_exception_message_when_output_is_empty() -> None:
    async def main(_args: list[str], _out: IO[str]) -> None:
        raise ValueError("Invalid grid 'unknown_grid'")

    result: dict[str, Any] = {}
    await admin._run(["generate-tiles", "--grid=unknown_grid"], main, result)

    assert result["error"] is True
    assert result["out"] == "Error while running the command: Invalid grid 'unknown_grid'"


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
