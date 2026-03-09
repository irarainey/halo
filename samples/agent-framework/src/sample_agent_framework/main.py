# SPDX-License-Identifier: Apache-2.0

"""HALO Agent Framework sample — DevUI entry point."""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from agent_framework_devui import _server

from sample_agent_framework import settings, store
from sample_agent_framework.agents import halo_all_tools
from sample_agent_framework.utils import logger as logger_mod

_THREADS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / ".threads"

logger = logging.getLogger(__name__)
log = logger_mod.create_logger("Server")


class _PersistingDevServer(_server.DevServer):
    """DevServer that persists conversation turns to disk.

    Captures the ``response.completed`` SSE event at the end of each
    turn and writes it to the file-backed conversation store.
    """

    def __init__(
        self,
        persistence: store.FileBackedConversationStore,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._persistence = persistence

    async def _stream_execution(  # type: ignore[override]
        self,
        executor: _server.AgentFrameworkExecutor,
        request: Any,
    ) -> AsyncGenerator[str]:
        """Wrap the parent stream and persist the completed turn."""
        completed_response: dict[str, Any] | None = None

        async for chunk in super()._stream_execution(executor, request):
            if chunk.startswith("data: {") and "response.completed" in chunk:
                try:
                    event = json.loads(chunk.removeprefix("data: ").strip())
                    if event.get("type") == "response.completed":
                        completed_response = event.get("response")
                except (json.JSONDecodeError, AttributeError):
                    pass
            yield chunk

        try:
            conversation_id: str | None = request._get_conversation_id()
        except Exception:
            return

        if conversation_id:
            user_input = _extract_user_input(request.input)
            self._persistence.persist_turn(
                conversation_id,
                user_input=user_input,
                response=completed_response,
            )
            log.debug("Persisted thread", {"conversationId": conversation_id})


def _extract_user_input(input_data: Any) -> str:
    """Extract the user's text from the request input."""
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, list):
        for item in input_data:
            if isinstance(item, dict):
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "input_text":
                        return str(content.get("text", ""))
    return ""


def main() -> None:
    """Build agents and launch the DevUI."""
    config = settings.Settings()
    logger_mod.configure_logging(config.log_level)

    persistence_store = store.FileBackedConversationStore(_THREADS_DIR)
    log.info("Persisting threads", {"path": str(_THREADS_DIR)})

    # Build the agent; if the API is unreachable the DevUI still starts.
    entities: list[object] = []
    try:
        agent = asyncio.run(halo_all_tools.build())
        entities.append(agent)
    except Exception:
        log.warn("Agent build failed — is the sample API running on port 3001? The DevUI will start without tools.")

    server = _PersistingDevServer(
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
