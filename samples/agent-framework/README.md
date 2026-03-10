# Sample: Agent Framework

LLM agent application that consumes the [sample API](../api) via the HALO protocol using `halo-fastapi` and [Microsoft Agent Framework](https://github.com/microsoft/agents).

The agent runs inside an Agent Framework DevUI server, providing a browser-based chat interface at `http://localhost:8080`.

## Agents

### halo-all-tools

Discovers every tool exposed by the sample API and makes them all available to the LLM. Uses Azure OpenAI as the chat backend.

### halo-filter-tools

Discovers only the tools matching the tags configured in `HALO_TAGS` and exposes those to the LLM. This reduces the number of tools in the LLM context, improving token efficiency and agent focus. Uses Azure OpenAI as the chat backend.

## Running

The Agent Framework sample has a dependency conflict with the Semantic Kernel sample (`azure-ai-projects` version mismatch), so it is excluded from the main workspace. Dependencies are installed on demand.

### Using poe tasks (recommended)

Open two VS Code integrated terminals:

```bash
# Terminal 1 — start the sample API
poe api

# Terminal 2 — sync MAF dependencies and start the agent
poe sync:maf
poe maf
```

You only need to run `poe sync:maf` once per session (or after a `uv sync --all-packages` which resets the venv).

### Using VS Code launch profiles

Select **Sample API + Agent Framework** from the Run and Debug dropdown and press F5. The pre-launch task automatically syncs MAF dependencies before starting.

### Manual

```bash
# Install MAF dependencies (once)
uv sync --all-packages
uv pip install -e samples/agent-framework

# Start the API in one terminal
uvicorn sample_api.main:app --reload --port 3001 --app-dir samples/api/src

# Start the agent in another terminal
cd samples/agent-framework/src
python -m sample_agent_framework.main
```

The DevUI is available at `http://localhost:8080` once the agent starts. If the sample API is not reachable, the DevUI will still start but without any tools registered.

## Configuration

Settings are managed via Pydantic Settings. The `.env` file in the repository root is loaded automatically.

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `API_BASE_URL` | `http://localhost:3001` | URL of the HALO-compliant API to consume |
| `API_TOKEN` | `halo-sample-token` | Bearer token for API authentication |
| `AZURE_OPENAI_ENDPOINT` | *(required)* | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | *(required)* | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | *(required)* | Azure OpenAI model deployment name |
| `OPENAI_API_VERSION` | `2024-12-01-preview` | Azure OpenAI API version |
| `HALO_TAGS` | `weather,books` | Comma-separated tags for the filter-tools agent |

## Thread Persistence

Conversation threads are persisted as JSON files in the `.threads/` directory (relative to the sample package root). Each conversation is saved to a separate file and updated after every turn with the user input and full agent response.

## Project Structure

```text
samples/agent-framework/
└── src/sample_agent_framework/
    ├── main.py            # DevUI server with thread persistence
    ├── settings.py        # Pydantic Settings configuration
    ├── store.py           # FileBackedConversationStore
    ├── agents/
    │   ├── halo_all_tools.py    # All-tools agent — discovers every tool
    │   └── halo_filter_tools.py # Filter-tools agent — discovers tools by tag
    └── utils/
        ├── __init__.py
        └── logger.py      # Coloured console log formatter
```

## Licence

[Apache 2.0](../../LICENSE)
