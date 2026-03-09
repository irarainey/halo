# SPDX-License-Identifier: Apache-2.0

"""halo-fastapi — HALO protocol implementation for FastAPI.

Server-side:
    ``HaloRegister(app)`` makes a FastAPI application HALO-compliant by
    registering OPTIONS handlers that serve ``application/llm+json``.

Client-side:
    ``HttpPlugin`` discovers and invokes HALO-compliant APIs, with
    built-in credential injection and schema caching.
"""

from halo_fastapi._constants import CONTENT_TYPE  # noqa: important[import-modules-not-symbols]
from halo_fastapi._plugin import HttpPlugin  # noqa: important[import-modules-not-symbols]
from halo_fastapi._schema import HaloRegister  # noqa: important[import-modules-not-symbols]
from halo_fastapi._types import (  # noqa: important[import-modules-not-symbols]
    HaloAuth,
    HaloCall,
    HaloEffects,
    HaloExample,
    HaloLimits,
    HaloManifest,
    HaloNext,
    HaloResilience,
    HaloSchema,
    HaloToolEntry,
)

__all__ = [
    "CONTENT_TYPE",
    "HaloAuth",
    "HaloCall",
    "HaloEffects",
    "HaloExample",
    "HaloLimits",
    "HaloManifest",
    "HaloNext",
    "HaloRegister",
    "HaloResilience",
    "HaloSchema",
    "HaloToolEntry",
    "HttpPlugin",
]
