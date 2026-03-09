# SPDX-License-Identifier: Apache-2.0

"""HALO Agent Framework sample — DevUI entry point."""

from __future__ import annotations

import asyncio
import logging

import agent_framework_devui

from sample_agent_framework import settings
from sample_agent_framework.agents import halo_all_tools
from sample_agent_framework.utils import logger as logger_mod

logger = logging.getLogger(__name__)
log = logger_mod.create_logger("Server")


def main() -> None:
    """Build agents and launch the DevUI."""
    config = settings.Settings()
    logger_mod.configure_logging(config.log_level)

    # Build the agent; if the API is unreachable the DevUI still starts.
    entities: list[object] = []
    try:
        agent = asyncio.run(halo_all_tools.build())
        entities.append(agent)
    except Exception:
        log.warn("Agent build failed — is the sample API running on port 3001? The DevUI will start without tools.")

    log.section("HALO Agent Framework Sample")

    agent_framework_devui.serve(
        entities=entities,
        port=8080,
        host="0.0.0.0",
        ui_enabled=True,
    )


if __name__ == "__main__":
    main()
