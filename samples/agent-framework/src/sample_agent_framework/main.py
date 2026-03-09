# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
import pathlib
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from agent_framework_devui import _server

from sample_agent_framework import settings, store
from sample_agent_framework.agents import halo_all_tools
from sample_agent_framework.utils import logger

_THREADS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / ".threads"

log = logger.create_logger("Server")


class _PersistingDevServer(_server.DevServer):
    """DevServer that persists conversation turns to disk.

    The canonical persist happens at the end of ``_stream_execution``
    by capturing the ``response.completed`` SSE event which contains
    the full agent output in OpenAI format.
    """

    def __init__(
        self,
        persistence: store.FileBackedConversationStore,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._persistence = persistence

    # -- post-stream persistence ---------------------------------------------

    async def _stream_execution(  # type: ignore[override]
        self,
        executor: _server.AgentFrameworkExecutor,
        request: Any,
    ) -> AsyncGenerator[str]:
        """Wrap the parent SSE stream and persist the completed turn.

        The ``response.completed`` SSE event contains the full agent
        response in standard OpenAI format.  We capture it and pass
        it to the store so the thread file records every turn with
        both the user input and agent output.
        """
        completed_response: dict[str, Any] | None = None

        async for chunk in super()._stream_execution(executor, request):
            # Capture the response.completed event payload.
            if chunk.startswith("data: {") and "response.completed" in chunk:
                try:
                    event = json.loads(chunk.removeprefix("data: ").strip())
                    if event.get("type") == "response.completed":
                        completed_response = event.get("response")
                except (json.JSONDecodeError, AttributeError):
                    pass
            yield chunk

        # Persist the turn with the full response.
        try:
            conversation_id: str | None = request._get_conversation_id()
        except Exception:
            return

        if conversation_id:
            user_input = ""
            if isinstance(request.input, str):
                user_input = request.input
            elif isinstance(request.input, list):
                for item in request.input:
                    if isinstance(item, dict):
                        for content in item.get("content", []):
                            if isinstance(content, dict) and content.get("type") == "input_text":
                                user_input = content.get("text", "")
                                break
                    if user_input:
                        break

            self._persistence.persist_turn(
                conversation_id,
                user_input=user_input,
                response=completed_response,
            )
            log.debug("Persisted thread", {"conversationId": conversation_id})


def main() -> None:
    """Build agents and launch the DevUI."""
    config = settings.Settings()
    logger.configure_logging(config.log_level)

    all_tools_agent = asyncio.run(halo_all_tools.build())

    persistence_store = store.FileBackedConversationStore(_THREADS_DIR)
    log.info("Persisting threads", {"path": str(_THREADS_DIR)})

    server = _PersistingDevServer(
        persistence=persistence_store,
        port=8080,
    )
    server.register_entities([all_tools_agent])
    app = server.get_app()

    log.section("HALO Agent Framework Sample")
    log.info("Starting DevUI", {"port": server.port})
    uvicorn.run(app, host="127.0.0.1", port=server.port, log_level="info")


if __name__ == "__main__":
    main()
