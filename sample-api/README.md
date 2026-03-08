# Sample API

A FastAPI server that demonstrates HALO-compliant endpoints using the `halohttp` package. This shows how an API can describe itself to LLM agents via the `OPTIONS` verb and `application/llm+json` content type.

## Running

From the repository root:

```bash
uvicorn sample_api.main:app --reload --port 3001 --app-dir sample-api/src
```

Or use the **Sample API** launch profile in VS Code.

## Configuration

Settings are managed via Pydantic Settings with the `SAMPLE_API_` env prefix:

| Variable | Default | Description |
|---|---|---|
| `SAMPLE_API_APP_TITLE` | `Sample HALO API` | API title |
| `SAMPLE_API_APP_VERSION` | `0.1.0` | API version |
| `SAMPLE_API_HOST` | `0.0.0.0` | Bind host |
| `SAMPLE_API_PORT` | `3001` | Bind port |

## Endpoints

| Method | Path | Description | Tags |
|---|---|---|---|
| POST | `/api/greet` | Generate a greeting | `greetings`, `read` |
| POST | `/api/echo` | Echo text back | `debug`, `read` |

Both endpoints require Bearer token authentication.

## Licence

[Apache 2.0](../LICENSE)
