# SPDX-License-Identifier: Apache-2.0

"""Tests for halo_fastapi._schema — server-side FastAPI HALO plugin."""

# NOTE: Do NOT use ``from __future__ import annotations`` here.
# ``_build_schema`` calls ``get_type_hints()`` on endpoint functions and
# PEP 563 deferred annotations break resolution for models defined in
# the local scope.

from typing import Any

import fastapi
import httpx
import pydantic
from fastapi import security

from halo_fastapi import _constants, _schema, _types

# ── Models used by _build_schema tests (must be at module level) ─


class CreateItem(pydantic.BaseModel):
    name: str = pydantic.Field(description="The item name")
    quantity: int = pydantic.Field(description="Amount in stock")


class SearchBody(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        json_schema_extra={
            "llm": {
                "why": "Use when searching for products",
                "tags": ["search", "products"],
                "effects": {"reversible": False},
                "limits": {"rate": "10/min", "idempotent": True},
                "status": "active",
            }
        }
    )
    query: str


class ItemResponse(pydantic.BaseModel):
    id: int
    name: str


class BooksBody(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(json_schema_extra={"llm": {"tags": ["books"]}})
    query: str


class WeatherBody(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(json_schema_extra={"llm": {"tags": ["weather"]}})
    city: str


# ── Helper factories ────────────────────────────────────────────


def _make_app(**kwargs: Any) -> fastapi.FastAPI:
    """Create a FastAPI app with HALO registered."""
    app = fastapi.FastAPI(title="Test API", version="0.1.0", **kwargs)
    return app


async def _client(app: fastapi.FastAPI) -> httpx.AsyncClient:
    """Create an async test client that triggers ASGI lifespan events."""
    # Manually fire startup hooks so HaloRegister introspects routes
    # and registers OPTIONS handlers before we send requests.
    for hook in app.router.on_startup:
        await hook()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ── _resolve_any_of ─────────────────────────────────────────────


class TestResolveAnyOf:
    """Tests for the _resolve_any_of helper."""

    def test_returns_non_null_branch(self) -> None:
        prop = {
            "anyOf": [
                {"type": "string", "enum": ["a", "b"]},
                {"type": "null"},
            ]
        }
        result = _schema._resolve_any_of(prop)
        assert result == {"type": "string", "enum": ["a", "b"]}

    def test_returns_empty_when_all_null(self) -> None:
        prop = {"anyOf": [{"type": "null"}]}
        result = _schema._resolve_any_of(prop)
        assert result == {}

    def test_returns_empty_when_no_any_of(self) -> None:
        prop = {"type": "string"}
        result = _schema._resolve_any_of(prop)
        assert result == {}

    def test_returns_first_non_null_branch(self) -> None:
        prop = {
            "anyOf": [
                {"type": "null"},
                {"type": "integer", "minimum": 0},
            ]
        }
        result = _schema._resolve_any_of(prop)
        assert result == {"type": "integer", "minimum": 0}


# ── _extract_input_fields ───────────────────────────────────────


class TestExtractInputFields:
    """Tests for the _extract_input_fields helper."""

    def test_simple_properties(self) -> None:
        schema = {
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        fields = _schema._extract_input_fields(schema)
        assert "name" in fields
        assert fields["name"]["type"] == "string"
        assert fields["name"]["required"] is True
        assert "age" in fields
        assert "required" not in fields["age"]

    def test_anyof_optional_field(self) -> None:
        schema = {
            "properties": {
                "status": {
                    "anyOf": [
                        {"type": "string", "enum": ["active", "inactive"]},
                        {"type": "null"},
                    ],
                    "description": "Filter by status",
                }
            },
            "required": [],
        }
        fields = _schema._extract_input_fields(schema)
        assert fields["status"]["type"] == "string"
        assert fields["status"]["enum"] == ["active", "inactive"]
        assert fields["status"]["description"] == "Filter by status"

    def test_empty_schema(self) -> None:
        fields = _schema._extract_input_fields({})
        assert fields == {}

    def test_preserves_constraints(self) -> None:
        schema = {
            "properties": {
                "count": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["count"],
        }
        fields = _schema._extract_input_fields(schema)
        assert fields["count"]["minimum"] == 1
        assert fields["count"]["maximum"] == 100
        assert fields["count"]["required"] is True


# ── _detect_auth ────────────────────────────────────────────────


class TestDetectAuth:
    """Tests for the _detect_auth helper."""

    def test_no_dependencies(self) -> None:
        """Returns default none auth when no deps exist."""

        class FakeDep:
            def __init__(self) -> None:
                self.dependencies: list[Any] = []

        auth = _schema._detect_auth(FakeDep())
        assert auth.type == "none"

    def test_bearer_auth(self) -> None:
        bearer = security.HTTPBearer()

        class FakeSub:
            def __init__(self) -> None:
                self.call = bearer
                self.dependencies: list[Any] = []

        class FakeDep:
            def __init__(self) -> None:
                self.dependencies = [FakeSub()]

        auth = _schema._detect_auth(FakeDep())
        assert auth.type == "bearer"

    def test_basic_auth(self) -> None:
        basic = security.HTTPBasic()

        class FakeSub:
            def __init__(self) -> None:
                self.call = basic
                self.dependencies: list[Any] = []

        class FakeDep:
            def __init__(self) -> None:
                self.dependencies = [FakeSub()]

        auth = _schema._detect_auth(FakeDep())
        assert auth.type == "basic"

    def test_apikey_auth(self) -> None:
        apikey = security.APIKeyHeader(name="X-My-Key")

        class FakeSub:
            def __init__(self) -> None:
                self.call = apikey
                self.dependencies: list[Any] = []

        class FakeDep:
            def __init__(self) -> None:
                self.dependencies = [FakeSub()]

        auth = _schema._detect_auth(FakeDep())
        assert auth.type == "apikey"
        assert auth.header == "X-My-Key"

    def test_no_call_attribute(self) -> None:
        """Deps without a .call attribute are skipped."""

        class FakeSub:
            def __init__(self) -> None:
                self.dependencies: list[Any] = []

        class FakeDep:
            def __init__(self) -> None:
                self.dependencies = [FakeSub()]

        auth = _schema._detect_auth(FakeDep())
        assert auth.type == "none"


# ── _build_schema ───────────────────────────────────────────────


class TestBuildSchema:
    """Tests for the _build_schema helper."""

    def test_simple_get_route(self) -> None:
        app = _make_app()

        @app.get("/api/items")
        async def list_items() -> list[dict[str, str]]:
            """List all items."""
            return []

        route = next(r for r in app.routes if getattr(r, "path", None) == "/api/items")
        schema = _schema._build_schema(route, _types.HaloAuth())  # type: ignore[arg-type]
        assert schema.call.method == "GET"
        assert schema.call.url == "/api/items"
        assert schema.description == "List all items."
        assert schema.auth.type == "none"

    def test_post_route_with_body_model(self) -> None:
        app = _make_app()

        @app.post("/api/items")
        async def create_item(body: CreateItem) -> dict[str, str]:
            """Create a new item."""
            return {}

        route = next(r for r in app.routes if getattr(r, "path", None) == "/api/items")
        schema = _schema._build_schema(route, _types.HaloAuth())  # type: ignore[arg-type]
        assert schema.call.method == "POST"
        assert "name" in schema.input
        assert "quantity" in schema.input
        assert schema.input["name"]["description"] == "The item name"

    def test_llm_extra_metadata(self) -> None:
        app = _make_app()

        @app.post("/api/search")
        async def search(body: SearchBody) -> dict[str, Any]:
            """Search products."""
            return {}

        route = next(r for r in app.routes if getattr(r, "path", None) == "/api/search")
        schema = _schema._build_schema(route, _types.HaloAuth())  # type: ignore[arg-type]
        assert schema.why == "Use when searching for products"
        assert schema.tags == ["search", "products"]
        assert schema.effects is not None
        assert schema.effects.reversible is False
        assert schema.limits is not None
        assert schema.limits.rate == "10/min"
        assert schema.status == "active"

    def test_route_with_response_model(self) -> None:
        app = _make_app()

        @app.get("/api/items/{item_id}", response_model=ItemResponse)
        async def get_item(item_id: int) -> ItemResponse:
            """Get a single item."""
            return ItemResponse(id=item_id, name="test")

        route = next(r for r in app.routes if getattr(r, "path", None) == "/api/items/{item_id}")
        schema = _schema._build_schema(route, _types.HaloAuth())  # type: ignore[arg-type]
        assert "properties" in schema.output
        assert "id" in schema.output["properties"]
        assert "name" in schema.output["properties"]

    def test_no_docstring(self) -> None:
        app = _make_app()

        @app.get("/api/nodoc")
        async def nodoc() -> dict[str, str]:
            return {}

        route = next(r for r in app.routes if getattr(r, "path", None) == "/api/nodoc")
        schema = _schema._build_schema(route, _types.HaloAuth())  # type: ignore[arg-type]
        assert schema.description == ""


# ── HaloRegister integration ────────────────────────────────────


class TestHaloRegister:
    """Integration tests for HaloRegister via ASGI test client."""

    async def test_root_manifest(self) -> None:
        """OPTIONS / with HALO Accept returns a manifest."""
        app = _make_app()

        @app.get("/api/books")
        async def list_books() -> list[dict[str, str]]:
            """List all books."""
            return []

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["api"] == "Test API"
        assert data["version"] == "0.1.0"
        assert len(data["tools"]) == 1
        assert data["tools"][0]["url"] == "/api/books"

    async def test_root_without_halo_accept_returns_204(self) -> None:
        """OPTIONS / without HALO Accept returns 204."""
        app = _make_app()

        @app.get("/api/books")
        async def list_books() -> list[dict[str, str]]:
            """List all books."""
            return []

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options("/")
        assert resp.status_code == 204

    async def test_route_options_returns_schema(self) -> None:
        """OPTIONS /api/books with HALO Accept returns the endpoint schema as an array."""
        app = _make_app()

        @app.get("/api/books")
        async def list_books() -> list[dict[str, str]]:
            """List all books in the library."""
            return []

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/api/books",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["call"]["method"] == "GET"
        assert data[0]["call"]["url"] == "/api/books"
        assert data[0]["description"] == "List all books in the library."

    async def test_route_options_without_accept_returns_204(self) -> None:
        """OPTIONS /api/books without HALO Accept returns 204."""
        app = _make_app()

        @app.get("/api/books")
        async def list_books() -> list[dict[str, str]]:
            """List all books."""
            return []

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options("/api/books")
        assert resp.status_code == 204

    async def test_tag_filtering(self) -> None:
        """Root manifest filters tools by tag query parameter."""
        app = _make_app()

        @app.post("/api/books")
        async def search_books(body: BooksBody) -> dict[str, Any]:
            """Search books."""
            return {}

        @app.post("/api/weather")
        async def get_weather(body: WeatherBody) -> dict[str, Any]:
            """Get weather."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/?tags=weather",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["url"] == "/api/weather"

    async def test_multiple_routes(self) -> None:
        """All routes appear in the manifest."""
        app = _make_app()

        @app.get("/api/a")
        async def route_a() -> dict[str, str]:
            """Route A."""
            return {}

        @app.post("/api/b")
        async def route_b() -> dict[str, str]:
            """Route B."""
            return {}

        @app.put("/api/c")
        async def route_c() -> dict[str, str]:
            """Route C."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        urls = {t["url"] for t in data["tools"]}
        assert urls == {"/api/a", "/api/b", "/api/c"}

    async def test_tool_filter(self) -> None:
        """tool_filter callback excludes matching routes from the manifest."""
        app = _make_app()

        @app.get("/api/public")
        async def public_route() -> dict[str, str]:
            """Public."""
            return {}

        @app.get("/api/internal")
        async def internal_route() -> dict[str, str]:
            """Internal."""
            return {}

        def only_public(_request: Any, path: str) -> bool:
            return "internal" not in path

        _schema.HaloRegister(app, tool_filter=only_public)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        urls = [t["url"] for t in data["tools"]]
        assert "/api/public" in urls
        assert "/api/internal" not in urls

    async def test_bearer_auth_detected(self) -> None:
        """Routes with HTTPBearer dependency report bearer auth."""
        app = _make_app()
        bearer = security.HTTPBearer()

        dep = fastapi.Depends(bearer)

        @app.get("/api/protected")
        async def protected(
            creds: Any = dep,
        ) -> dict[str, str]:
            """Protected endpoint."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/api/protected",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["auth"]["type"] == "bearer"

    async def test_content_type_header(self) -> None:
        """HALO responses use application/llm+json content type."""
        app = _make_app()

        @app.get("/api/test")
        async def test_route() -> dict[str, str]:
            """Test."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/api/test",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        assert resp.headers["content-type"].startswith(_constants.CONTENT_TYPE)

    async def test_schema_strips_empty_fields(self) -> None:
        """Per-route OPTIONS response omits empty fields."""
        app = _make_app()

        @app.get("/api/simple")
        async def simple() -> dict[str, str]:
            """Simple endpoint."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/api/simple",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert isinstance(data, list)
        schema = data[0]
        # Empty fields should be stripped by to_response_dict.
        assert "input" not in schema
        assert "output" not in schema
        assert "tags" not in schema
        # Populated fields remain.
        assert "call" in schema
        assert "description" in schema

    async def test_multi_method_path(self) -> None:
        """Multiple methods on the same path return an array with all schemas."""
        app = _make_app()

        @app.get("/api/items")
        async def list_items() -> list[dict[str, str]]:
            """List items."""
            return []

        @app.post("/api/items")
        async def create_item(body: CreateItem) -> dict[str, str]:
            """Create an item."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/api/items",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        methods = {s["call"]["method"] for s in data}
        assert methods == {"GET", "POST"}

    async def test_manifest_includes_description(self) -> None:
        """Root manifest includes API description."""
        app = _make_app(description="A test API for unit testing.")

        @app.get("/api/test")
        async def test_route() -> dict[str, str]:
            """Test."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert data["description"] == "A test API for unit testing."

    async def test_manifest_tool_entries_include_method(self) -> None:
        """Tool entries in the manifest include the HTTP method."""
        app = _make_app()

        @app.post("/api/items")
        async def create_item(body: CreateItem) -> dict[str, str]:
            """Create an item."""
            return {}

        _schema.HaloRegister(app)
        client = await _client(app)

        async with client:
            resp = await client.options(
                "/",
                headers={"Accept": _constants.CONTENT_TYPE},
            )
        data = resp.json()
        assert data["tools"][0]["method"] == "POST"
