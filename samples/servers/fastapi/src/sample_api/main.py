# SPDX-License-Identifier: Apache-2.0

from datetime import UTC, datetime

import fastapi
from fastapi import security

import halo_fastapi
from sample_api import data, models, settings, store
from sample_api.utils import logger

_settings = settings.Settings()

logger.configure_logging(_settings.log_level)
log = logger.create_logger("Server")

app = fastapi.FastAPI(
    title=_settings.app_title,
    version=_settings.app_version,
    description="Sample API demonstrating the HALO protocol with books, employees, inventory, and weather data.",
)

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


@app.get("/api/books", response_model=models.BookSearchResponse)
async def search_books(
    params: models.BookSearchRequest = fastapi.Depends(),  # noqa: B008
    _token: str = fastapi.Depends(_security),
):
    """Search the book catalogue by title or author, with optional genre filter."""
    records = store.books()
    results = records
    if params.query:
        q = params.query.lower()
        results = [r for r in results if q in r["title"].lower() or q in r["author"].lower()]
    if params.genre:
        results = [r for r in results if r["genre"].lower() == params.genre.lower()]
    return models.BookSearchResponse(
        results=[models.BookResult(**r) for r in results],
        total=len(results),
    )


@app.post("/api/books", response_model=models.CreateBookResponse)
async def add_book(body: models.CreateBookRequest, _token: str = fastapi.Depends(_security)):
    """Add a new book to the catalogue."""
    isbn = store._generate_isbn()
    record = {
        "isbn": isbn,
        "title": body.title,
        "author": body.author,
        "genre": body.genre,
        "year": datetime.now(tz=UTC).year,
        "pages": 0,
        "rating": 0.0,
        "summary": body.summary or f"A {body.genre} book by {body.author}.",
    }
    store.books().append(record)
    return models.CreateBookResponse(
        isbn=isbn,
        title=body.title,
        author=body.author,
        genre=body.genre,
        message=f"'{body.title}' by {body.author} added to the catalogue.",
    )


# -- Inventory ----------------------------------------------------------------


@app.get("/api/inventory", response_model=models.InventoryResponse)
async def search_inventory(
    params: models.InventoryRequest = fastapi.Depends(),  # noqa: B008
    _token: str = fastapi.Depends(_security),
):
    """Check stock levels across warehouses with optional category and low-stock filters."""
    items = store.inventory()
    if params.category:
        items = [i for i in items if i["category"].lower() == params.category.lower()]
    if params.low_stock_only:
        items = [i for i in items if i["stock"] <= i["reorder_threshold"]]
    return models.InventoryResponse(
        items=[models.InventoryItem(**i) for i in items],
        total=len(items),
    )


@app.post("/api/inventory", response_model=models.CreateInventoryItemResponse)
async def add_inventory_item(body: models.CreateInventoryItemRequest, _token: str = fastapi.Depends(_security)):
    """Add a new product to the warehouse inventory."""
    sku = store._generate_sku(body.category)
    record = {
        "sku": sku,
        "name": body.name,
        "category": body.category,
        "price_gbp": body.price_gbp,
        "stock": body.stock,
        "warehouse": body.warehouse,
        "reorder_threshold": 10,
    }
    store.inventory().append(record)
    return models.CreateInventoryItemResponse(
        sku=sku,
        name=body.name,
        category=body.category,
        stock=body.stock,
        message=f"'{body.name}' added to inventory at {body.warehouse}.",
    )


# -- Employees ----------------------------------------------------------------


@app.get("/api/employees", response_model=models.EmployeeLookupResponse)
async def search_employees(
    params: models.EmployeeLookupRequest = fastapi.Depends(),  # noqa: B008
    _token: str = fastapi.Depends(_security),
):
    """Look up employees in the company directory with optional department and office filters."""
    results = store.employees()
    if params.department:
        results = [e for e in results if e["department"].lower() == params.department.lower()]
    if params.office:
        results = [e for e in results if e["office"].lower() == params.office.lower()]
    return models.EmployeeLookupResponse(
        employees=[models.Employee(**e) for e in results],
        total=len(results),
    )


@app.post("/api/employees", response_model=models.CreateEmployeeResponse)
async def add_employee(body: models.CreateEmployeeRequest, _token: str = fastapi.Depends(_security)):
    """Register a new employee in the company directory."""
    emp_id = store._generate_employee_id()
    email = body.name.lower().replace(" ", ".") + "@example.com"
    record = {
        "employee_id": emp_id,
        "name": body.name,
        "email": email,
        "department": body.department,
        "role": body.role,
        "office": body.office,
        "start_date": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
    }
    store.employees().append(record)
    return models.CreateEmployeeResponse(
        employee_id=emp_id,
        name=body.name,
        department=body.department,
        role=body.role,
        email=email,
        message=f"{body.name} registered as {body.role} in {body.department}.",
    )
