# halohttp

The Python reference implementation of the [HALO protocol](../halo-specification.md) — a FastAPI plugin and agent adapter package.

## What It Does

**Server-side (`LLMSchema`)** — A single line added to any FastAPI application makes every route HALO-compliant. The plugin introspects existing routes, Pydantic models, and dependency injection at startup to automatically generate `application/llm+json` schemas served via `OPTIONS` handlers.

**Client-side (`HttpPlugin`)** — An agent adapter that discovers and consumes any HALO-compliant API, with built-in framework adapters for Semantic Kernel, LangChain, LlamaIndex, and Microsoft Agent Framework.

## Installation

```bash
uv add halohttp
```

## Server Usage

```python
from halohttp import LLMSchema
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")
LLMSchema(app)
```

Everything is derived automatically from your existing route definitions, Pydantic models, docstrings, and dependency injection. LLM-native fields (`why`, `tags`, `effects`) can be added via `json_schema_extra` on your Pydantic models.

## Client Usage

```python
from halohttp import HttpPlugin

plugin = await HttpPlugin(
    base_url="https://api.example.com",
    credentials={"api.example.com": {"type": "bearer", "value": os.getenv("API_KEY")}}
).discover(tags=["payments"])

# Framework adapters
kernel.add_plugin(plugin.to_semantic_kernel())
tools = plugin.to_langchain()
tools = plugin.to_llama_index()
```

## Licence

[Apache 2.0](../LICENSE)
