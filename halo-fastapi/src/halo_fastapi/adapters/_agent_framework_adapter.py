# SPDX-License-Identifier: Apache-2.0

"""HaloAgentFrameworkAdapter — Microsoft Agent Framework adapter for HALO tools.

Converts HALO tool schemas discovered by :class:`HaloClient` into
``agent_framework.FunctionTool`` instances that can be passed directly
to an ``Agent``.

Requires the ``agent-framework`` optional extra::

    uv add halo-fastapi[agent-framework]
"""

from __future__ import annotations

import json
import logging
from typing import Any

from halo_fastapi import _client, _types

logger = logging.getLogger(__name__)


def _build_input_model(schema: _types.HaloSchema) -> dict[str, Any]:
    """Convert HALO input fields to a JSON Schema dict for FunctionTool."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, spec in schema.input.items():
        prop = {k: v for k, v in spec.items() if k != "required"}
        properties[name] = prop
        if spec.get("required"):
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class HaloAgentFrameworkAdapter:
    """Adapter that converts HALO tools into Microsoft Agent Framework FunctionTools.

    Usage::

        from halo_fastapi import HaloClient, HaloAgentFrameworkAdapter

        client = HaloClient(base_url="https://api.example.com", credentials={...})
        await client.discover(tags=["payments"])

        plugin = HaloAgentFrameworkAdapter(client)
        tools = await plugin.create_tools()

        agent = Agent(client=chat_client, tools=tools, ...)
    """

    def __init__(self, client: _client.HaloClient) -> None:
        """Initialise the plugin.

        Args:
            client: A :class:`HaloClient` that has already called
                ``discover()``.
        """
        self._client = client

    async def create_tools(self) -> list[Any]:
        """Create an ``agent_framework.FunctionTool`` for each discovered tool.

        Returns:
            List of ``FunctionTool`` instances ready to pass to an ``Agent``.

        Raises:
            ImportError: If ``agent-framework-core`` is not installed.
        """
        try:
            import agent_framework
        except ImportError as exc:
            msg = "agent-framework-core is required for HaloAgentFrameworkAdapter. Install with: uv add halo-fastapi[agent-framework]"
            raise ImportError(msg) from exc

        tools: list[agent_framework.FunctionTool] = []
        for entry in self._client.tools:
            schema = await self._client.get_tool(entry.url)
            path = entry.url

            async def _invoke(
                _path: str = path,
                **kwargs: Any,
            ) -> str:
                logger.debug("Tool invoked: %s with %s", _path, kwargs)
                result = await self._client.invoke(_path, body=kwargs)
                return json.dumps(result)

            tool = agent_framework.FunctionTool(
                name=entry.name or path.strip("/").replace("/", "_"),
                description=schema.why or schema.description,
                func=_invoke,
                input_model=_build_input_model(schema),
            )
            tools.append(tool)
            logger.debug("Created tool: %s (%s)", tool.name, path)
        return tools
