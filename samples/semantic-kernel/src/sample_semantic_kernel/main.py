# SPDX-License-Identifier: Apache-2.0

"""HALO Semantic Kernel sample — interactive CLI chat."""

from __future__ import annotations

import asyncio
import logging

import semantic_kernel
from rich import console as console_mod
from rich import markdown
from semantic_kernel.connectors.ai import function_choice_behavior as function_choice_behavior_mod
from semantic_kernel.connectors.ai import open_ai
from semantic_kernel.contents import chat_history as chat_history_mod

import halo_fastapi
from sample_semantic_kernel import settings as settings_mod

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a set of API tools. "
    "Use the tools to answer the user's questions. "
    "Always cite which tool you used when presenting results."
)


async def _run() -> None:
    """Set up the kernel and run the interactive chat loop."""
    config = settings_mod.Settings()
    logging.basicConfig(level=config.log_level, format="%(levelname)s %(name)s: %(message)s")

    # Suppress noisy loggers so the chat output stays clean.
    for name in ("httpx", "semantic_kernel", "openai", "azure"):
        logging.getLogger(name).setLevel(logging.WARNING)

    console = console_mod.Console()

    # 1. Discover HALO tools from the sample API.
    console.print("[dim]Connecting to HALO API...[/dim]")
    client = halo_fastapi.HaloClient(
        base_url=config.api_base_url,
        bearer_token=config.api_token,
    )
    try:
        await client.discover()
    except Exception as exc:
        console.print(f"[red bold]Failed to connect to API:[/red bold] {exc}")
        console.print(f"[dim]Is the sample API running at {config.api_base_url}?[/dim]")
        return

    # 2. Build a Semantic Kernel plugin from the discovered tools.
    adapter = halo_fastapi.HaloSemanticKernelAdapter(client)
    plugin = await adapter.create_plugin()
    tool_names = list(plugin.functions.keys())
    console.print(f"[green]Loaded {len(tool_names)} tool(s):[/green] {', '.join(tool_names)}")

    # 3. Set up the kernel with Azure OpenAI.
    kernel = semantic_kernel.Kernel()

    if not config.azure_openai_endpoint or not config.azure_openai_deployment:
        console.print("[red bold]Azure OpenAI not configured.[/red bold]")
        console.print("[dim]Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT in .env[/dim]")
        await client.close()
        return

    service = open_ai.AzureChatCompletion(
        service_id="chat",
        endpoint=config.azure_openai_endpoint,
        api_key=config.azure_openai_api_key,
        deployment_name=config.azure_openai_deployment,
        api_version=config.openai_api_version,
    )
    kernel.add_service(service)
    kernel.add_plugin(plugin)

    # 4. Configure execution settings with auto function calling.
    execution_settings = open_ai.AzureChatPromptExecutionSettings(
        service_id="chat",
        function_choice_behavior=function_choice_behavior_mod.FunctionChoiceBehavior.Auto(),
    )

    history = chat_history_mod.ChatHistory(system_message=SYSTEM_PROMPT)

    # 5. Interactive chat loop.
    console.print()
    console.rule("[bold]HALO Semantic Kernel Chat[/bold]")
    console.print("[dim]Type your message and press Enter. Type 'quit' or 'exit' to stop.[/dim]")
    console.print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        history.add_user_message(user_input)

        try:
            result = await service.get_chat_message_contents(
                chat_history=history,
                settings=execution_settings,
                kernel=kernel,
            )
            response = str(result[0]) if result else ""
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            continue

        history.add_assistant_message(response)
        console.print()
        console.print("[bold green]Assistant:[/bold green]")
        console.print(markdown.Markdown(response))
        console.print()

    await client.close()
    console.print("[dim]Goodbye![/dim]")


def main() -> None:
    """Entry point for the CLI."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
