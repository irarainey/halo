# SPDX-License-Identifier: Apache-2.0

"""Tests for halo_fastapi._types — Pydantic model validation and serialisation."""

from typing import Any

import pydantic
import pytest

from halo_fastapi import _types

# ── HaloAuth ────────────────────────────────────────────────────


class TestHaloAuth:
    """Tests for the HaloAuth model."""

    def test_defaults(self) -> None:
        auth = _types.HaloAuth()
        assert auth.type == "none"
        assert auth.header is None
        assert auth.scopes == []
        assert auth.token_url is None
        assert auth.already is False

    def test_bearer(self) -> None:
        auth = _types.HaloAuth(type="bearer")
        assert auth.type == "bearer"

    def test_apikey_with_header(self) -> None:
        auth = _types.HaloAuth(type="apikey", header="X-Custom-Key")
        assert auth.type == "apikey"
        assert auth.header == "X-Custom-Key"

    def test_oauth_with_scopes(self) -> None:
        auth = _types.HaloAuth(
            type="oauth",
            token_url="https://auth.example.com/token",
            scopes=["read", "write"],
        )
        assert auth.type == "oauth"
        assert auth.token_url == "https://auth.example.com/token"
        assert auth.scopes == ["read", "write"]

    def test_token_url_alias(self) -> None:
        """token_url serialises as 'tokenUrl' via alias."""
        auth = _types.HaloAuth(type="oauth", token_url="https://example.com/token")
        dumped = auth.model_dump(by_alias=True)
        assert "tokenUrl" in dumped

    def test_already_flag(self) -> None:
        auth = _types.HaloAuth(type="bearer", already=True)
        assert auth.already is True


# ── HaloCall ────────────────────────────────────────────────────


class TestHaloCall:
    """Tests for the HaloCall model."""

    def test_required_fields(self) -> None:
        call = _types.HaloCall(method="POST", url="/api/orders")
        assert call.method == "POST"
        assert call.url == "/api/orders"

    def test_missing_method_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            _types.HaloCall(url="/api/orders")  # type: ignore[call-arg]

    def test_missing_url_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            _types.HaloCall(method="GET")  # type: ignore[call-arg]


# ── HaloEffects ─────────────────────────────────────────────────


class TestHaloEffects:
    """Tests for the HaloEffects model."""

    def test_defaults(self) -> None:
        effects = _types.HaloEffects()  # type: ignore[call-arg]
        assert effects.reversible is False
        assert effects.undo is None

    def test_reversible_with_undo(self) -> None:
        effects = _types.HaloEffects(reversible=True, undo="/api/orders/cancel")
        assert effects.reversible is True
        assert effects.undo == "/api/orders/cancel"


# ── HaloLimits ──────────────────────────────────────────────────


class TestHaloLimits:
    """Tests for the HaloLimits model."""

    def test_defaults(self) -> None:
        limits = _types.HaloLimits()  # type: ignore[call-arg]
        assert limits.rate is None
        assert limits.idempotent is False

    def test_rate_and_idempotent(self) -> None:
        limits = _types.HaloLimits(rate="100/hour", idempotent=True)
        assert limits.rate == "100/hour"
        assert limits.idempotent is True


# ── HaloResilience ──────────────────────────────────────────────


class TestHaloResilience:
    """Tests for the HaloResilience model."""

    def test_defaults(self) -> None:
        r = _types.HaloResilience()  # type: ignore[call-arg]
        assert r.retry is False
        assert r.backoff is None
        assert r.timeout_ms is None
        assert r.fallback is None

    def test_full_config(self) -> None:
        r = _types.HaloResilience(
            retry=True,
            backoff="exponential",
            timeout_ms=5000,
            fallback="/api/v1/fallback",
        )
        assert r.retry is True
        assert r.backoff == "exponential"
        assert r.timeout_ms == 5000
        assert r.fallback == "/api/v1/fallback"


# ── HaloNext ────────────────────────────────────────────────────


class TestHaloNext:
    """Tests for the HaloNext model."""

    def test_required_fields(self) -> None:
        n = _types.HaloNext(when="status=pending", suggest="/api/orders/confirm")
        assert n.when == "status=pending"
        assert n.suggest == "/api/orders/confirm"

    def test_missing_when_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            _types.HaloNext(suggest="/api/orders/confirm")  # type: ignore[call-arg]


# ── HaloTrust ───────────────────────────────────────────────────


class TestHaloTrust:
    """Tests for the HaloTrust model."""

    def test_defaults(self) -> None:
        t = _types.HaloTrust()  # type: ignore[call-arg]
        assert t.signed is False
        assert t.jwks is None

    def test_signed_with_jwks(self) -> None:
        t = _types.HaloTrust(signed=True, jwks="https://example.com/.well-known/jwks.json")
        assert t.signed is True
        assert t.jwks == "https://example.com/.well-known/jwks.json"


# ── HaloObserve ─────────────────────────────────────────────────


class TestHaloObserve:
    """Tests for the HaloObserve model."""

    def test_defaults(self) -> None:
        o = _types.HaloObserve()  # type: ignore[call-arg]
        assert o.trace_header is None
        assert o.explain is False

    def test_with_trace_header(self) -> None:
        o = _types.HaloObserve(trace_header="X-Trace-Id", explain=True)
        assert o.trace_header == "X-Trace-Id"
        assert o.explain is True


