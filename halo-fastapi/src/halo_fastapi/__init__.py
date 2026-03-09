# SPDX-License-Identifier: Apache-2.0

"""halo-fastapi — HALO protocol implementation for FastAPI.

Server-side:
    ``HaloRegister(app)`` makes a FastAPI application HALO-compliant by
    registering OPTIONS handlers that serve ``application/llm+json``.

Client-side:
    ``HaloClient`` discovers and invokes HALO-compliant APIs, with
    built-in credential injection and schema caching.

Agent Framework adapter (optional):
    ``HaloAgentFrameworkAdapter`` converts discovered tools into Agent Framework
    ``FunctionTool`` instances.  Requires the ``agent-framework`` extra.

Semantic Kernel adapter (optional):
    ``HaloSemanticKernelAdapter`` converts discovered tools into a Semantic Kernel
    ``KernelPlugin``.  Requires the ``semantic-kernel`` extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from halo_fastapi._client import HaloClient
from halo_fastapi._constants import CONTENT_TYPE
from halo_fastapi._schema import HaloRegister
from halo_fastapi._types import (
    HaloAuth,
    HaloCall,
    HaloEffects,
    HaloExample,
    HaloLimits,
    HaloManifest,
    HaloNext,
    HaloObserve,
    HaloResilience,
    HaloSchema,
    HaloToolEntry,
    HaloTrust,
)

if TYPE_CHECKING:
    from halo_fastapi.adapters._agent_framework_adapter import HaloAgentFrameworkAdapter
    from halo_fastapi.adapters._semantic_kernel_adapter import HaloSemanticKernelAdapter

# HaloAgentFrameworkAdapter and HaloSemanticKernelAdapter are imported
# lazily via __getattr__ so their heavy dependencies stay optional.

__all__ = [
    "CONTENT_TYPE",
    "HaloAgentFrameworkAdapter",
    "HaloAuth",
    "HaloCall",
    "HaloClient",
    "HaloEffects",
    "HaloExample",
    "HaloLimits",
    "HaloManifest",
    "HaloNext",
    "HaloObserve",
    "HaloRegister",
    "HaloResilience",
    "HaloSchema",
    "HaloSemanticKernelAdapter",
    "HaloToolEntry",
    "HaloTrust",
]


def __getattr__(name: str) -> object:
    if name == "HaloAgentFrameworkAdapter":
        from halo_fastapi.adapters._agent_framework_adapter import HaloAgentFrameworkAdapter

        return HaloAgentFrameworkAdapter
    if name == "HaloSemanticKernelAdapter":
        from halo_fastapi.adapters._semantic_kernel_adapter import HaloSemanticKernelAdapter

        return HaloSemanticKernelAdapter
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
