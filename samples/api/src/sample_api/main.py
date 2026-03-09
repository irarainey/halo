# SPDX-License-Identifier: Apache-2.0

import fastapi
from fastapi import security

import halo_fastapi
from sample_api import data, models, settings
from sample_api.utils import logger

_settings = settings.Settings()

logger.configure_logging(_settings.log_level)
log = logger.create_logger("Server")

app = fastapi.FastAPI(title=_settings.app_title, version=_settings.app_version)

# Register the HALO endpoints with FastAPI - this is the only code needed in the API
halo_fastapi.HaloRegister(app)

log.success("Sample API configured", {"title": _settings.app_title, "version": _settings.app_version})

# -- Auth dependency ----------------------------------------------------------

_security = security.HTTPBearer()


# -- Weather ------------------------------------------------------------------


@app.post("/api/weather", response_model=models.WeatherResponse)
async def get_weather(body: models.WeatherRequest, _token: str = fastapi.Depends(_security)):
    """Return current weather conditions and forecast for a given city."""
    records = data.weather()
    match = next((r for r in records if r["city"].lower() == body.city.lower()), None)
    if not match:
        available = ", ".join(r["city"] for r in records)
        raise fastapi.HTTPException(status_code=404, detail=f"City not found. Available cities: {available}")
    return models.WeatherResponse(**match)


# -- Books --------------------------------------------------------------------


@app.post("/api/books", response_model=models.BookSearchResponse)
async def search_books(body: models.BookSearchRequest, _token: str = fastapi.Depends(_security)):
    """Search the book catalogue by title or author, with optional genre filter."""
    records = data.books()
    query = body.query.lower()
    results = [r for r in records if query in r["title"].lower() or query in r["author"].lower()]
    if body.genre:
        results = [r for r in results if r["genre"] == body.genre]
    return models.BookSearchResponse(
        results=[models.BookResult(**r) for r in results],
        total=len(results),
    )


# -- Inventory ----------------------------------------------------------------


@app.post("/api/inventory", response_model=models.InventoryResponse)
async def check_inventory(body: models.InventoryRequest, _token: str = fastapi.Depends(_security)):
    """Check stock levels across warehouses with optional category and low-stock filters."""
    records = data.inventory()
    items = records
    if body.category:
        items = [i for i in items if i["category"] == body.category]
    if body.low_stock_only:
        items = [i for i in items if i["stock"] <= i["reorder_threshold"]]
    return models.InventoryResponse(
        items=[models.InventoryItem(**i) for i in items],
        total=len(items),
    )


# -- Employees ----------------------------------------------------------------


@app.post("/api/employees", response_model=models.EmployeeLookupResponse)
async def lookup_employees(body: models.EmployeeLookupRequest, _token: str = fastapi.Depends(_security)):
    """Look up employees in the company directory with optional department and office filters."""
    records = data.employees()
    results = records
    if body.department:
        results = [e for e in results if e["department"] == body.department]
    if body.office:
        results = [e for e in results if e["office"].lower() == body.office.lower()]
    return models.EmployeeLookupResponse(
        employees=[models.Employee(**e) for e in results],
        total=len(results),
    )
