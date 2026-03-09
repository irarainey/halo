# SPDX-License-Identifier: Apache-2.0

"""HALO all-tools agent — discovers every tool from the sample API."""

from __future__ import annotations

import logging

import agent_framework
from agent_framework import azure

import halo_fastapi
from sample_agent import settings as settings_mod
from sample_agent import tools as tools_mod

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a set of API tools. "
    "Use the tools to answer the user's questions. "
    "Always cite which tool you used when presenting results."
)


async def build() -> agent_framework.Agent:
    """Discover HALO tools and build the all-tools agent."""
    settings = settings_mod.Settings()
    log = logging.getLogger(__name__)

    # 1. Discover HALO tools from the sample API.
    domain = settings.api_base_url.split("://")[-1].split("/")[0]
    plugin = halo_fastapi.HttpPlugin(
        base_url=settings.api_base_url,
        credentials={
            domain: {"type": "bearer", "value": settings.api_token},
        },
    )
    await plugin.discover()

    # 2. Convert HALO schemas to Agent Framework FunctionTools.
    halo_tools = await tools_mod.create_tools(plugin)
    log.info("Loaded %d HALO tool(s)", len(halo_tools))

    # 3. Create the Azure OpenAI chat client and agent.
    client = azure.AzureOpenAIChatClient(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        deployment_name=settings.azure_openai_deployment,
        api_version=settings.openai_api_version,
    )
    return agent_framework.Agent(
        client=client,
        name="halo-all-tools",
        instructions=SYSTEM_PROMPT,
        tools=halo_tools,
    )
