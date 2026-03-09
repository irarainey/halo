# Sample: Semantic Kernel

LLM agent CLI that consumes the [sample API](../api) via the HALO protocol using `halo-fastapi` and [Semantic Kernel](https://github.com/microsoft/semantic-kernel).

Provides an interactive command-line chat interface powered by [Rich](https://github.com/Textualize/rich).

## Running

The Semantic Kernel sample has a dependency conflict with the Agent Framework sample (`azure-ai-projects` version mismatch), so it is excluded from the main workspace. Dependencies are installed on demand.

### Using poe tasks (recommended)

Open two VS Code integrated terminals:

```bash
# Terminal 1 — start the sample API
poe api

# Terminal 2 — sync SK dependencies and start the chat
poe sync:sk
poe sk
```

You only need to run `poe sync:sk` once per session (or after a `uv sync --all-packages` which resets the venv).

### Using VS Code launch profiles

Select **Sample API + Semantic Kernel** from the Run and Debug dropdown and press F5. The pre-launch task automatically syncs SK dependencies before starting.

### Manual

```bash
# Install SK dependencies (once)
uv sync --all-packages
uv pip install -e samples/semantic-kernel

# Start the API in one terminal
uvicorn sample_api.main:app --reload --port 3001 --app-dir samples/api/src

# Start the SK chat in another terminal
cd samples/semantic-kernel/src
python -m sample_semantic_kernel.main
```

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

## How It Works

1. **Discover** — `HaloClient` calls `OPTIONS /` on the sample API to get the tool manifest
2. **Build plugin** — `HaloSemanticKernelAdapter` wraps each HALO tool as a `@kernel_function` inside a `KernelPlugin`
3. **Chat** — Semantic Kernel handles function calling automatically via `FunctionChoiceBehavior.Auto()`
4. **Invoke** — when the LLM selects a tool, the kernel function calls `HaloClient.invoke()` directly

## Project Structure

```text
samples/semantic-kernel/
└── src/sample_semantic_kernel/
    ├── main.py      # CLI chat loop with Rich
    └── settings.py  # Pydantic Settings configuration
```

## Licence

[Apache 2.0](../../LICENSE)
