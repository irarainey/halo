# SPDX-License-Identifier: Apache-2.0

"""HALO all-tools agent — discovers every tool from the sample API."""

from __future__ import annotations

import agent_framework
from agent_framework import azure

import halo_fastapi
from sample_agent_framework import settings as settings_mod
from sample_agent_framework.utils import logger

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a set of API tools. "
    "Use the tools to answer the user's questions. "
    "Always cite which tool you used when presenting results."
)


async def build() -> agent_framework.Agent:
    """Discover HALO tools and build the all-tools agent."""
    settings = settings_mod.Settings()
    log = logger.create_logger("Agent")

    # 1. Discover HALO tools from the sample API.
    client = halo_fastapi.HaloClient(
        base_url=settings.api_base_url,
        bearer_token=settings.api_token,
    )
    await client.discover()

    # 2. Convert HALO schemas to Agent Framework FunctionTools.
    adapter = halo_fastapi.HaloAgentFrameworkAdapter(client)
    halo_tools = await adapter.create_tools()
    log.success("HALO tools loaded", {"count": len(halo_tools)})

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
        name="halo-all-tools",
        instructions=SYSTEM_PROMPT,
        tools=halo_tools,
    )
