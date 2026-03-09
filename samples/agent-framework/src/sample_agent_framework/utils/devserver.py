# SPDX-License-Identifier: Apache-2.0

"""PersistingDevServer — DevServer subclass with thread persistence."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from agent_framework_devui import _server

from sample_agent_framework import store

_logger = logging.getLogger(__name__)


def extract_user_input(input_data: Any) -> str:
    """Extract the user's text from the request input.

    Handles both plain string inputs and the structured list
    format used by the Agent Framework DevUI.
    """
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, list):
        for item in input_data:
            if isinstance(item, dict):
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "input_text":
                        return str(content.get("text", ""))
    return ""


class PersistingDevServer(_server.DevServer):
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
            user_input = extract_user_input(request.input)
            self._persistence.persist_turn(
                conversation_id,
                user_input=user_input,
                response=completed_response,
            )
            _logger.debug("Persisted thread for conversation %s", conversation_id)
