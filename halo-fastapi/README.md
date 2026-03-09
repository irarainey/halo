# halo-fastapi

The Python reference implementation of the [HALO protocol](../halo-specification.md) — a server-side FastAPI plugin and an agent-side HTTP client.

## What It Does

**Server-side (`HaloDiscovery`)** — A single line added to any FastAPI application makes every route HALO-compliant. The plugin introspects existing routes, Pydantic models, and dependency injection at startup to automatically generate `application/llm+json` schemas served via `OPTIONS` handlers.

**Client-side (`HttpPlugin`)** — An HTTP client that discovers and consumes any HALO-compliant API. Handles root manifest discovery, per-route schema fetching with caching, credential injection (bearer, API key, basic), and retry with exponential backoff.

## Installation

```bash
uv add halo-fastapi
```

## Server Usage

```python
from halo_fastapi import HaloDiscovery
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")
HaloDiscovery(app)
```

Everything is derived automatically from your existing route definitions, Pydantic models, docstrings, and dependency injection. LLM-native fields (`why`, `tags`, `effects`) can be added via `json_schema_extra` on your Pydantic models.

### Auth Detection

`HaloDiscovery` walks the FastAPI dependency tree and maps security classes to HALO auth shapes:

| FastAPI Security Class | HALO Auth Type |
|---|---|
| `HTTPBearer` | `bearer` |
| `HTTPBasic` | `basic` |
| `APIKeyHeader` | `apikey` (with custom header name) |
| `OAuth2PasswordBearer` | `oauth` (with `tokenUrl` and `scopes`) |

## Client Usage

```python
from halo_fastapi import HttpPlugin

plugin = await HttpPlugin(
    base_url="https://api.example.com",
    credentials={"api.example.com": {"type": "bearer", "value": os.getenv("API_KEY")}}
).discover(tags=["payments"])

# Fetch a single tool schema (cached after first call)
schema = await plugin.get_tool("/api/payments/charge")

# Invoke a tool — credentials injected automatically
result = await plugin.invoke("/api/payments/charge", body={"amount": 1000})
```

### Retry Behaviour

`HttpPlugin` retries failed requests with exponential backoff on connection errors, HTTP 429, and 5xx responses. Defaults: 5 retries, 0.5s base delay, 30s max delay — configurable via constructor parameters.

## Licence

[Apache 2.0](../LICENSE)
