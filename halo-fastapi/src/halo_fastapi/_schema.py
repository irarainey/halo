# SPDX-License-Identifier: Apache-2.0

"""HaloRegister — server-side FastAPI plugin for the HALO protocol.

A single call to ``HaloRegister(app)`` introspects all routes at startup
and registers ``OPTIONS`` handlers that serve ``application/llm+json``
schemas describing each endpoint.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import Any, get_type_hints

import fastapi
from fastapi import routing, security
from fastapi.dependencies import utils
from starlette import requests, responses

from halo_fastapi import _constants, _types

_logger = logging.getLogger(__name__)


def _detect_auth(dependant: Any) -> _types.HaloAuth:
    """Walk the FastAPI dependency tree and detect auth type."""
    deps_to_check: list[Any] = []
    if hasattr(dependant, "dependencies"):
        deps_to_check.extend(dependant.dependencies)

    for dep in deps_to_check:
        # The actual security class lives on the dependency model.
        call = dep.call if hasattr(dep, "call") else None
        if call is None:
            continue

        if isinstance(call, security.HTTPBearer):
            return _types.HaloAuth(type="bearer")
        if isinstance(call, security.HTTPBasic):
            return _types.HaloAuth(type="basic")
        if isinstance(call, security.APIKeyHeader):
            name = getattr(call.model, "name", None) or "X-API-Key"
            return _types.HaloAuth(type="apikey", header=name)
        if isinstance(call, security.OAuth2PasswordBearer):
            token_url = getattr(call, "tokenUrl", None)
            scopes = list(getattr(call, "scopes", {}).keys())
            return _types.HaloAuth(type="oauth", token_url=token_url, scopes=scopes)

        # Recurse into sub-dependencies.
        if hasattr(dep, "dependencies") and dep.dependencies:
            sub = _detect_auth(dep)
            if sub.type != "none":
                return sub

    return _types.HaloAuth()


def _resolve_any_of(prop: dict[str, Any]) -> dict[str, Any]:
    """Resolve an ``anyOf`` wrapper produced by Pydantic for optional types.

    When Pydantic serialises ``Literal[...] | None`` it emits::

        {"anyOf": [{"type": "string", "enum": [...]}, {"type": "null"}], ...}

    This helper collapses that into the non-null branch so callers can
    read ``type`` and ``enum`` directly.
    """
    branches: list[dict[str, Any]] = prop.get("anyOf", [])
    for branch in branches:
        if branch.get("type") != "null":
            return branch
    return {}


def _extract_input_fields(
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Extract a flat input field map from a Pydantic JSON schema."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for name, prop in props.items():
        # Pydantic wraps ``Literal[...] | None`` in an ``anyOf``
        # envelope.  Resolve it so ``type`` and ``enum`` are visible.
        resolved = _resolve_any_of(prop) if "anyOf" in prop else prop

        # Start with all JSON Schema properties from the resolved
        # branch (preserves constraints like minimum, maxLength, etc.)
        entry: dict[str, Any] = dict(resolved)
        # Description lives on the original prop, not the anyOf branch.
        if "description" in prop:
            entry["description"] = prop["description"]
        if name in required:
            entry["required"] = True
        fields[name] = entry
    return fields


def _build_schema(
    route: routing.APIRoute,
    auth: _types.HaloAuth,
) -> _types.HaloSchema:
    """Build a HaloSchema from a single FastAPI route."""
    method = next(iter(route.methods or {"GET"})).upper()
    path = route.path
    endpoint = route.endpoint

    # Description from docstring.
    docstring = inspect.getdoc(endpoint) or ""

    # Resolve request body type from type hints.
    hints = get_type_hints(endpoint)
    body_type = hints.get("body")

    # Extract LLM extra and input schema from the Pydantic model.
    llm_extra: dict[str, Any] = {}
    input_fields: dict[str, Any] = {}
    if body_type is not None and hasattr(body_type, "model_json_schema"):
        raw_schema = body_type.model_json_schema()
        llm_extra = raw_schema.get("llm", {})
        input_fields = _extract_input_fields(raw_schema)

    # Extract output schema from response_model.
    output_fields: dict[str, Any] = {}
    if route.response_model is not None and hasattr(route.response_model, "model_json_schema"):
        output_fields = route.response_model.model_json_schema()

    # Build effects.
    effects_raw = llm_extra.get("effects")
    effects = _types.HaloEffects(**effects_raw) if effects_raw else None

    # Build limits.
    limits_raw = llm_extra.get("limits")
    limits = _types.HaloLimits(**limits_raw) if limits_raw else None

    # Build resilience.
    resilience_raw = llm_extra.get("resilience")
    resilience = _types.HaloResilience(**resilience_raw) if resilience_raw else None

    # Build trust.
    trust_raw = llm_extra.get("trust")
    trust = _types.HaloTrust(**trust_raw) if trust_raw else None

    # Build observe.
    observe_raw = llm_extra.get("observe")
    observe = _types.HaloObserve(**observe_raw) if observe_raw else None

    # Build next steps.
    next_steps = [_types.HaloNext(**n) for n in llm_extra.get("next", [])]

    # Build examples.
    examples = [_types.HaloExample(**e) for e in llm_extra.get("examples", [])]

    why = llm_extra.get("why", docstring)

    return _types.HaloSchema(
        description=docstring,
        call=_types.HaloCall(method=method, url=path),
        auth=auth,
        input=input_fields,
        output=output_fields,
        why=why,
        tags=llm_extra.get("tags", []),
        effects=effects,
        limits=limits,
        resilience=resilience,
        trust=trust,
        observe=observe,
        next=next_steps,
        examples=examples,
        status=llm_extra.get("status"),
        sunset=llm_extra.get("sunset"),
        replace_with=llm_extra.get("replace_with"),
    )


class HaloRegister:
    """FastAPI plugin that makes every route HALO-compliant.

    Usage::

        from halo_fastapi import HaloRegister
        from fastapi import FastAPI

        app = FastAPI(title="My API", version="1.0.0")
        HaloRegister(app)

    At startup the plugin introspects all registered routes, extracts
    Pydantic schemas and dependency-injected auth, then registers
    ``OPTIONS`` handlers that serve ``application/llm+json`` responses.
    """

    def __init__(
        self,
        app: fastapi.FastAPI,
        *,
        tool_filter: Callable[[requests.Request, str], bool] | None = None,
    ) -> None:
        self._app = app
        self._schemas: dict[str, list[_types.HaloSchema]] = {}
        self._endpoint_names: dict[str, str] = {}
        self._tool_filter = tool_filter

        async def _register() -> None:
            self._introspect()
            self._register_handlers()

        app.router.on_startup.append(_register)

    def _introspect(self) -> None:
        """Walk the route table and build HALO schemas."""
        for route in self._app.routes:
            if not isinstance(route, routing.APIRoute):
                continue

            # Resolve the dependency tree for auth detection.
            dependant = utils.get_dependant(path=route.path, call=route.endpoint)
            auth = _detect_auth(dependant)

            schema = _build_schema(route, auth)
            self._schemas.setdefault(route.path, []).append(schema)
            self._endpoint_names[route.path] = route.endpoint.__name__
            _logger.debug("Registered HALO schema for %s %s", schema.call.method, route.path)

        total = sum(len(v) for v in self._schemas.values())
        _logger.info("HALO introspection complete — %d schema(s) on %d path(s)", total, len(self._schemas))

    def _register_handlers(self) -> None:
        """Register OPTIONS handlers for each route and the root.

        If an OPTIONS handler already exists on a given path, the
        existing handler is preserved and called for non-HALO requests
        (i.e. when ``Accept`` is not ``application/llm+json``).
        """
        app = self._app
        schemas = self._schemas
        endpoint_names = self._endpoint_names
        tool_filter = self._tool_filter

        existing_root = self._pop_options_route("/")

        # Root manifest handler.
        @app.options("/")
        async def _halo_root_manifest(
            request: requests.Request,
            tags: str | None = None,
        ) -> responses.Response:
            if request.headers.get("accept") != _constants.CONTENT_TYPE:
                if existing_root is not None:
                    return await existing_root(request)
                return responses.Response(status_code=204)

            tools = []
            requested_tags = {t.strip() for t in tags.split(",")} if tags else None
            for path, schema_list in schemas.items():
                for schema in schema_list:
                    if requested_tags and not (requested_tags & set(schema.tags)):
                        continue
                    if tool_filter and not tool_filter(request, path):
                        continue
                    tools.append(
                        _types.HaloToolEntry(
                            url=path,
                            method=schema.call.method,
                            name=endpoint_names.get(path, path.strip("/").split("/")[-1]),
                            description=schema.description,
                            tags=schema.tags,
                        )
                    )

            manifest = _types.HaloManifest(
                api=app.title or "",
                version=app.version or "",
                description=getattr(app, "description", None) or "",
                tools=tools,
            )
            return responses.JSONResponse(
                content=manifest.model_dump(),
                media_type=_constants.CONTENT_TYPE,
            )

        # Per-route OPTIONS handlers.
        for path, schema_list in schemas.items():
            self._add_route_handler(path, schema_list)

    def _pop_options_route(
        self,
        path: str,
    ) -> Callable[..., Coroutine[Any, Any, responses.Response]] | None:
        """Remove and return an existing OPTIONS handler for *path*.

        Walks ``app.routes`` and removes the first ``APIRoute`` whose
        path matches and whose methods include ``OPTIONS``.  Returns
        the endpoint callable, or ``None`` if no match is found.
        """
        for i, route in enumerate(self._app.routes):
            if isinstance(route, routing.APIRoute) and route.path == path and "OPTIONS" in (route.methods or set()):
                self._app.routes.pop(i)
                _logger.debug("Wrapped existing OPTIONS handler for %s", path)
                return route.endpoint  # type: ignore[return-value]
        return None

    def _add_route_handler(self, path: str, schema_list: list[_types.HaloSchema]) -> None:
        """Register an OPTIONS handler for a single route."""
        response_list = [s.to_response_dict() for s in schema_list]
        existing = self._pop_options_route(path)

        @self._app.options(path)
        async def _halo_route_options(
            request: requests.Request,
            _response: list[dict[str, Any]] = response_list,
            _existing: Callable[..., Coroutine[Any, Any, responses.Response]] | None = existing,
        ) -> responses.Response:
            if request.headers.get("accept") != _constants.CONTENT_TYPE:
                if _existing is not None:
                    return await _existing(request)
                return responses.Response(status_code=204)
            return responses.JSONResponse(content=_response, media_type=_constants.CONTENT_TYPE)
