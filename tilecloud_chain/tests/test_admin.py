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
