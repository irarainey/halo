# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from agent_framework_devui import _server

from sample_agent import settings as settings_mod
from sample_agent import store as store_mod
from sample_agent.agents import halo_all_tools
from sample_agent.utils import logger

_THREADS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / ".threads"

_log = logging.getLogger(__name__)


class _PersistingDevServer(_server.DevServer):
    """DevServer that injects a file-backed conversation store.

    The canonical persist happens at the end of ``_stream_execution``
    by capturing the ``response.completed`` SSE event which contains
    the full agent output in OpenAI format.
    """

    def __init__(
        self,
        store: store_mod.FileBackedConversationStore,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._store = store

    async def _ensure_executor(
        self,
    ) -> _server.AgentFrameworkExecutor:
        """Initialise executor with file-backed store."""
        if self.executor is None:  # type: ignore[has-type]
            entity_discovery = _server.EntityDiscovery(
                self.entities_dir,  # type: ignore[arg-type]
            )
            message_mapper = _server.MessageMapper()
            self.executor = _server.AgentFrameworkExecutor(  # type: ignore[assignment,has-type]
                entity_discovery,
                message_mapper,
                conversation_store=self._store,
            )
            await self.executor.discover_entities()  # type: ignore[attr-defined]

            if self._pending_entities:  # type: ignore[has-type]
                discovery = self.executor.entity_discovery  # type: ignore[attr-defined]
                for entity in self._pending_entities:  # type: ignore[has-type]
                    info = await discovery.create_entity_info_from_object(
                        entity,
                        source="in_memory",
                    )
                    discovery.register_entity(
                        info.id,
                        info,
                        entity,
                    )
                self._pending_entities = None

        return self.executor  # type: ignore[return-value]

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
        conversation_id: str | None = request._get_conversation_id()
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

            self._store.persist_turn(
                conversation_id,
                user_input=user_input,
                response=completed_response,
            )
            _log.debug("Persisted thread %s after stream completed", conversation_id)


def main() -> None:
    """Build agents and launch the DevUI."""
    settings = settings_mod.Settings()
    logger.configure_logging(settings.log_level)
    log = logging.getLogger(__name__)

    agent = asyncio.run(halo_all_tools.build())

    store = store_mod.FileBackedConversationStore(_THREADS_DIR)
    log.info("Persisting threads to %s", _THREADS_DIR)

    server = _PersistingDevServer(
        store=store,
        port=8080,
    )
    server._pending_entities = [agent]  # type: ignore[assignment]
    app = server.get_app()

    log.info("Starting DevUI on port 8080")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


if __name__ == "__main__":
    main()
