# SPDX-License-Identifier: Apache-2.0

"""HaloSemanticKernelAdapter — Semantic Kernel adapter for HALO tools.

Converts HALO tool schemas discovered by :class:`HaloClient` into a
Semantic Kernel ``KernelPlugin`` containing ``KernelFunction`` instances.

Requires ``semantic-kernel`` to be installed::

    uv pip install semantic-kernel
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Annotated, Any

from halo_fastapi import _client, _types

logger = logging.getLogger(__name__)


class HaloSemanticKernelAdapter:
    """Adapter that converts HALO tools into a Semantic Kernel KernelPlugin.

    Usage::

        from halo_fastapi import HaloClient, HaloSemanticKernelAdapter

        client = HaloClient(base_url="https://api.example.com", bearer_token="...")
        await client.discover(tags=["payments"])

        adapter = HaloSemanticKernelAdapter(client)
        plugin = await adapter.create_plugin()

        kernel.add_plugin(plugin)
    """

    def __init__(self, client: _client.HaloClient) -> None:
        """Initialise the adapter.

        Args:
            client: A :class:`HaloClient` that has already called
                ``discover()``.
        """
        self._client = client

    async def create_plugin(self, plugin_name: str = "halo") -> Any:
        """Create a ``KernelPlugin`` with one ``KernelFunction`` per discovered tool.

        Args:
            plugin_name: Name for the resulting plugin.

        Returns:
            A ``KernelPlugin`` ready to pass to ``kernel.add_plugin()``.

        Raises:
            ImportError: If ``semantic-kernel`` is not installed.
        """
        try:
            from semantic_kernel.functions import KernelFunction, KernelPlugin, kernel_function  # noqa: important[misplaced-import]
        except ImportError as exc:
            msg = "semantic-kernel is required for HaloSemanticKernelAdapter. Install with: uv pip install semantic-kernel"
            raise ImportError(msg) from exc

        functions: list[KernelFunction] = []

        for entry in self._client.tools:
            schema = await self._client.get_tool(entry.url)
            path = entry.url

            func = _make_invoke_func(self._client, path, schema, kernel_function)
            kf = KernelFunction.from_method(func, plugin_name=plugin_name)
            functions.append(kf)
            logger.debug("Created SK function: %s (%s)", kf.name, path)

        logger.info("Built SK plugin '%s' with %d function(s)", plugin_name, len(functions))
        return KernelPlugin(name=plugin_name, functions=functions)


def _make_invoke_func(
    client: _client.HaloClient,
    path: str,
    schema: _types.HaloSchema,
    kernel_function_decorator: Any,
) -> Any:
    """Create a ``@kernel_function``-decorated async callable for a HALO tool.

    Builds a function with explicit keyword parameters matching the
    HALO input schema so Semantic Kernel can map LLM arguments
    correctly (instead of bundling them into a single ``kwargs`` dict).
    """
    name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    description = schema.why or schema.description or name

    # Build the parameter list from the HALO input schema.
    param_names = list(schema.input.keys())
    param_descriptions = {p: schema.input[p].get("description", p) for p in param_names}

    @kernel_function_decorator(name=name, description=description)
    async def _invoke(**kwargs: Any) -> Annotated[str, "JSON result"]:
        # SK may nest args under a "kwargs" key — unwrap if so.
        body = kwargs.get("kwargs", kwargs) if "kwargs" in kwargs else kwargs
        result = await client.invoke(path, body=body)
        return json.dumps(result)

    # Patch the function's annotations so SK discovers the real parameters.
    annotations: dict[str, Any] = {}
    for p in param_names:
        annotations[p] = Annotated[str, param_descriptions[p]]
    annotations["return"] = Annotated[str, "JSON result"]
    _invoke.__annotations__ = annotations

    # Update the signature so SK introspects typed parameters.
    params = [inspect.Parameter(p, inspect.Parameter.KEYWORD_ONLY, default=None) for p in param_names]
    _invoke.__signature__ = inspect.Signature(params, return_annotation=Annotated[str, "JSON result"])  # type: ignore[attr-defined]

    return _invoke
