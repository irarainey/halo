# Sample: Agent Framework

LLM agent application that consumes the [sample API](../api) via the HALO protocol using `halo-fastapi` and [Microsoft Agent Framework](https://github.com/microsoft/agents).

The agent runs inside an Agent Framework DevUI server, providing a browser-based chat interface at `http://localhost:8080`.

## Agents

### halo-all-tools

Discovers every tool exposed by the sample API and makes them all available to the LLM. Uses Azure OpenAI as the chat backend.

## Running

Ensure the sample API is running first, then from the repository root:

```bash
python -m sample_agent_framework.main
```

Or use the **Agent Framework** launch profile in VS Code. The **Sample API + Agent Framework** compound profile launches both together.

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
    │   └── halo_all_tools.py  # Agent builder — discovers tools and creates the agent
    └── utils/
        ├── __init__.py
        └── logger.py      # Coloured console log formatter
```

## Licence

[Apache 2.0](../../LICENSE)
