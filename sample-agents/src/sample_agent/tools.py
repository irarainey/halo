# SPDX-License-Identifier: Apache-2.0

"""Converts HALO tool schemas into Agent Framework FunctionTool instances."""

from __future__ import annotations

import json
import logging
from typing import Any

import agent_framework

import halo_fastapi

logger = logging.getLogger(__name__)


def _build_input_model(schema: halo_fastapi.HaloSchema) -> dict[str, Any]:
    """Convert HALO input fields to a JSON Schema dict for FunctionTool."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, spec in schema.input.items():
        prop: dict[str, Any] = {}
        if "type" in spec:
            prop["type"] = spec["type"]
        if "description" in spec:
            prop["description"] = spec["description"]
        if "enum" in spec:
            prop["enum"] = spec["enum"]
        properties[name] = prop
        if spec.get("required"):
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


async def create_tools(plugin: halo_fastapi.HttpPlugin) -> list[agent_framework.FunctionTool]:
    """Discover HALO endpoints and return a FunctionTool for each one.

    Each tool, when invoked by the LLM, fetches the full schema (lazy),
    then calls the real API endpoint via ``plugin.invoke()``.
    """
    tools: list[agent_framework.FunctionTool] = []
    for entry in plugin.tools:
        schema = await plugin.get_tool(entry.url)
        path = entry.url

        async def _invoke(path: str = path, **kwargs: Any) -> str:
            logger.debug("Tool invoked: %s with %s", path, kwargs)
            result = await plugin.invoke(path, body=kwargs)
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
