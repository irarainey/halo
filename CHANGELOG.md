# Changelog

All notable changes to this project will be documented in this file.

## 0.2.0

### Breaking Changes

- Both sample agent apps (`samples/agent-framework` and
  `samples/semantic-kernel`) are now excluded from the uv workspace due to
  conflicting transitive dependencies (`azure-ai-projects` version mismatch
  between `agent-framework-core` and `semantic-kernel`). Install them on
  demand with `uv pip install -e samples/agent-framework` or
  `uv pip install -e samples/semantic-kernel`. The `poe sync:maf` and
  `poe sync:sk` tasks handle this automatically.

### Added

- `semantic-kernel` optional extra for `halo-fastapi`
  (`halo-fastapi[semantic-kernel]`).
- `httpx` added to the dev dependency group (previously only available as a
  transitive dependency).
- `tool.uv.conflicts` declaration in root `pyproject.toml` marking the
  `agent-framework` and `semantic-kernel` extras as mutually exclusive.
- Dependency sync instructions added to the READMEs for `halo-fastapi`,
  `samples/agent-framework`, and `samples/api`.

### Changed

- Updated protocol specification to remove duplication and unfair claims. The full specification is now in `halo-specification.md` with a CC BY 4.0 licence.
- Upgraded `agent-framework-core` from `1.0.0rc2` to `1.0.0rc3`.
- Upgraded `agent-framework-devui` from `>=1.0.0b260225` to
  `>=1.0.0b260304`.
- Upgraded `fastapi` minimum from `>=0.129.0` to `>=0.135.1`.
- Upgraded `python-dotenv` minimum from `>=1.2.1` to `>=1.2.2`.
- Upgraded `rich` minimum from `>=14.0.0` to `>=14.3.3`.
- Pinned `pydantic` to `<2.12` in `halo-fastapi` to avoid compatibility
  issues.
- `poe sync:maf` now runs `uv pip install -e samples/agent-framework` after
  `uv sync`, matching the pattern used by `poe sync:sk`.
- VS Code "Sync MAF" task updated to include
  `uv pip install -e samples/agent-framework`.

### Fixed

- `test_all_list_complete` no longer fails when `semantic-kernel` is not
  installed. Lazy-loaded adapters with optional dependencies are skipped
  instead of triggering an import error via `hasattr()`.

## 0.1.0

Initial public release.