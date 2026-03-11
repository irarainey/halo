# SPDX-License-Identifier: Apache-2.0

"""Structured, colourful console logging.

Provides a custom :class:`Logger` with timestamped, symbol-prefixed output
and structured ``key=value`` data, plus a standard-library logging handler
so messages from third-party code render in the same style.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import UTC, datetime

# ── ANSI colours ────────────────────────────────────────────────

_colours = {
    "reset": "\033[0m",
    "bright": "\033[1m",
    "dim": "\033[2m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "blue": "\033[34m",
    "gray": "\033[90m",
}

_level_colour = {
    "info": _colours["cyan"],
    "success": _colours["green"],
    "warn": _colours["yellow"],
    "error": _colours["red"],
    "debug": _colours["gray"],
    "timing": _colours["magenta"],
}

_level_symbol = {
    "info": "\u2139",
    "success": "\u2713",
    "warn": "\u26a0",
    "error": "\u2717",
    "debug": "\u2022",
    "timing": "\u23f1",
}

# Map standard logging level names to our internal level keys.
_STD_LEVEL_MAP: dict[str, str] = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warn",
    "ERROR": "error",
    "CRITICAL": "error",
}

# ── Formatting helpers ──────────────────────────────────────────


def _get_timestamp() -> str:
    """Return the current UTC time as ``HH:MM:SS.mmm``."""
    now = datetime.now(UTC)
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def _format_duration(ms: float) -> str:
    """Format a duration in milliseconds for display."""
    if ms < 1000:
        return f"{int(ms)}ms"
    if ms < 60000:
        return f"{ms / 1000:.2f}s"
    minutes = int(ms // 60000)
    seconds = (ms % 60000) / 1000
    return f"{minutes}m {seconds:.1f}s"


def _format_value(value: object) -> str:
    """Return an ANSI-coloured representation of *value*."""
    c = _colours
    if value is None:
        return f"{c['dim']}None{c['reset']}"
    if isinstance(value, bool):
        return f"{c['green']}True{c['reset']}" if value else f"{c['red']}False{c['reset']}"
    if isinstance(value, (int, float)):
        return f"{c['yellow']}{value}{c['reset']}"
    if isinstance(value, str):
        display = value[:497] + "..." if len(value) > 500 else value
        return f'{c["green"]}"{display}"{c["reset"]}'
    if isinstance(value, list):
        return f"{c['cyan']}[{len(value)} items]{c['reset']}"
    if isinstance(value, dict):
        return f"{c['cyan']}{{{len(value)} keys}}{c['reset']}"
    return str(value)


# ── Logger class ────────────────────────────────────────────────


class Logger:
    """Structured logger with context prefix and timing support."""

    def __init__(self, context: str = "Server") -> None:
        self._context = context
        self._timers: dict[str, tuple[float, str]] = {}

    def _log(self, level: str, message: str, data: dict[str, object] | None = None) -> None:
        ts = _get_timestamp()
        colour = _level_colour.get(level, _colours["cyan"])
        symbol = _level_symbol.get(level, "\u2139")
        c = _colours

        prefix = f"{c['gray']}[{ts}]{c['reset']} {colour}{symbol}{c['reset']} {c['bright']}[{self._context}]{c['reset']}"

        if data:
            data_str = " ".join(f"{c['dim']}{k}={c['reset']}{_format_value(v)}" for k, v in data.items())
            log_line = f"{prefix} {message} {data_str}"
        else:
            log_line = f"{prefix} {message}"

        print(log_line, file=sys.stderr)  # noqa: T201

    def info(self, message: str, data: dict[str, object] | None = None) -> None:
        self._log("info", message, data)

    def success(self, message: str, data: dict[str, object] | None = None) -> None:
        self._log("success", message, data)

    def warn(self, message: str, data: dict[str, object] | None = None) -> None:
        self._log("warn", message, data)

    def error(self, message: str, data: dict[str, object] | None = None) -> None:
        self._log("error", message, data)

    def debug(self, message: str, data: dict[str, object] | None = None) -> None:
        self._log("debug", message, data)

    def start_timer(self, label: str) -> None:
        self._timers[label] = (time.monotonic() * 1000, _get_timestamp())
        self._log("timing", f"Starting: {label}")

    def end_timer(self, label: str, message: str | None = None) -> float:
        entry = self._timers.pop(label, None)
        if entry is None:
            self.warn(f'Timer "{label}" was not started')
            return 0.0

        start_ms, start_ts = entry
        duration = time.monotonic() * 1000 - start_ms
        c = _colours
        duration_str = f"{c['magenta']}{_format_duration(duration)}{c['reset']}"
        display_message = message or f"Completed: {label}"
        self._log(
            "timing",
            f"{display_message} {c['dim']}took{c['reset']} {duration_str} {c['dim']}(started {start_ts}){c['reset']}",
        )
        return duration

    def section(self, title: str) -> None:
        c = _colours
        line = "\u2500" * 60
        parts = (
            "",
            f"{c['blue']}{line}{c['reset']}",
            f"{c['blue']}{c['bright']}  {title}{c['reset']}",
            f"{c['blue']}{line}{c['reset']}",
            "",
        )
        for ln in parts:
            print(ln, file=sys.stderr)  # noqa: T201


# ── Standard-library bridge ─────────────────────────────────────


class _BridgeHandler(logging.Handler):
    """Logging handler that emits records in the same visual style."""

    def emit(self, record: logging.LogRecord) -> None:
        level = _STD_LEVEL_MAP.get(record.levelname, "info")
        ts = _get_timestamp()
        colour = _level_colour.get(level, _colours["cyan"])
        symbol = _level_symbol.get(level, "\u2139")
        c = _colours

        # Use the last segment of the logger name as context.
        context = record.name.rsplit(".", 1)[-1] if record.name else "root"
        prefix = f"{c['gray']}[{ts}]{c['reset']} {colour}{symbol}{c['reset']} {c['bright']}[{context}]{c['reset']}"
        print(f"{prefix} {record.getMessage()}", file=sys.stderr)  # noqa: T201


def create_logger(context: str) -> Logger:
    """Create a :class:`Logger` for a specific module or component."""
    return Logger(context)


def configure_logging(level: str = "INFO") -> None:
    """Install the bridge handler on the root logger.

    This ensures messages from third-party libraries (``halo_fastapi``,
    ``uvicorn``, ``agent_framework``, etc.) render in the same style.
    """
    resolved = getattr(logging, level.upper(), logging.INFO)
    handler = _BridgeHandler(level=resolved)

    root = logging.getLogger()
    root.setLevel(resolved)
    # Remove any existing handlers to prevent duplicate output.
    root.handlers.clear()
    root.addHandler(handler)

    # Uvicorn creates its own loggers with their own handlers.
    # Replace them so all output uses the same style.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.propagate = False
