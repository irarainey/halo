# Sample API

A FastAPI server that demonstrates HALO-compliant endpoints across four
domains. Each endpoint includes Pydantic models with `json_schema_extra`
metadata so LLM agents can discover capabilities via the `OPTIONS` verb and
`application/llm+json` content type.

## Dependencies

The sample API is a workspace member. Sync with:

```bash
uv sync --all-packages
```

## Running

From the repository root:

```bash
uvicorn sample_api.main:app --reload --port 3010 --app-dir samples/servers/fastapi/src
```

Or use the **Sample API** launch profile in VS Code.

## Configuration

Settings are managed via Pydantic Settings. The `.env` file in the repository root is loaded automatically.

| Variable | Default | Description |
|---|---|---|
| `APP_TITLE` | `Sample HALO API` | API title |
| `APP_VERSION` | `0.1.0` | API version |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `3010` | Bind port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

## Endpoints

| Method | Path | Description | Tags |
|---|---|---|---|
| POST | `/api/weather` | Return current weather conditions and forecast for a city | weather, read |
| GET | `/api/books` | Search the book catalogue by title/author with optional genre filter | books, read |
| POST | `/api/books` | Add a new book to the catalogue | books, write |
| GET | `/api/inventory` | Check stock levels with optional category and low-stock filters | inventory, read |
| POST | `/api/inventory` | Add a new product to the warehouse inventory | inventory, write |
| GET | `/api/employees` | Look up employees by department and office | employees, read |
| POST | `/api/employees` | Register a new employee in the company directory | employees, write |

All endpoints require Bearer token authentication.

GET endpoints accept query parameters (e.g. `?department=engineering&office=London`). POST create endpoints accept a JSON body. Data created via POST is stored in memory and resets on server restart.

## Project Structure

```text
samples/servers/fastapi/
├── data/                  # JSON data files
│   ├── books.json
│   ├── employees.json
│   ├── inventory.json
│   └── weather.json
└── src/sample_api/
    ├── main.py            # FastAPI app and route definitions
    ├── settings.py        # Pydantic Settings configuration
    ├── store.py           # In-memory data store (lazy-loaded from JSON)
    ├── data/
    │   ├── __init__.py    # Re-exports loader functions
    │   └── loader.py      # JSON data loader
    ├── models/
    │   ├── __init__.py    # Re-exports all model classes
    │   ├── books.py       # BookSearchRequest, CreateBookRequest, BookResult, etc.
    │   ├── employees.py   # EmployeeLookupRequest, CreateEmployeeRequest, etc.
    │   ├── inventory.py   # InventoryRequest, CreateInventoryItemRequest, etc.
    │   └── weather.py     # WeatherRequest, WeatherResponse
    └── utils/
        ├── __init__.py
        └── logger.py      # Coloured console log formatter
```

## Licence

[Apache 2.0](../LICENSE)
