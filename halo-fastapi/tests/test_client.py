# SPDX-License-Identifier: Apache-2.0

"""Tests for halo_fastapi._client — client-side HALO protocol adapter."""

from typing import Any
from unittest import mock

import aiohttp
import pytest

from halo_fastapi import _client, _constants, _types

# ── Helpers ─────────────────────────────────────────────────────


def _mock_response(
    status: int = 200,
    json_data: dict[str, Any] | None = None,
) -> mock.MagicMock:
    """Create a mock aiohttp response with async context manager support."""
    resp = mock.MagicMock()
    resp.status = status
    resp.json = mock.AsyncMock(return_value=json_data or {})
    resp.raise_for_status = mock.MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=mock.MagicMock(),
            history=(),
            status=status,
        )
    return resp


def _mock_session(responses: list[mock.MagicMock]) -> mock.MagicMock:
    """Create a mock aiohttp.ClientSession returning given responses in order."""
    session = mock.MagicMock(spec=aiohttp.ClientSession)
    session.closed = False

    call_count = 0

    def _request(*args: Any, **kwargs: Any) -> mock.MagicMock:
        nonlocal call_count
        ctx = mock.MagicMock()
        idx = min(call_count, len(responses) - 1)
        ctx.__aenter__ = mock.AsyncMock(return_value=responses[idx])
        ctx.__aexit__ = mock.AsyncMock(return_value=False)
        call_count += 1
        return ctx

    session.request = _request
    session.close = mock.AsyncMock()
    return session


# ── _request_with_retry ─────────────────────────────────────────


class TestRequestWithRetry:
    """Tests for the _request_with_retry function."""

    async def test_success_on_first_attempt(self) -> None:
        resp = _mock_response(200, {"result": "ok"})
        session = _mock_session([resp])
        result = await _client._request_with_retry(
            session,
            "GET",
            "http://test/api",
            max_retries=0,
        )
        assert result == {"result": "ok"}

    async def test_retries_on_500(self) -> None:
        """Retries on 5xx then succeeds."""
        fail_resp = _mock_response(500)
        ok_resp = _mock_response(200, {"ok": True})
        session = _mock_session([fail_resp, ok_resp])
        result = await _client._request_with_retry(
            session,
            "GET",
            "http://test/api",
            max_retries=1,
            base_delay=0.01,
        )
        assert result == {"ok": True}

    async def test_retries_on_429(self) -> None:
        """Retries on 429 (rate limited)."""
        rate_resp = _mock_response(429)
        ok_resp = _mock_response(200, {"data": "yes"})
        session = _mock_session([rate_resp, ok_resp])
        result = await _client._request_with_retry(
            session,
            "GET",
            "http://test/api",
            max_retries=1,
            base_delay=0.01,
        )
        assert result == {"data": "yes"}

    async def test_raises_after_max_retries_on_server_error(self) -> None:
        """Raises after exhausting retries on 5xx."""
        fail_resp = _mock_response(500)
        session = _mock_session([fail_resp, fail_resp])
        with pytest.raises(aiohttp.ClientResponseError):
            await _client._request_with_retry(
                session,
                "GET",
                "http://test/api",
                max_retries=1,
                base_delay=0.01,
            )

    async def test_raises_on_client_error_status(self) -> None:
        """4xx errors (other than 429) raise immediately."""
        resp = _mock_response(404)
        session = _mock_session([resp])
        with pytest.raises(aiohttp.ClientResponseError):
            await _client._request_with_retry(
                session,
                "GET",
                "http://test/api",
                max_retries=0,
            )

    async def test_retries_on_connection_error(self) -> None:
        """Retries on connection errors then succeeds."""
        session = mock.MagicMock(spec=aiohttp.ClientSession)
        session.closed = False

        call_count = 0
        ok_resp = _mock_response(200, {"connected": True})

        def _request(*args: Any, **kwargs: Any) -> mock.MagicMock:
            nonlocal call_count
            ctx = mock.MagicMock()
            if call_count == 0:
                call_count += 1
                ctx.__aenter__ = mock.AsyncMock(side_effect=aiohttp.ClientConnectionError("refused"))
                ctx.__aexit__ = mock.AsyncMock(return_value=False)
            else:
                ctx.__aenter__ = mock.AsyncMock(return_value=ok_resp)
                ctx.__aexit__ = mock.AsyncMock(return_value=False)
            return ctx

        session.request = _request
        result = await _client._request_with_retry(
            session,
            "GET",
            "http://test/api",
            max_retries=1,
            base_delay=0.01,
        )
        assert result == {"connected": True}

    async def test_passes_headers_and_json(self) -> None:
        """Headers and JSON body are forwarded to the session."""
        resp = _mock_response(200, {})
        session = mock.MagicMock(spec=aiohttp.ClientSession)
        session.closed = False

        captured: dict[str, Any] = {}

        def _request(*args: Any, **kwargs: Any) -> mock.MagicMock:
            captured["args"] = args
            captured["kwargs"] = kwargs
            ctx = mock.MagicMock()
            ctx.__aenter__ = mock.AsyncMock(return_value=resp)
            ctx.__aexit__ = mock.AsyncMock(return_value=False)
            return ctx

        session.request = _request
        await _client._request_with_retry(
            session,
            "POST",
            "http://test/api",
            headers={"X-Custom": "value"},
            json={"key": "val"},
            max_retries=0,
        )
        assert captured["args"] == ("POST", "http://test/api")
        assert captured["kwargs"]["headers"] == {"X-Custom": "value"}
        assert captured["kwargs"]["json"] == {"key": "val"}


