# Sample Agents

LLM agent applications that consume the [sample API](../sample-api) via the HALO protocol using `halo-fastapi` and [Microsoft Agent Framework](https://github.com/microsoft/agents).

The agent runs inside an Agent Framework DevUI server, providing a browser-based chat interface at `http://localhost:8080`.

## Agents

### halo-all-tools

Discovers every tool exposed by the sample API and makes them all available to the LLM. Uses Azure OpenAI as the chat backend.

## Running

Ensure the sample API is running first, then from the repository root:

```bash
python -m sample_agent.main
```

Or use the **Sample Agent** launch profile in VS Code. The **Sample API + Agent** compound profile launches both together.

The DevUI is available at `http://localhost:8080` once the agent starts.

## Configuration

Settings are managed via Pydantic Settings. The `.env` file in the repository root is loaded automatically.

| Variable | Default | Description |
|---|---|---|
| `SAMPLE_AGENT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `api_base_url` | `http://localhost:3001` | URL of the HALO-compliant API to consume |
| `api_token` | `halo-sample-token` | Bearer token for API authentication |
| `AZURE_OPENAI_ENDPOINT` | *(required)* | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | *(required)* | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | *(required)* | Azure OpenAI model deployment name |
| `OPENAI_API_VERSION` | `2024-12-01-preview` | Azure OpenAI API version |

## Thread Persistence

Conversation threads are persisted as JSON files in the `.threads/` directory (relative to the `sample-agents` package root). Each conversation is saved to a separate file and updated after every turn with the user input and full agent response.

## Project Structure

```text
sample-agents/
└── src/sample_agent/
    ├── main.py            # DevUI server with thread persistence
    ├── settings.py        # Pydantic Settings configuration
    ├── store.py           # FileBackedConversationStore
    ├── tools.py           # Converts HALO schemas to Agent Framework FunctionTools
    ├── agents/
    │   └── halo_all_tools.py  # Agent builder — discovers tools and creates the agent
    └── utils/
        ├── __init__.py
        └── logger.py      # Coloured console log formatter
```

## Licence

[Apache 2.0](../LICENSE)