# ── HaloExample ─────────────────────────────────────────────────


class TestHaloExample:
    """Tests for the HaloExample model."""

    def test_with_input_and_output(self) -> None:
        e = _types.HaloExample(
            input={"name": "Alice"},
            output={"id": 1, "name": "Alice"},
        )
        assert e.input == {"name": "Alice"}
        assert e.output == {"id": 1, "name": "Alice"}

    def test_output_defaults_to_empty(self) -> None:
        e = _types.HaloExample(input={"q": "test"})
        assert e.output == {}

    def test_missing_input_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            _types.HaloExample()  # type: ignore[call-arg]


# ── HaloSchema ──────────────────────────────────────────────────


class TestHaloSchema:
    """Tests for the HaloSchema model."""

    def _minimal_schema(self, **overrides: Any) -> _types.HaloSchema:
        """Create a minimal valid HaloSchema for testing."""
        defaults: dict[str, Any] = {
            "call": _types.HaloCall(method="GET", url="/api/items"),
        }
        defaults.update(overrides)
        return _types.HaloSchema(**defaults)

    def test_minimal(self) -> None:
        s = self._minimal_schema()
        assert s.description == ""
        assert s.call.method == "GET"
        assert s.auth.type == "none"
        assert s.input == {}
        assert s.output == {}
        assert s.tags == []
        assert s.effects is None
        assert s.next == []
        assert s.examples == []

    def test_full_schema(self) -> None:
        s = self._minimal_schema(
            description="List items",
            why="Use when the user asks for inventory",
            tags=["inventory", "read"],
            effects=_types.HaloEffects(reversible=False),  # type: ignore[call-arg]
            limits=_types.HaloLimits(rate="50/min", idempotent=True),
            resilience=_types.HaloResilience(retry=True, timeout_ms=3000),  # type: ignore[call-arg]
            trust=_types.HaloTrust(signed=True),  # type: ignore[call-arg]
            observe=_types.HaloObserve(explain=True),  # type: ignore[call-arg]
            next=[_types.HaloNext(when="count>0", suggest="/api/items/{id}")],
            examples=[_types.HaloExample(input={}, output={"items": []})],
            status="active",
        )
        assert s.description == "List items"
        assert s.why == "Use when the user asks for inventory"
        assert s.tags == ["inventory", "read"]
        assert s.effects is not None
        assert s.limits is not None and s.limits.idempotent is True
        assert s.resilience is not None and s.resilience.retry is True
        assert s.trust is not None and s.trust.signed is True
        assert s.observe is not None and s.observe.explain is True
        assert len(s.next) == 1
        assert len(s.examples) == 1
        assert s.status == "active"

    def test_to_response_dict_strips_empty_values(self) -> None:
        """to_response_dict() removes empty strings, empty lists, and empty dicts."""
        s = self._minimal_schema(description="", tags=[], input={})
        d = s.to_response_dict()
        assert "description" not in d
        assert "tags" not in d
        assert "input" not in d
        # 'call' should remain since it has content.
        assert "call" in d

    def test_to_response_dict_preserves_false(self) -> None:
        """Falsy values like False and 0 must not be stripped."""
        s = self._minimal_schema(
            effects=_types.HaloEffects(reversible=False),  # type: ignore[call-arg]
        )
        d = s.to_response_dict()
        assert "effects" in d
        assert d["effects"]["reversible"] is False

    def test_to_response_dict_excludes_none(self) -> None:
        s = self._minimal_schema(status=None, sunset=None)
        d = s.to_response_dict()
        assert "status" not in d
        assert "sunset" not in d

    def test_to_response_dict_keeps_populated_fields(self) -> None:
        s = self._minimal_schema(
            description="Test",
            why="For testing",
            tags=["test"],
            input={"name": {"type": "string"}},
        )
        d = s.to_response_dict()
        assert d["description"] == "Test"
        assert d["why"] == "For testing"
        assert d["tags"] == ["test"]
        assert d["input"] == {"name": {"type": "string"}}


# ── HaloToolEntry ───────────────────────────────────────────────


class TestHaloToolEntry:
    """Tests for the HaloToolEntry model."""

    def test_required_url(self) -> None:
        entry = _types.HaloToolEntry(url="/api/books")
        assert entry.url == "/api/books"
        assert entry.name == ""
        assert entry.description == ""
        assert entry.tags == []

    def test_full_entry(self) -> None:
        entry = _types.HaloToolEntry(
            url="/api/books",
            name="list_books",
            description="List all books",
            tags=["books", "read"],
        )
        assert entry.name == "list_books"
        assert entry.tags == ["books", "read"]


# ── HaloManifest ────────────────────────────────────────────────


class TestHaloManifest:
    """Tests for the HaloManifest model."""

    def test_empty_manifest(self) -> None:
        m = _types.HaloManifest(api="Test API", version="1.0.0")
        assert m.api == "Test API"
        assert m.version == "1.0.0"
        assert m.tools == []

    def test_manifest_with_tools(self) -> None:
        m = _types.HaloManifest(
            api="Test API",
            version="2.0.0",
            tools=[
                _types.HaloToolEntry(url="/api/books", name="list_books"),
                _types.HaloToolEntry(url="/api/weather", name="get_weather"),
            ],
        )
        assert len(m.tools) == 2
        assert m.tools[0].name == "list_books"
        assert m.tools[1].url == "/api/weather"