# ── HaloClient.__init__ ────────────────────────────────────────


class TestHaloClientInit:
    """Tests for HaloClient initialisation."""

    def test_strips_trailing_slash(self) -> None:
        client = _client.HaloClient(base_url="http://localhost:3010/")
        assert client._base_url == "http://localhost:3010"

    def test_bearer_token_stored_as_credential(self) -> None:
        client = _client.HaloClient(
            base_url="http://localhost:3010",
            bearer_token="my-token",
        )
        cred = client._credentials.get("localhost:3010")
        assert cred is not None
        assert cred["type"] == "bearer"
        assert cred["value"] == "my-token"

    def test_bearer_token_with_default_port(self) -> None:
        """URL without explicit port uses hostname only as key."""
        client = _client.HaloClient(
            base_url="https://api.example.com",
            bearer_token="tok",
        )
        assert "api.example.com" in client._credentials

    def test_explicit_credentials(self) -> None:
        creds = {"myhost:8080": {"type": "apikey", "value": "key123"}}
        client = _client.HaloClient(
            base_url="http://myhost:8080",
            credentials=creds,
        )
        assert client._credentials == creds

    def test_custom_retry_settings(self) -> None:
        client = _client.HaloClient(
            base_url="http://localhost",
            max_retries=10,
            base_delay=1.0,
            max_delay=60.0,
        )
        assert client._max_retries == 10
        assert client._base_delay == 1.0
        assert client._max_delay == 60.0

    def test_initial_state(self) -> None:
        client = _client.HaloClient(base_url="http://localhost")
        assert client.manifest is None
        assert client.schemas == {}
        assert client.tools == []


# ── HaloClient._build_headers ──────────────────────────────────


