# SPDX-License-Identifier: Apache-2.0

"""Colour-formatted logging configuration."""

import logging

_LEVEL_COLOURS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;31m",
}
_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    """Logging formatter that applies ANSI colour to the level name."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, "")
        record.levelname = f"{colour}{record.levelname:<8}{_RESET}"
        return super().format(record)


def configure_logging(level: str = "INFO") -> None:
    """Set up root logging with coloured output.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        _ColourFormatter(
            fmt="[%(asctime)s] %(levelname)s: %(name)s %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logging.basicConfig(level=level.upper(), handlers=[handler])
