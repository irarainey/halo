# Sample Agent

An LLM agent application that consumes the [sample API](../sample-api) via the HALO protocol using `halohttp` and [Agent Framework](https://github.com/microsoft/agents).

## Running

Ensure the sample API is running first, then from the repository root:

```bash
python -m sample_agent.main
```

Or use the **Sample Agent** launch profile in VS Code. The **Sample API + Agent** compound profile launches both together.

## Configuration

Settings are managed via Pydantic Settings with the `SAMPLE_AGENT_` env prefix:

| Variable | Default | Description |
|---|---|---|
| `SAMPLE_AGENT_API_BASE_URL` | `http://localhost:3001` | URL of the HALO-compliant API to consume |

## Licence

[Apache 2.0](../LICENSE)
