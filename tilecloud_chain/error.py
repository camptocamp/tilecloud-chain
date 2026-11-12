# Copyright (c) 2026 by Camptocamp
"""Format the tile generation errors with all the useful details."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorContext:
    """The context in which an error was raised, to be able to explain what failed."""

    url: str | None = None
    duration: float | None = None
    step: str | None = None
    layer: str | None = None
    host: str | None = None
    hint: str | None = None


_MAX_MESSAGE_LENGTH = 2000
_MAX_CAUSES = 3


class TileGenerationError(RuntimeError):
    """An error raised while generating a tile, already formatted with its context."""


def _format_exception(error: BaseException) -> str:
    message = str(error)
    if not message:
        return f"{type(error).__name__}: <no message>"
    return f"{type(error).__name__}: {message}"


def _get_causes(error: BaseException) -> list[BaseException]:
    causes: list[BaseException] = []
    current: BaseException | None = error.__cause__
    if current is None:
        current = error.__context__
    seen = {id(error)}
    while current is not None and id(current) not in seen and len(causes) < _MAX_CAUSES:
        seen.add(id(current))
        causes.append(current)
        current = current.__cause__ if current.__cause__ is not None else current.__context__
    return causes


def format_error(error: BaseException | str, context: ErrorContext | None = None) -> str:
    """
    Format an error with enough details to understand what failed.

    The type of the error is always displayed, even when the error has no message at all, the
    cause chain is appended, and the context (URL, elapsed time, failing step, layer, host) is
    added as additional lines.
    """
    lines: list[str] = []
    if isinstance(error, TileGenerationError):
        # already formatted with its context when raised
        lines.append(str(error))
    elif isinstance(error, str):
        lines.append(error or "<no message>")
    else:
        lines.append(_format_exception(error))
        lines.extend(f"Caused by: {_format_exception(cause)}" for cause in _get_causes(error))
        notes = error.__dict__.get("__notes__")
        if isinstance(notes, list):
            lines.extend(f"Note: {note}" for note in notes)

    if context is not None:
        if context.url is not None:
            elapsed = "" if context.duration is None else f" (after {context.duration:.3f} s)"
            lines.append(f"URL: {context.url}{elapsed}")
        elif context.duration is not None:
            lines.append(f"Elapsed: {context.duration:.3f} s")
        if context.step is not None:
            lines.append(f"Step: {context.step}")
        if context.layer is not None:
            lines.append(f"Layer: {context.layer}")
        if context.host is not None:
            lines.append(f"Host: {context.host}")
        if context.hint is not None:
            lines.append(f"Hint: {context.hint}")

    message = "\n".join(lines)
    if len(message) > _MAX_MESSAGE_LENGTH:
        message = f"{message[:_MAX_MESSAGE_LENGTH]}... (truncated)"
    return message
