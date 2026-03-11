# SPDX-License-Identifier: Apache-2.0

"""HALO Agent Framework sample — DevUI entry point."""

from __future__ import annotations

import asyncio
import pathlib

import uvicorn

from sample_agent_framework import settings, store
from sample_agent_framework.agents import halo_all_tools, halo_filter_tools
from sample_agent_framework.utils import devserver, logger

_THREADS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / ".threads"

log = logger.create_logger("Server")


def main() -> None:
    """Build agents and launch the DevUI."""
    config = settings.Settings()
    logger.configure_logging(config.log_level)

    persistence_store = store.FileBackedConversationStore(_THREADS_DIR)
    log.info("Persisting threads", {"path": str(_THREADS_DIR)})

    # Build agents; if the API is unreachable the DevUI still starts.
    entities: list[object] = []
    try:
        all_tools_agent = asyncio.run(halo_all_tools.build())
        entities.append(all_tools_agent)
    except Exception:
        log.warn("All-tools agent build failed — is the sample API running on port 3010?")

    tags = [t.strip() for t in config.halo_tags.split(",") if t.strip()]
    if tags:
        try:
            filter_agent = asyncio.run(halo_filter_tools.build(tags))
            entities.append(filter_agent)
        except Exception:
            log.warn("Filter-tools agent build failed — is the sample API running on port 3010?")

    if not entities:
        log.warn("No agents registered. The DevUI will start without tools.")

    server = devserver.PersistingDevServer(
        persistence=persistence_store,
        port=8080,
        host="0.0.0.0",
        ui_enabled=True,
    )

    if entities:
        server._pending_entities = entities

    app = server.get_app()

    log.section("HALO Agent Framework Sample")
    log.info("Starting DevUI", {"port": server.port})
    uvicorn.run(app, host=server.host, port=server.port, log_level="info")


if __name__ == "__main__":
    main()
