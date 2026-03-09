# SPDX-License-Identifier: Apache-2.0

"""HALO filter-tools agent — discovers tools filtered by tag."""

from __future__ import annotations

import agent_framework
from agent_framework import azure

import halo_fastapi
from sample_agent_framework import settings as settings_mod
from sample_agent_framework.utils import logger

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a filtered set of API tools. "
    "Use only the tools available to you to answer the user's questions. "
    "Always cite which tool you used when presenting results."
)


async def build(tags: list[str]) -> agent_framework.Agent:
    """Discover HALO tools filtered by tag and build the agent.

    Args:
        tags: Tags to filter discovered tools by.
    """
    settings = settings_mod.Settings()
    log = logger.create_logger("Agent")

    # 1. Discover HALO tools filtered by the requested tags.
    client = halo_fastapi.HaloClient(
        base_url=settings.api_base_url,
        bearer_token=settings.api_token,
    )
    await client.discover(tags=tags)

    # 2. Convert HALO schemas to Agent Framework FunctionTools.
    adapter = halo_fastapi.HaloAgentFrameworkAdapter(client)
    halo_tools = await adapter.create_tools()
    log.success(
        "HALO tools loaded (filtered)",
        {"count": len(halo_tools), "tags": tags},
    )

    # Close the discovery session — tools will create a fresh session
    # in uvicorn's event loop when invoked at runtime.
    await client.close()

    # 3. Create the Azure OpenAI chat client and agent.
    llm_client = azure.AzureOpenAIChatClient(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment_name=settings.azure_openai_deployment,
        api_version=settings.openai_api_version,
    )
    return agent_framework.Agent(
        client=llm_client,
        name="halo-filter-tools",
        instructions=SYSTEM_PROMPT,
        tools=halo_tools,
    )
