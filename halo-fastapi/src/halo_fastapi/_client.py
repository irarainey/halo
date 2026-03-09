# SPDX-License-Identifier: Apache-2.0

"""HaloClient — client-side adapter for the HALO protocol.

Discovers HALO-compliant APIs via ``OPTIONS`` requests, caches schemas,
injects credentials, and invokes tools directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib import parse

import aiohttp

from halo_fastapi import _constants, _types

_logger = logging.getLogger(__name__)

_DEFAULT_MAX_RETRIES = 5
_DEFAULT_BASE_DELAY = 0.5
_DEFAULT_MAX_DELAY = 30.0


async def _request_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay: float = _DEFAULT_BASE_DELAY,
    max_delay: float = _DEFAULT_MAX_DELAY,
) -> dict[str, Any]:
    """Execute an HTTP request with exponential backoff on retryable failures.

    Retries on connection errors and 5xx / 429 responses.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            async with session.request(method, url, headers=headers, json=json) as resp:
                if resp.status == 429 or resp.status >= 500:
                    if attempt == max_retries:
                        resp.raise_for_status()
                    delay = min(base_delay * (2**attempt), max_delay)
                    _logger.warning(
                        "Request to %s returned %s, retrying in %.1fs (attempt %d/%d)",
                        url,
                        resp.status,
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue
                resp.raise_for_status()
                result: dict[str, Any] = await resp.json(content_type=None)
                return result
        except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError) as exc:
            last_exc = exc
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2**attempt), max_delay)
            _logger.warning(
                "Connection to %s failed (%s), retrying in %.1fs (attempt %d/%d)",
                url,
                exc,
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(delay)

    msg = f"Request to {url} failed after {max_retries + 1} attempts"
    raise aiohttp.ClientError(msg) from last_exc


class HaloClient:
    """Client-side adapter that discovers and consumes HALO APIs.

    Usage::

        from halo_fastapi import HaloClient

        client = await HaloClient(
            base_url="https://api.example.com",
            bearer_token="my-token",
        ).discover(tags=["payments"])

        # Access the full manifest
        plugin.manifest

        # Access cached schemas
        plugin.schemas

        # Fetch a specific tool schema
        schema = await plugin.get_tool("/api/payments/charge")
    """

    def __init__(
        self,
        base_url: str,
        credentials: dict[str, dict[str, str]] | None = None,
        *,
        bearer_token: str | None = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_delay: float = _DEFAULT_BASE_DELAY,
        max_delay: float = _DEFAULT_MAX_DELAY,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._credentials = credentials or {}
        if bearer_token:
            parsed = parse.urlparse(self._base_url)
            hostname = parsed.hostname or ""
            domain = f"{hostname}:{parsed.port}" if parsed.port else hostname
            self._credentials[domain] = {"type": "bearer", "value": bearer_token}
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._manifest: _types.HaloManifest | None = None
        self._schemas: dict[str, _types.HaloSchema] = {}
        self._tools: list[_types.HaloToolEntry] = []
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return the shared session, creating one lazily if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> HaloClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    @property
    def manifest(self) -> _types.HaloManifest | None:
        """The root discovery manifest, populated after ``discover()``."""
        return self._manifest

    @property
    def schemas(self) -> dict[str, _types.HaloSchema]:
        """Cached per-route HALO schemas keyed by path."""
        return dict(self._schemas)

    @property
    def tools(self) -> list[_types.HaloToolEntry]:
        """Tool entries from the last ``discover()`` call."""
        return list(self._tools)

    async def discover(
        self,
        tags: list[str] | None = None,
    ) -> HaloClient:
        """Perform root discovery via ``OPTIONS /``.

        Args:
            tags: Optional list of tags to filter the manifest.

        Returns:
            self, for chaining.
        """
        url = self._base_url + "/"
        if tags:
            url += "?tags=" + ",".join(tags)

        headers = self._build_headers()
        session = await self._get_session()
        data = await _request_with_retry(
            session,
            "OPTIONS",
            url,
            headers=headers,
            max_retries=self._max_retries,
            base_delay=self._base_delay,
            max_delay=self._max_delay,
        )

        self._manifest = _types.HaloManifest(**data)
        self._tools = list(self._manifest.tools)
        _logger.info(
            "Discovered %d tool(s) from %s",
            len(self._tools),
            self._base_url,
        )
        return self

    async def get_tool(self, path: str) -> _types.HaloSchema:
        """Fetch the full HALO schema for a single endpoint.

        Caches the result so repeated calls do not fire
        additional ``OPTIONS`` requests.

        Args:
            path: The endpoint path, e.g. ``/api/payments/charge``.

        Returns:
            The full ``HaloSchema`` for the endpoint.
        """
        if path in self._schemas:
            return self._schemas[path]

        url = self._base_url + path
        headers = self._build_headers()
        session = await self._get_session()
        data = await _request_with_retry(
            session,
            "OPTIONS",
            url,
            headers=headers,
            max_retries=self._max_retries,
            base_delay=self._base_delay,
            max_delay=self._max_delay,
        )

        schema = _types.HaloSchema(**data)
        self._schemas[path] = schema
        _logger.debug("Fetched schema for %s", path)
        return schema

    async def invoke(
        self,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an endpoint using its HALO schema.

        Fetches the schema (if not cached) to determine the HTTP method,
        then fires the real request with credentials injected.

        Args:
            path: The endpoint path.
            body: Optional JSON request body.

        Returns:
            The parsed JSON response.
        """
        schema = await self.get_tool(path)
        url = self._base_url + schema.call.url
        method = schema.call.method.upper()
        headers = self._build_headers(include_accept_halo=False)
        _logger.debug("Invoking %s %s", method, url)

        session = await self._get_session()
        return await _request_with_retry(
            session,
            method,
            url,
            headers=headers,
            json=body,
            max_retries=self._max_retries,
            base_delay=self._base_delay,
            max_delay=self._max_delay,
        )

    def _build_headers(self, include_accept_halo: bool = True) -> dict[str, str]:
        """Build request headers with credentials and Accept type."""
        headers: dict[str, str] = {}
        if include_accept_halo:
            headers["Accept"] = _constants.CONTENT_TYPE

        # Inject credentials based on the base URL host (including port).
        parsed = parse.urlparse(self._base_url)
        hostname = parsed.hostname or ""
        host_with_port = f"{hostname}:{parsed.port}" if parsed.port else hostname
        cred = self._credentials.get(host_with_port) or self._credentials.get(hostname, {})
        cred_type = cred.get("type", "")
        value = cred.get("value", "")

        if cred_type == "bearer" and value:
            headers["Authorization"] = f"Bearer {value}"
        elif cred_type == "apikey" and value:
            header_name = cred.get("header", "X-API-Key")
            headers[header_name] = value
        elif cred_type == "basic" and value:
            headers["Authorization"] = f"Basic {value}"

        return headers
