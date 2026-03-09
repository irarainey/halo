# HALO — HTTP API Language for Operations

**Self-describing APIs for LLM agents — without MCP.**

HALO is a lightweight protocol convention that lets any HTTP API describe itself to LLM agents using the standard `OPTIONS` verb and a custom `Accept: application/llm+json` header. No registry, no sidecar process, no proxy layer — just the API describing itself.

This repository contains:

- **HALO Protocol Specification** — the full language and platform agnostic protocol spec ([halo-specification.md](halo-specification.md))
- **`halo-fastapi`** — a Python package providing a FastAPI server-side plugin (`HaloRegister`) and an agent-side HTTP client (`HttpPlugin`) with discovery, schema caching, credential injection, and retry
- **Sample API** — a FastAPI server implementing HALO-compliant endpoints across four domains
- **Sample Agents** — an LLM agent application using Microsoft Agent Framework and DevUI to consume the sample API via HALO

## How It Works

```
1. OPTIONS /?tags=payments       → discover relevant tools (cheap manifest)
2. OPTIONS /api/payments/charge  → fetch full schema (lazy, on demand)
3. POST /api/payments/charge     → call the API directly — no proxy
```

An LLM agent sends `OPTIONS` with `Accept: application/llm+json` to any endpoint. The API returns a compact JSON schema describing what it does, how to call it, what auth it needs, and what side effects it has. The agent then calls the real endpoint directly.

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

- **Zero drift** — the schema is derived from the same code that handles requests. If the API changes, the schema changes atomically.
- **Tag-filtered discovery** — agents discover only the tools relevant to their task via `OPTIONS /?tags=payments`.
- **Auth-aware scoping** — pass a token with `OPTIONS /` and the manifest reflects only what those credentials permit.
- **Lazy loading** — full schemas are fetched only when the agent selects a tool, keeping token costs low.
- **Direct call path** — no proxy layer. Agent calls the API directly. Two hops: agent → API.
- **Credential injection** — `HttpPlugin` injects bearer tokens, API keys, or basic auth from a credential map at call time.
- **Retry with backoff** — `HttpPlugin` retries failed requests with exponential backoff on 429 and 5xx responses.

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
from halo_fastapi import HttpPlugin

plugin = await HttpPlugin(
    base_url="https://api.example.com",
    credentials={"api.example.com": {"type": "bearer", "value": os.getenv("API_KEY")}}
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
| Schema drift | Structurally impossible |
| Proxy layer / extra hop | Agent calls the API directly |
| Static tool definitions | Dynamic discovery via OPTIONS |
| Upfront token cost | Lazy, tag-filtered loading |

## Specification

The full protocol specification is in [halo-specification.md](halo-specification.md). The protocol is language and platform agnostic — any HTTP server in any language can implement HALO.

## Repository Structure

```text
halo/
├── halo-specification.md      # Full protocol specification (CC BY 4.0)
├── halo-fastapi/              # Python reference implementation (Apache 2.0)
│   └── src/halo_fastapi/
│       ├── _schema.py         # HaloRegister server-side plugin
│       ├── _plugin.py         # HttpPlugin client-side adapter
│       └── _types.py          # Pydantic models for HALO schema types
├── sample-api/                # HALO-compliant demo API
│   ├── data/                  # JSON data files (weather, books, inventory, employees)
│   └── src/sample_api/
└── sample-agents/             # Agent consuming the sample API via HALO
    └── src/sample_agent/
```

## Licence

- **HALO Protocol Specification** ([halo-specification.md](halo-specification.md)): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **halo-fastapi Reference Implementation** (all source code): [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)