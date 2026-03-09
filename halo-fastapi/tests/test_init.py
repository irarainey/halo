# SPDX-License-Identifier: Apache-2.0

"""Tests for halo_fastapi package exports and lazy imports."""

import pytest

import halo_fastapi
from halo_fastapi import _constants


class TestPackageExports:
    """Tests for the halo_fastapi public API surface."""

    def test_content_type_constant(self) -> None:
        assert halo_fastapi.CONTENT_TYPE == "application/llm+json"
        assert halo_fastapi.CONTENT_TYPE is _constants.CONTENT_TYPE

    def test_halo_client_importable(self) -> None:
        assert hasattr(halo_fastapi, "HaloClient")
        assert halo_fastapi.HaloClient is not None

    def test_halo_register_importable(self) -> None:
        assert hasattr(halo_fastapi, "HaloRegister")
        assert halo_fastapi.HaloRegister is not None

    def test_all_type_models_importable(self) -> None:
        for cls in (
            halo_fastapi.HaloAuth,
            halo_fastapi.HaloCall,
            halo_fastapi.HaloEffects,
            halo_fastapi.HaloExample,
            halo_fastapi.HaloLimits,
            halo_fastapi.HaloManifest,
            halo_fastapi.HaloNext,
            halo_fastapi.HaloObserve,
            halo_fastapi.HaloResilience,
            halo_fastapi.HaloSchema,
            halo_fastapi.HaloToolEntry,
            halo_fastapi.HaloTrust,
        ):
            assert cls is not None

    def test_all_list_complete(self) -> None:
        """__all__ contains every public name."""
        for name in halo_fastapi.__all__:
            assert hasattr(halo_fastapi, name) or name == "HaloAgentFrameworkAdapter"

    def test_lazy_adapter_import(self) -> None:
        """HaloAgentFrameworkAdapter is importable via lazy __getattr__."""
        adapter_cls = halo_fastapi.HaloAgentFrameworkAdapter
        assert adapter_cls is not None
        assert adapter_cls.__name__ == "HaloAgentFrameworkAdapter"

    def test_unknown_attribute_raises(self) -> None:
        with pytest.raises(AttributeError, match="no attribute"):
            _ = halo_fastapi.NonExistentThing  # type: ignore[attr-defined]