class TestBuildHeaders:
    """Tests for HaloClient._build_headers credential injection."""

    def test_includes_halo_accept_by_default(self) -> None:
        client = _client.HaloClient(base_url="http://localhost")
        headers = client._build_headers()
        assert headers["Accept"] == _constants.CONTENT_TYPE

    def test_excludes_accept_when_disabled(self) -> None:
        client = _client.HaloClient(base_url="http://localhost")
        headers = client._build_headers(include_accept_halo=False)
        assert "Accept" not in headers

    def test_bearer_token_header(self) -> None:
        client = _client.HaloClient(
            base_url="http://localhost:3010",
            bearer_token="tok123",
        )
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer tok123"

    def test_apikey_header(self) -> None:
        client = _client.HaloClient(
            base_url="http://myhost:9090",
            credentials={
                "myhost:9090": {
                    "type": "apikey",
                    "value": "secret",
                    "header": "X-My-Key",
                }
            },
        )
        headers = client._build_headers()
        assert headers["X-My-Key"] == "secret"

    def test_apikey_default_header_name(self) -> None:
        client = _client.HaloClient(
            base_url="http://myhost:9090",
            credentials={"myhost:9090": {"type": "apikey", "value": "secret"}},
        )
        headers = client._build_headers()
        assert headers["X-API-Key"] == "secret"

    def test_basic_auth_header(self) -> None:
        client = _client.HaloClient(
            base_url="http://myhost",
            credentials={"myhost": {"type": "basic", "value": "dXNlcjpwYXNz"}},
        )
        headers = client._build_headers()
        assert headers["Authorization"] == "Basic dXNlcjpwYXNz"

    def test_no_credentials(self) -> None:
        client = _client.HaloClient(base_url="http://localhost")
        headers = client._build_headers()
        assert "Authorization" not in headers

    def test_host_with_port_matched_first(self) -> None:
        """Credentials keyed by host:port take precedence over host only."""
        client = _client.HaloClient(
            base_url="http://myhost:8080",
            credentials={
                "myhost:8080": {"type": "bearer", "value": "port-tok"},
                "myhost": {"type": "bearer", "value": "host-tok"},
            },
        )
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer port-tok"


# ── HaloClient.discover ────────────────────────────────────────


class TestHaloClientDiscover:
    """Tests for HaloClient.discover."""

    async def test_discover_populates_manifest_and_tools(self) -> None:
        manifest_data = {
            "api": "Test",
            "version": "1.0",
            "tools": [
                {"url": "/api/books", "name": "list_books", "description": "List books", "tags": ["books"]},
                {"url": "/api/weather", "name": "weather", "description": "Get weather", "tags": []},
            ],
        }
        mock_session = _mock_session([_mock_response(200, manifest_data)])

        client = _client.HaloClient(base_url="http://test")
        client._session = mock_session

        result = await client.discover()
        assert result is client  # Returns self for chaining.
        assert client.manifest is not None
        assert client.manifest.api == "Test"
        assert len(client.tools) == 2
        assert client.tools[0].name == "list_books"
        await client.close()

    async def test_discover_with_tag_filter(self) -> None:
        """Tags are appended to the URL as a query parameter."""
        manifest_data = {"api": "Test", "version": "1.0", "tools": []}
        mock_session = _mock_session([_mock_response(200, manifest_data)])

        captured_url: str = ""

        original_request = mock_session.request

        def _capture_request(*args: Any, **kwargs: Any) -> Any:
            nonlocal captured_url
            captured_url = args[1] if len(args) > 1 else kwargs.get("url", "")
            return original_request(*args, **kwargs)

        mock_session.request = _capture_request

        client = _client.HaloClient(base_url="http://test")
        client._session = mock_session

        await client.discover(tags=["books", "novels"])
        assert "?tags=books,novels" in captured_url
        await client.close()


# ── HaloClient.get_tool ────────────────────────────────────────


