# Changelog

All notable changes to this project will be documented in this file.

## 0.3.1-draft

### Specification Changes

- **Tool surface trust (section 9.6):** New section — consumer-side risks from tool surface expansion and tool shadowing across servers, with manifest pinning and allowlist mitigations.
- **Skills (sections 7, 7.3, 14):** Removed "multi-tool orchestration" and "tool orchestration logic" — the LLM should infer tool composition from well-described individual tools.
- **Auth-aware discovery (section 3.4):** Replaced invalid JSON comments with separate code blocks.
- **Server example (section 12.4):** Simplified annotated code example — replaced verbose block comments with concise inline annotations.
- **Editorial pass:** Toned down absolute claims, removed repetitive disclaimers from section 9 subsections, fixed code examples in section 12.6 to return arrays per the spec, reduced verbosity across sections 1.2, 1.4, 2.4, 3.2, 8.2, and 12.3 without removing content, and minor language improvements throughout.
- **Version:** Bumped to 0.3.1-draft.

### Documentation Changes

- **README files:** Updated sample API references and restructured directory paths across root, agent-framework, semantic-kernel, and sample server READMEs (#2).

## 0.3.0-draft

### Specification Changes

- **OpenAPI comparison (section 2.4):** Rewritten with fair counter-arguments, cited LLM provider tool-calling formats (OpenAI, Anthropic, Gemini), acknowledged `x-*` extensions and existing conversion libraries. Removed unsupported "disabled in production" argument.
- **MCP positioning:** Aligned throughout spec — HALO targets thin-wrapper MCP servers; complementary for MCP servers doing real work or serving consumer clients. Removed combative "Without MCP" subtitle. Added MCP bridge pattern (stdio MCP consuming HALO schemas at runtime).
- **Scope note (section 2):** Added explicit scope — HALO targets HTTP API tool discovery only, not MCP's resources, prompts, sampling, or sessions. Clarified "tool" means REST API endpoint.
- **Applicability (section 2.5):** New section — honest about consumer client limitations (ChatGPT, Copilot, Claude Desktop require MCP). HALO's audience is developer-built agent systems.
- **Error responses (section 2.6):** New section — formalised HTTP status code behaviour for all OPTIONS scenarios.
- **Skills comparison (section 7):** Rewritten — skills now win on most dimensions. Added skills-as-abstraction-layer framing, multi-source orchestration, deliberate decoupling vs accidental drift.
- **Security (section 9):** New section — auth-gating recommendation, information disclosure, schema poisoning, prompt injection, rate limiting. All noted as not HALO-specific.
- **Root manifest:** Added `description` field for API-level LLM reasoning. Documented manifest fields in section 6.1.
- **Tag filtering (section 3.2):** Clarified OR semantics for multi-tag queries. Added DDD/microservices note.
- **Two-phase lazy loading (section 3.5):** Corrected to show two LLM calls (tool selection + request construction).
- **Caching (section 3.7):** New section — ETag/Cache-Control recommendation, cold-start vs warm-agent flows.
- **Intent-based filtering (section 3.6):** Removed redundant second OPTIONS call — LLM selects from manifest directly.
- **Prior art (section 11.2):** Added MCP as a proper entry. Updated OpenAPI entry to cross-reference section 2.4.
- **Human vs LLM descriptions (section 2.4):** Added `why` vs OpenAPI `description` audience distinction with examples.
- **IANA media type (section 2.2):** Added note that `application/llm+json` is a custom media type, not IANA-registered.
- **API discovery limitation (section 2.5):** Acknowledged HALO requires pre-configured base URLs.
- **Section 8:** Consolidated six short subsections into a compact table while retaining the three substantive subsections.
- **Section 10 table:** Updated to acknowledge embedded MCP, MCP dynamic tool lists, and skills-as-decoupling.
- **Section 14 summary:** Updated to reflect balanced MCP positioning, skills-first framing, and scoped "What it removes" list.
- **Removed** undefined `"already": true` field from section 4.2.
- **Removed** "commonly misunderstood" claim from section 12.4.
- **Multi-method paths (section 6.1):** Per-endpoint OPTIONS always returns a JSON array — one schema per HTTP method. Single-method paths return a one-element array for consistency.
- **Manifest tool entries:** Now include `method` field for disambiguation with multi-method paths.

### Implementation Changes (`halo-fastapi` 0.3.0)

- **Multi-method path support:** Schema storage changed from `dict[str, HaloSchema]` (keyed by path) to `dict[str, list[HaloSchema]]` — multiple HTTP methods on the same path are all preserved.
- **Per-endpoint OPTIONS returns array:** `_add_route_handler()` now returns a JSON array of schemas, consistent with the updated protocol spec.
- **Root manifest `description` field:** Manifest response now includes `description` from FastAPI's `app.description`.
- **Tool entry `method` field:** `HaloToolEntry` now includes the HTTP method for each tool in the manifest.
- **Client array handling:** `HaloClient.get_tool()` accepts optional `method` parameter, handles array responses, and maintains backwards compatibility with single-object responses from older servers.
- **Client cache updated:** `schemas` property returns `dict[str, list[HaloSchema]]`.
- **Adapters updated:** Both `HaloAgentFrameworkAdapter` and `HaloSemanticKernelAdapter` pass `entry.method` to `get_tool()` and `invoke()`, ensuring correct method selection on multi-method paths.
- **Client GET query parameters:** `invoke()` now sends parameters as query params for GET requests and JSON body for POST/PUT/PATCH/DELETE.
- **Endpoint name keying:** `_endpoint_names` keyed by `method:path` instead of path only, fixing duplicate names on multi-method paths.
- **Query parameter model support:** `_build_schema()` now detects Pydantic models used as query-parameter dependencies (via `Depends()`) when no explicit body parameter exists, extracting input schema and LLM metadata for GET endpoints.
- **Removed `HaloAuth.already` field:** Vestigial field not in the spec removed from `_types.py`.
- **Version:** Bumped to 0.3.0.
- **Tests:** 8 new tests (multi-method paths, manifest description, manifest tool method, tag filtering across methods, schema content differences, client method selection). 105 tests pass.

### Sample API Changes

- **CRUD pattern:** Books, inventory, and employees now have both GET (search/list) and POST (create) endpoints on the same path, demonstrating multi-method support.
- **GET endpoints use query parameters:** Search/filter via `?query=Orwell&genre=fiction` instead of POST with JSON body. Pydantic models via `Depends()` carry full LLM metadata.
- **POST endpoints create resources:** Add books, employees, and inventory items to an in-memory store. Data persists within a session and resets on server restart.
- **In-memory store:** New `store.py` module provides lazy-loaded, mutable in-memory data backed by JSON files.
- **API description:** FastAPI app now includes a `description` field for manifest-level LLM reasoning.

## 0.2.0

### Breaking Changes

- Both sample agent apps (`samples/agents/agent-framework` and
  `samples/agents/semantic-kernel`) are now excluded from the uv workspace due to
  conflicting transitive dependencies (`azure-ai-projects` version mismatch
  between `agent-framework-core` and `semantic-kernel`). Install them on
  demand with `uv pip install -e samples/agents/agent-framework` or
  `uv pip install -e samples/agents/semantic-kernel`. The `poe sync:maf` and
  `poe sync:sk` tasks handle this automatically.

### Added

- `semantic-kernel` optional extra for `halo-fastapi`
  (`halo-fastapi[semantic-kernel]`).
- `httpx` added to the dev dependency group (previously only available as a
  transitive dependency).
- `tool.uv.conflicts` declaration in root `pyproject.toml` marking the
  `agent-framework` and `semantic-kernel` extras as mutually exclusive.
- Dependency sync instructions added to the READMEs for `halo-fastapi`,
  `samples/agents/agent-framework`, and `samples/servers/fastapi`.

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
- `poe sync:maf` now runs `uv pip install -e samples/agents/agent-framework` after
  `uv sync`, matching the pattern used by `poe sync:sk`.
- VS Code "Sync MAF" task updated to include
  `uv pip install -e samples/agents/agent-framework`.

### Fixed

- `test_all_list_complete` no longer fails when `semantic-kernel` is not
  installed. Lazy-loaded adapters with optional dependencies are skipped
  instead of triggering an import error via `hasattr()`.

## 0.1.0

Initial public release.