# SPDX-License-Identifier: Apache-2.0

"""File-backed conversation store for thread persistence."""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from agent_framework_devui import _conversations

_logger = logging.getLogger(__name__)


class FileBackedConversationStore(_conversations.InMemoryConversationStore):
    """Conversation store that persists threads as JSON.

    Extends the in-memory store with write-through JSON
    persistence.  Each conversation is saved to a separate file
    under the configured storage directory.

    The framework's ``InMemoryHistoryProvider.save_messages`` never
    fires in streaming mode because the DevUI iterates the
    ``ResponseStream`` with ``async for`` rather than using
    ``async with`` or calling ``get_final_response()``, so the
    stream's ``_post_hook`` is never invoked.

    Instead, the authoritative conversation record comes from the
    ``response.completed`` SSE event emitted at the end of every
    turn.  ``_PersistingDevServer._stream_execution`` captures
    that event and passes it to :meth:`persist_turn`.
    """

    def __init__(self, storage_dir: pathlib.Path) -> None:
        """Initialise the store.

        Args:
            storage_dir: Directory for conversation JSON files.
        """
        super().__init__()
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    # -- mutating overrides --------------------------------------------------

    def create_conversation(
        self,
        metadata: dict[str, str] | None = None,
        conversation_id: str | None = None,
    ) -> _conversations.Conversation:
        """Create a conversation and persist it."""
        conv = super().create_conversation(metadata, conversation_id)
        self._write(
            conv.id,
            {
                "id": conv.id,
                "created_at": conv.created_at,
                "metadata": conv.metadata or {},
                "turns": [],
            },
        )
        _logger.debug("Created conversation %s", conv.id)
        return conv

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> _conversations.ConversationDeletedResource:
        """Delete a conversation and remove its JSON file."""
        result = super().delete_conversation(conversation_id)
        path = self._storage_dir / f"{conversation_id}.json"
        path.unlink(missing_ok=True)
        _logger.debug("Deleted conversation %s", conversation_id)
        return result

    # -- serialisation -------------------------------------------------------

    def persist_turn(
        self,
        conversation_id: str,
        *,
        user_input: str,
        response: dict[str, Any] | None = None,
    ) -> None:
        """Append a completed turn to the thread file.

        Args:
            conversation_id: Conversation to update.
            user_input: The user's message text for this turn.
            response: The ``response`` payload from the
                ``response.completed`` SSE event (OpenAI format).
        """
        path = self._storage_dir / f"{conversation_id}.json"
        if path.exists():
            thread = json.loads(path.read_text(encoding="utf-8"))
        else:
            conv_data = self._conversations.get(conversation_id, {})
            thread = {
                "id": conversation_id,
                "created_at": conv_data.get("created_at"),
                "metadata": conv_data.get("metadata", {}),
                "turns": [],
            }

        thread.setdefault("turns", []).append(
            {
                "input": user_input,
                "response": response,
            }
        )
        self._write(conversation_id, thread)
        _logger.debug(
            "Persisted turn %d for conversation %s",
            len(thread["turns"]),
            conversation_id,
        )

    def _write(self, conversation_id: str, payload: dict[str, Any]) -> None:
        """Write a payload dict to the thread JSON file."""
        path = self._storage_dir / f"{conversation_id}.json"
        path.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
