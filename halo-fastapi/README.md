# halo-fastapi

The Python reference implementation of the [HALO protocol](../halo-specification.md) — a server-side FastAPI plugin and an agent-side HTTP client.

## What It Does

**Server-side (`HaloRegister`)** — A single line added to any FastAPI application makes every route HALO-compliant. The plugin introspects existing routes, Pydantic models, and dependency injection at startup to automatically generate `application/llm+json` schemas served via `OPTIONS` handlers.

**Client-side (`HaloClient`)** — A client that discovers and consumes any HALO-compliant API. Handles root manifest discovery, per-route schema fetching with caching, credential injection (bearer, API key, basic), and retry with exponential backoff.

## Installation

```bash
uv add halo-fastapi
```

### Optional Extras

The framework adapters have optional dependencies that conflict with each other (`azure-ai-projects` version mismatch), so they cannot be installed in the same environment:

```bash
# Agent Framework adapter
uv add "halo-fastapi[agent-framework]"

# Semantic Kernel adapter
uv add "halo-fastapi[semantic-kernel]"
```

### Development (Monorepo)

`halo-fastapi` is a workspace member. To sync the core workspace:

```bash
uv sync --all-packages
```

The sample agent apps are excluded from the workspace due to conflicting transitive dependencies. Install them on demand:

```bash
# Agent Framework sample
uv pip install -e samples/agent-framework

# Semantic Kernel sample
uv pip install -e samples/semantic-kernel
```

## Server Usage

```python
from halo_fastapi import HaloRegister
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")
HaloRegister(app)
```

Everything is derived automatically from your existing route definitions, Pydantic models, docstrings, and dependency injection. LLM-native fields (`why`, `tags`, `effects`) can be added via `json_schema_extra` on your Pydantic models.

### Auth Detection

`HaloRegister` walks the FastAPI dependency tree and maps security classes to HALO auth shapes:

| FastAPI Security Class | HALO Auth Type |
|---|---|
| `HTTPBearer` | `bearer` |
| `HTTPBasic` | `basic` |
| `APIKeyHeader` | `apikey` (with custom header name) |
| `OAuth2PasswordBearer` | `oauth` (with `tokenUrl` and `scopes`) |

## Client Usage

```python
from halo_fastapi import HaloClient

plugin = await HaloClient(
    base_url="https://api.example.com",
    bearer_token=os.getenv("API_KEY"),
).discover(tags=["payments"])

# Fetch a single tool schema (cached after first call)
schema = await plugin.get_tool("/api/payments/charge")

# Invoke a tool — credentials injected automatically
result = await plugin.invoke("/api/payments/charge", body={"amount": 1000})
```

### Retry Behaviour

`HaloClient` retries failed requests with exponential backoff on connection errors, HTTP 429, and 5xx responses. Defaults: 5 retries, 0.5s base delay, 30s max delay — configurable via constructor parameters.

## Agent Framework Integration (Optional)

`HaloAgentFrameworkAdapter` converts discovered HALO tools into Microsoft Agent Framework `FunctionTool` instances. Install with the optional extra:

```bash
uv add "halo-fastapi[agent-framework]"
```

```python
from halo_fastapi import HaloClient, HaloAgentFrameworkAdapter

client = await HaloClient(base_url="https://api.example.com").discover()
adapter = HaloAgentFrameworkAdapter(client)
tools = await adapter.create_tools()  # list[FunctionTool]
```

`create_tools()` fetches the full schema for each discovered tool via `HaloClient.get_tool()` and builds a `FunctionTool` from the result. Schemas are cached by `HaloClient` so subsequent invocations do not repeat the OPTIONS requests.

## Semantic Kernel Integration (Optional)

`HaloSemanticKernelAdapter` converts discovered HALO tools into a Semantic Kernel `KernelPlugin`. Install with the optional extra (cannot coexist with `halo-fastapi[agent-framework]` due to transitive dependency conflicts):

```bash
uv add "halo-fastapi[semantic-kernel]"
```

```python
from halo_fastapi import HaloClient, HaloSemanticKernelAdapter

client = await HaloClient(base_url="https://api.example.com").discover()
adapter = HaloSemanticKernelAdapter(client)
plugin = await adapter.create_plugin()  # KernelPlugin

kernel.add_plugin(plugin)
```

`create_plugin()` wraps each discovered tool as a `@kernel_function`-decorated async function inside a `KernelPlugin`. Semantic Kernel handles automatic function calling when `FunctionChoiceBehavior.Auto()` is configured.

## Licence

[Apache 2.0](../LICENSE)
