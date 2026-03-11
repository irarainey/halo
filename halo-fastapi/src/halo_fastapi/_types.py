# SPDX-License-Identifier: Apache-2.0

"""Pydantic models representing the HALO protocol schema structures."""

from __future__ import annotations

from typing import Any

import pydantic


class HaloAuth(pydantic.BaseModel):
    """Authentication shape descriptor for a HALO endpoint."""

    type: str = pydantic.Field(
        default="none",
        description="Auth mechanism: bearer, apikey, oauth, basic, none",
    )
    header: str | None = pydantic.Field(
        default=None,
        description="Header name for API-key auth",
    )
    scopes: list[str] = pydantic.Field(
        default_factory=list,
        description="Required OAuth scopes",
    )
    token_url: str | None = pydantic.Field(
        default=None,
        serialization_alias="tokenUrl",
        description="OAuth token endpoint URL",
    )
    already: bool = pydantic.Field(
        default=False,
        description="If true, discovery credentials are valid for invocation",
    )


class HaloCall(pydantic.BaseModel):
    """HTTP method and URL for invoking the endpoint."""

    method: str = pydantic.Field(..., description="HTTP verb: GET, POST, PUT, PATCH, DELETE")
    url: str = pydantic.Field(..., description="Endpoint path (relative or absolute)")


class HaloEffects(pydantic.BaseModel):
    """Side-effect contract for the endpoint."""

    reversible: bool = pydantic.Field(False, description="Whether the action can be undone")
    undo: str | None = pydantic.Field(None, description="URL of the endpoint that reverses this action")


class HaloLimits(pydantic.BaseModel):
    """Rate and idempotency information."""

    rate: str | None = pydantic.Field(None, description="Rate limit, e.g. '100/hour'")
    idempotent: bool = pydantic.Field(False, description="Whether repeated calls have the same effect")


class HaloResilience(pydantic.BaseModel):
    """Resilience contract for the endpoint."""

    retry: bool = pydantic.Field(False, description="Whether the agent should retry on failure")
    backoff: str | None = pydantic.Field(None, description="Backoff strategy: linear, exponential, none")
    timeout_ms: int | None = pydantic.Field(None, description="Expected maximum response time in milliseconds")
    fallback: str | None = pydantic.Field(None, description="URL of a fallback endpoint")


class HaloNext(pydantic.BaseModel):
    """Conditional next-step suggestion for workflow chaining."""

    when: str = pydantic.Field(..., description="Condition expression, e.g. 'status=pending'")
    suggest: str = pydantic.Field(..., description="URL of the suggested next endpoint")


class HaloTrust(pydantic.BaseModel):
    """Cryptographic trust metadata."""

    signed: bool = pydantic.Field(False, description="Whether the schema is cryptographically signed")
    jwks: str | None = pydantic.Field(None, description="URL of JWKS endpoint for signature verification")


class HaloObserve(pydantic.BaseModel):
    """Observability configuration."""

    trace_header: str | None = pydantic.Field(None, description="Header name for trace ID injection")
    explain: bool = pydantic.Field(False, description="Whether the agent should include a call reason header for audit")


class HaloExample(pydantic.BaseModel):
    """Concrete input/output example for the endpoint."""

    input: dict[str, Any] = pydantic.Field(..., description="Example request body")
    output: dict[str, Any] = pydantic.Field(default_factory=dict, description="Example response body")


class HaloSchema(pydantic.BaseModel):
    """Full HALO schema for a single endpoint.

    Returned when a client sends ``OPTIONS /path`` with
    ``Accept: application/llm+json``.
    """

    description: str = pydantic.Field("", description="Natural-language description of the endpoint")
    call: HaloCall
    auth: HaloAuth = pydantic.Field(default_factory=lambda: HaloAuth(type="none"))
    input: dict[str, Any] = pydantic.Field(
        default_factory=dict,
        description="JSON Schema describing request parameters",
    )
    output: dict[str, Any] = pydantic.Field(
        default_factory=dict,
        description="JSON Schema describing the response structure",
    )
    why: str = pydantic.Field(
        "",
        description="LLM routing hint — when to use this endpoint",
    )
    tags: list[str] = pydantic.Field(
        default_factory=list,
        description="Free-form tags for filtering and agent scoping",
    )
    effects: HaloEffects | None = None
    limits: HaloLimits | None = None
    resilience: HaloResilience | None = None
    next: list[HaloNext] = pydantic.Field(default_factory=list)
    examples: list[HaloExample] = pydantic.Field(default_factory=list)
    trust: HaloTrust | None = None
    observe: HaloObserve | None = None
    status: str | None = pydantic.Field(None, description="Lifecycle: active, deprecated, sunset")
    sunset: str | None = pydantic.Field(None, description="ISO date when deprecated endpoint is removed")
    replace_with: str | None = pydantic.Field(None, description="URL of the replacement endpoint")

    model_config = pydantic.ConfigDict(populate_by_name=True)

    def to_response_dict(self) -> dict[str, Any]:
        """Serialise to a dict, stripping None and empty fields.

        Preserves legitimate falsy values such as ``False`` and ``0``.
        """
        raw = self.model_dump(by_alias=True, exclude_none=True)
        _empty: tuple[str, list[Any], dict[str, Any]] = ("", [], {})
        return {k: v for k, v in raw.items() if v not in _empty}


class HaloToolEntry(pydantic.BaseModel):
    """A single tool entry in the root discovery manifest."""

    url: str = pydantic.Field(..., description="Endpoint path")
    method: str = pydantic.Field(default="", description="HTTP method (GET, POST, etc.)")
    name: str = pydantic.Field(default="", description="Short human-readable tool name")
    description: str = pydantic.Field(default="", description="What the tool does")
    tags: list[str] = pydantic.Field(default_factory=list, description="Tags for filtering")


class HaloManifest(pydantic.BaseModel):
    """Root discovery manifest returned by ``OPTIONS /``.

    Contains the API name, version, and a list of all
    discoverable tool endpoints with their tags.
    """

    api: str = pydantic.Field(..., description="API title")
    version: str = pydantic.Field(..., description="API version")
    description: str = pydantic.Field(default="", description="What this API does")
    tools: list[HaloToolEntry] = pydantic.Field(default_factory=list, description="Available tool endpoints")