class TestHaloClientGetTool:
    """Tests for HaloClient.get_tool."""

    async def test_fetches_and_caches_schema(self) -> None:
        schema_data = {
            "description": "List books",
            "call": {"method": "GET", "url": "/api/books"},
        }
        mock_session = _mock_session([_mock_response(200, schema_data)])

        client = _client.HaloClient(base_url="http://test")
        client._session = mock_session

        schema = await client.get_tool("/api/books")
        assert schema.call.method == "GET"
        assert schema.description == "List books"

        # Second call returns cached; no new request.
        schema2 = await client.get_tool("/api/books")
        assert schema2 is schema
        await client.close()

    async def test_schemas_property_returns_copy(self) -> None:
        client = _client.HaloClient(base_url="http://test")
        client._schemas["/test"] = [
            _types.HaloSchema(  # type: ignore[call-arg]
                call=_types.HaloCall(method="GET", url="/test"),
            )
        ]
        schemas = client.schemas
        assert "/test" in schemas
        # Mutating the returned dict must not affect the internal state.
        schemas.pop("/test")
        assert "/test" in client._schemas
        await client.close()

    async def test_get_tool_with_method_selects_correct_schema(self) -> None:
        """get_tool() with method parameter returns the matching schema."""
        client = _client.HaloClient(base_url="http://test")
        get_schema = _types.HaloSchema(  # type: ignore[call-arg]
            call=_types.HaloCall(method="GET", url="/items"),
            description="List items",
        )
        post_schema = _types.HaloSchema(  # type: ignore[call-arg]
            call=_types.HaloCall(method="POST", url="/items"),
            description="Create item",
        )
        client._schemas["/items"] = [get_schema, post_schema]

        result = await client.get_tool("/items", method="POST")
        assert result.call.method == "POST"
        assert result.description == "Create item"

        result2 = await client.get_tool("/items", method="GET")
        assert result2.call.method == "GET"
        assert result2.description == "List items"
        await client.close()

    async def test_get_tool_without_method_returns_first(self) -> None:
        """get_tool() without method returns the first schema in the list."""
        client = _client.HaloClient(base_url="http://test")
        get_schema = _types.HaloSchema(  # type: ignore[call-arg]
            call=_types.HaloCall(method="GET", url="/items"),
            description="List items",
        )
        post_schema = _types.HaloSchema(  # type: ignore[call-arg]
            call=_types.HaloCall(method="POST", url="/items"),
            description="Create item",
        )
        client._schemas["/items"] = [get_schema, post_schema]

        result = await client.get_tool("/items")
        assert result is get_schema
        await client.close()


# ── HaloClient.invoke ──────────────────────────────────────────


class TestHaloClientInvoke:
    """Tests for HaloClient.invoke."""

    async def test_invoke_uses_schema_method(self) -> None:
        """invoke() fetches the schema then calls the correct HTTP method."""
        schema_data = {
            "description": "Create item",
            "call": {"method": "POST", "url": "/api/items"},
        }
        invoke_result = {"id": 42, "name": "Widget"}

        # First call returns schema (OPTIONS), second returns invoke result.
        mock_session = _mock_session(
            [
                _mock_response(200, schema_data),
                _mock_response(200, invoke_result),
            ]
        )

        captured_calls: list[tuple[Any, ...]] = []
        original_request = mock_session.request

        def _capture(*args: Any, **kwargs: Any) -> Any:
            captured_calls.append(args)
            return original_request(*args, **kwargs)

        mock_session.request = _capture

        client = _client.HaloClient(base_url="http://test")
        client._session = mock_session

        result = await client.invoke("/api/items", body={"name": "Widget"})
        assert result == {"id": 42, "name": "Widget"}

        # First call is OPTIONS for schema, second is POST for invoke.
        assert captured_calls[0][0] == "OPTIONS"
        assert captured_calls[1][0] == "POST"
        await client.close()


# ── HaloClient context manager ──────────────────────────────────


class TestHaloClientContextManager:
    """Tests for HaloClient async context manager."""

    async def test_async_context_manager(self) -> None:
        async with _client.HaloClient(base_url="http://test") as client:
            assert isinstance(client, _client.HaloClient)
        # Session should be closed after exiting.
        assert client._session is None

    async def test_close_is_idempotent(self) -> None:
        client = _client.HaloClient(base_url="http://test")
        await client.close()
        await client.close()  # Should not raise.

    async def test_session_created_lazily(self) -> None:
        client = _client.HaloClient(base_url="http://test")
        assert client._session is None
        session = await client._get_session()
        assert session is not None
        await client.close()
