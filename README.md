# HALO — HTTP API Language for Operations

**Self-describing APIs for LLM agents — without MCP.**

HALO is a lightweight protocol convention that lets any HTTP API describe itself to LLM agents using the standard `OPTIONS` verb and a custom `Accept: application/llm+json` header. No registry, no sidecar process, no proxy layer — just the API describing itself.

This repository contains:

- **HALO Protocol Specification** — the full language and platform agnostic protocol spec ([halo-specification.md](halo-specification.md))
- **`halo-fastapi`** — a Python package providing a FastAPI server-side plugin (`HaloRegister`), an agent-side client (`HaloClient`), and framework adapters for Microsoft Agent Framework (`HaloAgentFrameworkAdapter`) and Semantic Kernel (`HaloSemanticKernelAdapter`)
- **Sample API** — a FastAPI server implementing HALO-compliant endpoints across four domains
- **Sample Agent (Agent Framework)** — an LLM agent with browser-based DevUI using Microsoft Agent Framework
- **Sample Agent (Semantic Kernel)** — an LLM agent with interactive CLI chat using Semantic Kernel

## How It Works

```
1. OPTIONS /                     → discover all available tools
2. OPTIONS /api/payments/charge  → fetch full schema for a specific tool
3. POST /api/payments/charge     → call the API directly — no proxy
```

An LLM agent sends `OPTIONS /` with `Accept: application/llm+json` to get a manifest of all available tools — their names, descriptions, and tags. When it selects a tool, it sends `OPTIONS` to that specific endpoint to get the full schema. Then it calls the real endpoint directly.

Tools can be filtered by tag (`OPTIONS /?tags=payments`) so agents only discover what is relevant to their task.

### Schema Response Example

```json
{
  "description": "Charge a payment method for a given amount",
  "call":    { "method": "POST", "url": "/api/payments/charge" },
  "auth":    { "type": "bearer", "scopes": ["payments:write"] },
  "input":   {
    "amount":      { "type": "number", "required": true },
    "currency":    { "type": "string", "enum": ["GBP", "USD", "EUR"] },
    "customer_id": { "type": "string", "required": true }
  },
  "output":  { "charge_id": { "type": "string" }, "status": { "type": "string" } },
  "why":     "Use to charge a customer immediately. Prefer /authorise for pre-auth flows.",
  "effects": { "reversible": true, "undo": "/api/payments/refund" },
  "tags":    ["payments", "write"]
}
```

## Key Features

- **Zero structural drift** — structural fields (inputs, outputs, types, auth) are derived from the same code that handles requests. LLM-native fields (`why`, `tags`, `effects`) are hand-written but co-located with the model.
- **Tag-filtered discovery** — agents discover only the tools relevant to their task via `OPTIONS /?tags=payments`.
- **Auth-aware scoping** — pass a token with `OPTIONS /` and the manifest reflects only what those credentials permit.
- **Lazy loading** — full schemas are fetched only when the agent selects a tool, keeping token costs low.
- **Direct call path** — no proxy layer. Agent calls the API directly. Two hops: agent → API.
- **Credential injection** — `HaloClient` injects bearer tokens, API keys, or basic auth from a credential map at call time.
- **Retry with backoff** — `HaloClient` retries failed requests with exponential backoff on 429 and 5xx responses.

## Installation

```bash
uv add halo-fastapi
```

## Server Usage (FastAPI)

A single line makes every route HALO-compliant:

```python
from halo_fastapi import HaloRegister
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")
HaloRegister(app)  # registers OPTIONS handlers automatically
```

Input/output schemas, auth requirements, and descriptions are all derived from your existing Pydantic models, route decorators, and dependency injection — no extra configuration needed. LLM-native fields like `why`, `tags`, and `effects` can be added via `json_schema_extra` on your Pydantic models.

## Client Usage (Agent Adapter)

```python
from halo_fastapi import HaloClient

plugin = await HaloClient(
    base_url="https://api.example.com",
    bearer_token=os.getenv("API_KEY"),
).discover(tags=["payments"])

# Fetch a single tool schema
schema = await plugin.get_tool("/api/payments/charge")

# Invoke a tool directly
result = await plugin.invoke("/api/payments/charge", body={"amount": 1000, "currency": "GBP", "customer_id": "cust_123"})
```

## What HALO Replaces

| Before | With HALO |
|---|---|
| MCP server process | OPTIONS handler inside the existing API |
| Tool registry | The API is the registry |
| Schema drift | Structural fields cannot drift — derived from code |
| Proxy layer / extra hop | Agent calls the API directly |
| Static tool definitions | Dynamic discovery via OPTIONS |
| Upfront token cost | Lazy, tag-filtered loading |

## Specification

The full protocol specification is in [halo-specification.md](halo-specification.md). The protocol is language and platform agnostic — any HTTP server in any language can implement HALO.

## Running the Samples

The repository includes a dev container with all tooling pre-configured. Open in VS Code with the Dev Containers extension.

### Poe tasks

| Command | Description |
|---|---|
| `poe api` | Start the sample API on port 3010 |
| `poe maf` | Start the Agent Framework DevUI (requires API) |
| `poe sk` | Start the Semantic Kernel CLI chat (requires API) |
| `poe sync:maf` | Sync dependencies for Agent Framework |
| `poe sync:sk` | Sync dependencies for Semantic Kernel |
| `poe test` | Run unit tests |
| `poe lint` | Run ruff and mypy |
| `poe format` | Auto-format code |
| `poe build` | Build the `halo-fastapi` package |

### VS Code launch profiles

| Profile | Description |
|---|---|
| **Sample API + Agent Framework** | Starts both; syncs MAF dependencies first |
| **Sample API + Semantic Kernel** | Starts both; syncs SK dependencies first |

> **Note:** The Agent Framework and Semantic Kernel samples have conflicting transitive dependencies and cannot be installed simultaneously. Use `poe sync:maf` or `poe sync:sk` to switch between them.

## Repository Structure

```text
halo/
├── halo-specification.md      # Full protocol specification (CC BY 4.0)
├── halo-fastapi/              # Python reference implementation (Apache 2.0)
│   └── src/halo_fastapi/
│       ├── _schema.py         # HaloRegister server-side plugin
│       ├── _client.py         # HaloClient client-side HTTP adapter
│       ├── _types.py          # Pydantic models for HALO schema types
│       ├── _constants.py      # Shared constants (content type, defaults)
│       └── adapters/
│           ├── _agent_framework_adapter.py  # Agent Framework integration
│           └── _semantic_kernel_adapter.py  # Semantic Kernel integration
├── samples/                   # Sample applications
│   ├── api/                   # HALO-compliant demo API
│   │   ├── data/              # JSON data files (weather, books, inventory, employees)
│   │   └── src/sample_api/
│   ├── agent-framework/       # Microsoft Agent Framework sample
│   │   └── src/sample_agent_framework/
│   └── semantic-kernel/       # Semantic Kernel sample
│       └── src/sample_semantic_kernel/
```

## Licence

- **HALO Protocol Specification** ([halo-specification.md](halo-specification.md)): [CC BY 4.0](LICENSE-SPECIFICATION)
- **All source code**: [Apache 2.0](LICENSE)