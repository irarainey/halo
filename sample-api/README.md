# Sample API

A FastAPI server that demonstrates HALO-compliant endpoints across four
domains. Each endpoint includes Pydantic models with `json_schema_extra`
metadata so LLM agents can discover capabilities via the `OPTIONS` verb and
`application/llm+json` content type.

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
| `SAMPLE_API_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/weather` | Return current weather conditions and forecast for a city |
| POST | `/api/books` | Search the book catalogue by title or author with optional genre filter |
| POST | `/api/inventory` | Check stock levels with optional category and low-stock filters |
| POST | `/api/employees` | Look up employees by department and office |

All endpoints require Bearer token authentication.

## Project Structure

```text
sample-api/
├── data/                  # JSON data files
│   ├── books.json
│   ├── employees.json
│   ├── inventory.json
│   └── weather.json
└── src/sample_api/
    ├── main.py            # FastAPI app and route definitions
    ├── settings.py        # Pydantic Settings configuration
    ├── data/
    │   ├── __init__.py    # Re-exports loader functions
    │   └── loader.py      # JSON data loader
    ├── models/
    │   ├── __init__.py    # Re-exports all model classes
    │   ├── books.py       # BookSearchRequest, BookResult, BookSearchResponse
    │   ├── employees.py   # EmployeeLookupRequest, Employee, EmployeeLookupResponse
    │   ├── inventory.py   # InventoryRequest, InventoryItem, InventoryResponse
    │   └── weather.py     # WeatherRequest, WeatherResponse
    └── utils/
        ├── __init__.py
        └── logger.py      # Coloured console log formatter
```

## Licence

[Apache 2.0](../LICENSE)
