# HALO — HTTP API Language for Operations

**`application/llm+json`**

*Self-Describing APIs for LLM Agents*

**Version: 0.3.1-draft**

**Author: Ira Rainey**

## Specification, Implementation & Framework Integration Guide

---

## Table of Contents

### Part I — The HALO Protocol Specification

- [1. The Problem](#1-the-problem)
  - [1.1 How It Works Today](#11-how-it-works-today)
  - [1.2 The Drift Problem](#12-the-drift-problem)
  - [1.3 The Architecture Problem](#13-the-architecture-problem)
  - [1.4 The Proxy Problem](#14-the-proxy-problem)
- [2. The Solution](#2-the-solution)
  - [2.1 The OPTIONS Verb](#21-the-options-verb)
  - [2.2 The Activation Header](#22-the-activation-header)
  - [2.3 The Schema Response](#23-the-schema-response)
  - [2.4 Why Not Use OpenAPI?](#24-why-not-use-openapi)
  - [2.5 Where HALO Applies](#25-where-halo-applies--and-where-it-does-not)
  - [2.6 Error Responses](#26-error-responses)
- [3. Capability Discovery and Filtering](#3-capability-discovery-and-filtering)
  - [3.1 Root Discovery](#31-root-discovery)
  - [3.2 Tag Filtering](#32-tag-filtering)
  - [3.3 Tag Conventions](#33-recommended-tag-conventions)
  - [3.4 Auth-Aware Discovery](#34-auth-aware-discovery)
  - [3.5 Lazy Loading](#35-two-phase-lazy-loading)
  - [3.6 Intent-Based Filtering](#36-intent-based-filtering)
  - [3.7 Caching](#37-caching)
- [4. Authentication](#4-authentication)
  - [4.1 Schema Shape](#41-schema-describes-shape-not-secret)
  - [4.2 Auth-Gated Schemas](#42-auth-gated-schemas)
  - [4.3 Credential Map](#43-agent-credential-map)
- [5. Framework Integration](#5-framework-integration)
  - [5.1 Microsoft Agent Framework](#51-microsoft-agent-framework)
  - [5.2 Semantic Kernel](#52-semantic-kernel)
  - [5.3 LangChain](#53-langchain)
  - [5.4 LlamaIndex](#54-llamaindex)
  - [5.5 Comparison](#55-framework-comparison)
- [6. Full Schema Specification](#6-full-schema-specification)
  - [6.1 Core Fields](#61-core-fields)
  - [6.2 LLM-Native Fields](#62-llm-native-fields)
  - [6.3 Operational Fields](#63-operational-fields)
- [7. Skills vs the OPTIONS Protocol](#7-skills-vs-the-options-protocol)
  - [7.1 Comparison](#71-honest-comparison)
  - [7.2 Skills as Abstraction](#72-skills-as-an-abstraction-layer)
  - [7.3 Where Each Belongs](#73-where-each-belongs)
- [8. Why This Is a Solid Foundation](#8-why-this-is-a-solid-foundation)
  - [8.1 Direct Call Path](#81-direct-call-path-and-zero-operational-overhead)
  - [8.2 Conditional Guarantees](#82-conditional-guarantees)
  - [8.3 Testability](#83-the-schema-is-testable)
  - [8.4 Additional Properties](#84-additional-properties)
- [9. Security Considerations](#9-security-considerations)
  - [9.1 Auth-Gating](#91-auth-gate-discovery-in-production)
  - [9.2 Disclosure](#92-information-disclosure)
  - [9.3 Schema Poisoning](#93-schema-poisoning)
  - [9.4 Prompt Injection](#94-prompt-injection-via-schema-fields)
  - [9.5 Rate Limiting](#95-rate-limiting-discovery)
  - [9.6 Tool Surface Trust](#96-tool-surface-trust)
- [10. What This Replaces](#10-what-this-replaces)
- [11. Prior Art and Naming](#11-prior-art-and-naming)
  - [11.1 HAL vs HALO](#111-the-name-hal-vs-halo)
  - [11.2 Related Standards](#112-related-standards-and-prior-art)

### Part II — The Python Reference Implementation

- [12. Server-Side Implementation](#12-halo-fastapi-server-side-implementation)
  - [12.1 Overview](#121-overview)
  - [12.2 HaloRegister](#122-the-haloregister-plugin)
  - [12.3 How It Works](#123-what-haloregisterapp-actually-does)
  - [12.4 Server Example](#124-complete-server-example)
  - [12.5 Auto-Derived Fields](#125-what-halo-fastapi-derives-automatically)
  - [12.6 Other Languages](#126-implementing-halo-in-other-languages)
  - [12.7 OpenAPI Bridge](#127-openapi-bridge)
- [13. Client-Side Agent Adapter](#13-halo-fastapi-client-side-agent-adapter)
  - [13.1 HaloClient](#131-haloclient-core)
  - [13.2 Internals](#132-what-haloclient-does-internally)
  - [13.3 Credentials](#133-credential-injection)
  - [13.4 Framework Integration](#134-framework-integration)
- [14. Summary](#14-summary)

---

## Licence

Protocol Specification: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
Reference Implementation (`halo-fastapi`): [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)

---

# PART I — The HALO Protocol Specification

*Language and platform agnostic — applicable to any API, any language, any framework*

---

## 1. The Problem

Current approaches to connecting LLM agents to external APIs share a common limitation: the agent-facing description of an API is either maintained separately from the code, or — where it is auto-generated — lacks the LLM-native fields that agents need to reason about tool selection, side effects, and workflow chaining.

Some frameworks auto-generate structural schemas from code (FastAPI's OpenAPI generation, for example, eliminates structural drift for the fields it covers). But even auto-generated OpenAPI is not designed for agent consumption — it lacks fields like `why`, `tags`, `effects`, and `next`, is not served per-endpoint at runtime, and its descriptions are written for human developers, not for LLM reasoning. The remaining approaches — MCP servers, tool registries, skill documents, and agent config files — are secondary artifacts that describe an API but have no binding relationship to it.

### 1.1 How It Works Today

Current agent frameworks — Microsoft Agent Framework, Semantic Kernel, LangChain, and MCP — generally follow a similar pattern:

- A developer writes or decorates a tool definition describing what the API does
- That definition is registered in a tool registry, MCP server, or agent config (some frameworks derive structural schemas from type hints, reducing boilerplate)
- The LLM reads all definitions at inference time and decides which to call
- The framework translates that decision into an actual API call

Even when structural schemas are auto-derived from code, the tool definitions still live in the agent's codebase — separate from the API they describe. Each layer can drift independently. Each adds maintenance overhead.

### 1.2 The Drift Problem

Schema drift is the default outcome of the current approach. The API changes, the tool description does not, and the LLM confidently calls the endpoint with stale parameters. No error surfaces at the description layer — just downstream failures that require log forensics to diagnose. In production systems with dozens of APIs maintained by different teams, this is not an edge case — it is the expected outcome.

When API descriptions are maintained separately from the code — whether as OpenAPI specs, MCP server definitions, or tool descriptions — they tend to diverge over time.

| Problem | Consequence |
|---|---|
| Schema drift | Tool descriptions in registries diverge from the real API as it evolves |
| Version mismatch | The tool description describes v1 behaviour but the API is on v2 |
| Maintenance burden | Every new API requires a new tool wrapper, schema, and registration |
| Token cost | All tool descriptions loaded upfront, consuming context regardless of use |
| Auth complexity | Auth handled separately from discovery, creating synchronisation problems |
| Silent failures | Stale descriptions cause incorrect calls with no schema-level error |

The API already knows everything about itself — inputs, outputs, auth, rate limits, side effects. The problem is that nothing asks it. Every secondary artifact that describes an API is a liability. The API itself is the only source of truth for its structural contract.

### 1.3 The Architecture Problem

Beyond drift, MCP creates a structural architecture problem with two options — neither clean.

**Option A: MCP as a standalone service.** This is the architecturally correct approach — separate codebase, separate deployment, separate lifecycle. It makes sense when the MCP server does real work: reshaping the API surface for LLM consumption, composing multiple backend calls into a single tool, or presenting a fundamentally different abstraction. In these cases, the separate service is justified.

For thin-wrapper MCP servers that only map 1:1 to existing API endpoints, however, the standalone service adds operational overhead with no value beyond protocol translation. HALO targets this space: APIs that are already HTTP endpoints and need to be discoverable by LLM agents without an intermediate service layer.

**Option B: MCP embedded in the API.** This avoids the operational overhead but conflates two distinct responsibilities — serving domain logic and acting as an agent transport layer. These have different reasons to change and different lifecycles. If MCP evolves, is versioned, or is replaced, your domain service has to change with it. In a microservices architecture this contaminates service boundaries that were deliberately drawn.

MCP's in-process stdio transport is a variant of Option B — it avoids the network hop (see section 1.4) but retains the protocol coupling, and the tool descriptions are still maintained as separate artifacts from the code that handles requests.

**Where HALO fits.** An OPTIONS handler is not an external concern added to the API — it is the API describing itself using a standard HTTP mechanism. No new protocol layer is introduced. No new service is required. For MCP servers that do real work or serve consumer clients that require MCP, HALO is complementary, not a replacement (see section 2.5). In the stdio scenario, a HALO-backed MCP server can consume HALO schemas at runtime — reading tool definitions from the API's own OPTIONS endpoints rather than maintaining them as hand-written artifacts.

### 1.4 The Proxy Problem

When deployed as a remote standalone service (not using in-process stdio transport), MCP does not just describe APIs — it proxies calls to them. Every tool invocation by an LLM travels through the MCP server before reaching the actual API. This introduces a network hop that would not otherwise exist.

In isolation, one extra network call seems trivial. In practice it compounds into several distinct problems:

- **Latency** — every tool call carries the overhead of an additional network round-trip through the MCP layer before the real API is reached
- **New failure point** — the MCP server can be down, overloaded, or misconfigured independently of the API it represents. A healthy API can be unreachable because its MCP proxy has failed
- **Harder failure attribution** — when a tool call fails, the error could originate from the LLM, the MCP server, the network between them, or the underlying API. Distributed call chains make root cause analysis significantly harder
- **Timeout stacking** — timeouts compound across hops. A call that would have succeeded directly may fail because the combined MCP-to-API round-trip exceeds a client timeout

HALO has no proxy layer. The LLM agent calls the API directly — OPTIONS to discover, then the real verb to invoke. The call path is two hops: agent to API. Failures are immediately attributable. Latency is the minimum possible. There is no intermediate service to operate or monitor.

---

## 2. The Solution

HALO is a protocol convention — language and platform agnostic — that can be implemented by any HTTP server. Python, Node.js, Go, Java, .NET, Ruby — the protocol has no dependency on any specific runtime, framework, or library.

HALO solves one specific problem: how an LLM agent discovers and invokes HTTP API endpoints as tools. In this context, a "tool" is a REST API endpoint — a URL that accepts a request and returns a response. MCP is a broader protocol that also defines primitives for resources, prompts, sampling, and sessions. HALO does not attempt to replace these capabilities — it targets tool discovery and invocation only, without the protocol and infrastructure overhead that MCP's broader feature set requires (see section 2.5 for applicability).

HTTP has always had the mechanism to fix this. The OPTIONS method has existed since HTTP/1.1. Its semantic meaning is unambiguous: tell me what is possible at this endpoint. Its response body has never been standardised — which means it is effectively unclaimed territory.

### 2.1 The OPTIONS Verb

Every HTTP framework already handles OPTIONS. Every server, proxy, and load balancer passes it through. CORS preflight uses the headers — but the body is untouched. It requires no new infrastructure, no new protocol, and critically no new server process — the handler runs inside the existing API, sharing its deployment, its uptime, and its codebase.

The convention is simple: an LLM agent sends OPTIONS with a custom Accept header to any endpoint. If the server understands the convention, it returns a JSON schema describing that endpoint. If it does not, it returns its normal OPTIONS response. Graceful degradation is built in.

### 2.2 The Activation Header

A custom Accept header acts as the opt-in signal, designed for backward compatibility with existing CORS handling. CORS preflight uses `Access-Control-Request-Method` and `Origin` headers — not `Accept` — so the two mechanisms do not conflict:

```http
OPTIONS /api/payments/charge HTTP/1.1
Host: api.example.com
Accept: application/llm+json
```

Servers that do not implement HALO return a 406 or their standard OPTIONS response. No conflict. No breakage. See section 2.6 for the full error response specification.

> **Media type note:** `application/llm+json` is not a registered IANA media type. It is a custom media type used by this specification as a convention. IANA registration would be a future step if the protocol sees broader adoption. In practice, custom media types with the `+json` suffix are widely used and well-handled by HTTP infrastructure.

### 2.3 The Schema Response

A per-endpoint `OPTIONS` response is always a JSON array — one schema per HTTP method on that path. For a single-method path, this is a one-element array:

```json
[
  {
    "description": "Charge a payment method for a given amount",
    "call":    { "method": "POST", "url": "/api/payments/charge" },
    "auth":    { "type": "bearer", "scopes": ["payments:write"] },
    "input":   {
      "amount":      { "type": "number", "required": true, "description": "Amount in pence" },
      "currency":    { "type": "string", "enum": ["GBP","USD","EUR"], "required": true },
      "customer_id": { "type": "string", "required": true }
    },
    "output":  { "charge_id": { "type": "string" }, "status": { "type": "string" } },
    "why":     "Use to charge a customer immediately. Prefer /authorise for pre-auth flows.",
    "effects": { "reversible": true, "undo": "/api/payments/refund" },
    "limits":  { "rate": "100/hour", "idempotent": false },
    "tags":    ["payments", "write"],
    "next": [
      { "when": "status=pending", "suggest": "/api/payments/confirm" },
      { "when": "status=failed",  "suggest": "/api/payments/retry" }
    ],
    "examples": [
      {
        "input":  { "amount": 1000, "currency": "GBP", "customer_id": "cust_123" },
        "output": { "charge_id": "ch_456", "status": "success" }
      }
    ]
  }
]
```

The server must respond with `Content-Type: application/llm+json`.

### 2.4 Why Not Use OpenAPI?

This is the most common question about HALO. OpenAPI is a mature, well-tooled standard. Many frameworks auto-generate it from code. Some agent frameworks (LangChain, for example) already ship converters that transform OpenAPI specs into tool definitions. For basic tool calling with a small, stable API, **OpenAPI can work** — and HALO does not claim otherwise.

The question is not whether OpenAPI describes APIs — it does, comprehensively — but whether it describes them *for LLM agents specifically, at runtime, in a way that scales*. The gaps that emerge are real but nuanced, and where OpenAPI has a fair counter-argument, it is noted.

#### The Specific Gaps

**1. OpenAPI is monolithic — HALO is granular.**

An OpenAPI spec is served as a single document. The OpenAPI 3.x specification defines no standard mechanism for requesting a subset by tag, method, or path — the full document is always served. OpenAPI has a `tags` concept, but tags are purely for documentation grouping used by tools like Swagger UI. They have no runtime filtering semantics.

> A client can filter by OpenAPI tags after fetching the spec. This is trivial to implement. The HALO advantage is specifically *server-side* filtering (`OPTIONS /?tags=payments`) combined with *lazy per-endpoint schema loading* — the agent never receives tool definitions it did not ask for, and full schemas are fetched only when the LLM selects a tool.

**2. OpenAPI descriptions are written for humans, not LLMs.**

Every major LLM provider uses the same core structure for tool definitions: a name, a description, and parameters as JSON Schema ([OpenAI](https://platform.openai.com/docs/guides/function-calling), [Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview), [Google Gemini](https://ai.google.dev/gemini-api/docs/function-calling)). No provider natively accepts an OpenAPI specification — all require conversion.

OpenAPI provides the base fields these formats require: `operationId` maps to name, `summary`/`description` map to description, and request body schemas provide parameters. **For basic tool calling, this works.** But there is a subtler problem: OpenAPI descriptions are written for human developers reading documentation, not for LLMs selecting tools. Consider the difference:

- **OpenAPI description** (for a developer): *"Processes payment transactions using the Stripe billing integration with support for multi-currency settlements."*
- **HALO `why` field** (for an LLM): *"Use to charge a customer immediately after order confirmation. Prefer /authorise if the charge amount may change before capture."*

These serve different audiences. The OpenAPI description explains what the endpoint does and how it is implemented. The `why` field tells the LLM *when to choose this tool over alternatives* — routing guidance, not documentation. Trying to write one description that serves both results in serving neither well. HALO separates these concerns: the `description` field (derived from the docstring) serves human readers, while `why` serves the LLM.

Beyond descriptions, OpenAPI lacks fields that help an LLM reason about tool selection entirely:

| HALO field | Purpose | OpenAPI 3.x equivalent |
|---|---|---|
| `why` | Routing hint: when to choose this tool over alternatives | None |
| `effects` | Side effects, reversibility, undo endpoint | None |
| `next` | Conditional workflow chaining | `Link Object` (partial — no conditional `when` clauses) |
| `limits` | Rate limits, idempotency | None |
| `resilience` | Retry strategy, timeout, fallback endpoint | None |
| `trust` | Schema signing and verification | None |
| `observe` | Trace header injection, audit logging | None |

> OpenAPI supports vendor extensions (`x-*`), so a team could define `x-llm-why`, `x-llm-effects`, etc. The mechanism to carry these fields exists. The difference is that HALO defines a *standard schema* for these fields — consistent naming, consistent structure, consistent tooling across implementations. Vendor extensions are ad-hoc by definition: every team invents its own convention, no framework knows how to consume them, and no contract exists between producer and consumer. HALO standardises what `x-*` leaves open.

**3. OpenAPI requires non-trivial transformation for LLM consumption.**

Converting an OpenAPI spec to tool definitions requires resolving `$ref` pointers, merging path/query/body parameters into a single flat object, navigating 7–8 levels of nesting, and synthesising names from `operationId`. Frameworks like LangChain ship converters that handle this, so the burden is not necessarily per-project — but it is a transformation layer that must be maintained as both OpenAPI and the framework evolve.

HALO schemas are flat, self-contained, and designed to be directly consumable — no dereferencing, no merging, no nesting traversal.

**4. OpenAPI discovery is not auth-scoped.**

An OpenAPI spec is the same document regardless of who requests it. There is no standard mechanism for serving a filtered spec based on the caller's permissions. HALO's root manifest varies per request based on the authentication token — a read-only caller discovers only read endpoints. (See section 3.4.)

#### Honest Assessment

| Dimension | OpenAPI | HALO | Notes |
|---|---|---|---|
| Structural schema accuracy | High (when auto-generated) | High (derived from same code) | Comparable |
| Description audience | Written for human developers | Separate `description` (human) and `why` (LLM) | HALO serves both audiences without compromise |
| LLM-native reasoning fields | None (extensible via `x-*`) | Standardised: `why`, `effects`, `next`, `limits`, etc. | HALO standardises what `x-*` leaves ad-hoc |
| Granularity | Monolithic (client-side filtering possible) | Per-endpoint + server-side tag filtering | HALO avoids loading unused schemas entirely |
| Transformation for LLM use | Non-trivial (libraries exist) | Direct consumption — flat, self-contained | Solved problem vs no-problem |
| Auth-scoped discovery | Not supported | Built-in — manifest varies by caller | HALO wins |
| Tooling ecosystem | Excellent — Swagger UI, code generators, validators | Early — reference implementation only | OpenAPI wins |
| Industry adoption | Ubiquitous | New | OpenAPI wins |
| Complementary use | Can coexist with HALO | Can coexist with OpenAPI | Not mutually exclusive |

OpenAPI is a comprehensive API description standard with a mature ecosystem. For basic tool calling with small, stable APIs, converting OpenAPI to tool definitions works. HALO is designed for the use case OpenAPI was not: runtime, per-endpoint, auth-scoped discovery with standardised LLM-native reasoning fields. The two are complementary — a FastAPI application can serve both simultaneously, and `halo-fastapi` includes an OpenAPI bridge (section 12.7) for teams transitioning between them.

### 2.5 Where HALO Applies — and Where It Does Not

Consumer LLM clients — ChatGPT, GitHub Copilot, Claude Desktop, Cursor, Windsurf — are coupled to MCP (or proprietary equivalents) for tool integration. HALO cannot be used directly with these clients. They do not support arbitrary HTTP tool-calling protocols, and there is no mechanism to add one.

HALO cannot bypass the MCP coupling in consumer clients. For teams whose only use case is exposing tools to ChatGPT or Copilot, MCP is the required protocol. HALO's value in that scenario is as a drift-free backing store for an MCP server's tool definitions — not as a replacement for MCP itself.

**HALO's primary audience is developer-built agent systems** — applications where the developer controls the agent runtime and chooses how tools are discovered and invoked. This includes:

- Custom agents built with Microsoft Agent Framework, Semantic Kernel, LangChain, or LlamaIndex
- Backend agent orchestration and multi-agent systems
- Server-side automation where agents call APIs programmatically

For consumer client compatibility, the MCP bridge pattern (described in section 1.3) provides a path: a lightweight MCP server that reads its tool definitions from HALO schemas at runtime rather than maintaining them as hand-written artifacts. This gives last-mile clients like Copilot and Claude Desktop access to HALO-described APIs through MCP, while the API owner maintains a single source of truth via HALO. The MCP server becomes a thin protocol translator with no hand-written tool definitions to maintain.

HALO assumes the agent already knows the base URL of each API it connects to. The protocol describes how to discover tools *within* a known API, not how to discover *which APIs exist*. This is the same limitation as MCP (which requires server URLs to be configured) and OpenAPI (which requires the spec URL). Multi-API discovery — a registry of HALO-compliant APIs — is outside the current scope.

### 2.6 Error Responses

HALO uses standard HTTP status codes. No custom error format is required.

| Scenario | Response |
|---|---|
| OPTIONS with `Accept: application/llm+json` on a HALO-enabled endpoint | `200` with `application/llm+json` body |
| OPTIONS without the HALO accept header | `204 No Content` (standard OPTIONS behaviour) |
| OPTIONS with `Accept: application/llm+json` on a non-HALO server | `406 Not Acceptable` or the server's standard OPTIONS response |
| OPTIONS on a path that does not exist | `404 Not Found` — standard HTTP, no HALO-specific handling |
| OPTIONS with unrecognised or malformed tag query | Server should ignore unrecognised tags and return matching tools. If no tools match, return an empty `tools` array — not an error. |
| OPTIONS without required auth credentials | `401 Unauthorized` — standard HTTP |
| OPTIONS with insufficient permissions | `403 Forbidden` or an empty manifest (auth-aware discovery returns only permitted tools) |

Implementations should not invent HALO-specific error codes or error body formats. Standard HTTP semantics apply throughout.

---

## 3. Capability Discovery and Filtering

### 3.1 Root Discovery

A single OPTIONS request to the base URL returns a manifest of all available endpoints including their name, description, and tags:

```http
OPTIONS / HTTP/1.1
Host: api.example.com
Accept: application/llm+json
```

```json
{
  "api": "Example Payments API",
  "version": "2.1.0",
  "description": "Payment processing, customer management, and communications for the Example platform.",
  "tools": [
    { "url": "/api/payments/charge",   "method": "POST", "name": "charge",  "description": "Charge a payment method",          "tags": ["payments", "write"] },
    { "url": "/api/payments/refund",   "method": "POST", "name": "refund",  "description": "Refund a previous charge",          "tags": ["payments", "write"] },
    { "url": "/api/customers/lookup",  "method": "GET",  "name": "lookup",  "description": "Look up customer details",           "tags": ["customers", "read"] },
    { "url": "/api/email/send",        "method": "POST", "name": "send",    "description": "Send an email to a recipient",       "tags": ["comms", "write"] },
    { "url": "/api/admin/users",       "method": "POST", "name": "users",   "description": "Manage admin user accounts",         "tags": ["admin", "write"] }
  ]
}
```

The `description` field on the manifest gives the LLM (or a multi-API orchestrator) enough context to decide whether this API is relevant to the current task before examining individual tools.

### 3.2 Tag Filtering

The client passes tags as a query parameter to receive only the relevant subset of tools:

```http
# Discover only payment tools
OPTIONS /?tags=payments

# Discover only safe read operations
OPTIONS /?tags=read

# Discover tools matching any of the specified tags (OR semantics)
# Matching is case-sensitive. Tags are comma-delimited.
OPTIONS /?tags=payments,read
```

Tag filtering is most useful when the agent is **pre-configured** with the tags it cares about — a payment agent calls `OPTIONS /?tags=payments` and never sees unrelated tools. For general-purpose agents discovering an unknown API, the unfiltered manifest from `OPTIONS /` is lightweight (names, descriptions, and tags only — no full schemas) and the LLM can select relevant tools directly from the response without a second filtered call.

> **Note on API design:** Well-designed microservices following domain-driven design naturally have narrow, focused tool surfaces. A payments service exposes payment operations; a customer service exposes customer operations. For these APIs, tag filtering may be unnecessary — the API surface is already scoped by design. Tag filtering becomes more valuable for larger monolithic APIs or APIs that span multiple domains.

This solves three problems simultaneously:

| Problem Solved | How |
|---|---|
| Token efficiency | The LLM context only contains tools relevant to the current task, not the entire API surface |
| Agent specialisation | A payment agent, comms agent, and admin agent all point at the same API but each sees only its own slice — no separate registrations needed |
| Reduced tool surface | A read-only agent configured to request `OPTIONS /?tags=read` never discovers write tools in its context. This is advisory — not enforced. For true least-privilege, combine tag filtering with auth-gated discovery (section 3.4) so the server only returns tools the caller's credentials permit |

### 3.3 Recommended Tag Conventions

Tags are free-form strings. The following conventions are recommended as a baseline:

| Tag | Meaning |
|---|---|
| `read` | Safe, non-mutating operations |
| `write` | Creates or modifies data |
| `delete` | Removes data — treat with caution |
| `admin` | Elevated privilege required |
| `async` | Returns immediately, result arrives later |
| `expensive` | High cost per call — use sparingly |
| `realtime` | Requires live connection |

### 3.4 Auth-Aware Discovery

When credentials are passed with the root OPTIONS request, the manifest reflects only what those credentials permit:

```json
// Read-only token:
{ "tools": [
  { "url": "/api/customers/lookup", "method": "GET", "name": "lookup", "description": "Look up customer details", "tags": ["customers","read"] }
] }

// Full-access token:
{ "tools": [
  { "url": "/api/payments/charge",  "method": "POST", "name": "charge", "description": "Charge a payment method",   "tags": ["payments","write"] },
  { "url": "/api/customers/lookup", "method": "GET",  "name": "lookup", "description": "Look up customer details",  "tags": ["customers","read"] },
  { "url": "/api/admin/users",      "method": "POST", "name": "users",  "description": "Manage admin user accounts", "tags": ["admin","write"] }
] }
```

The LLM never learns that restricted tools exist.

### 3.5 Two-Phase Lazy Loading

Lazy loading separates tool *selection* from tool *invocation*. The manifest provides enough information (name, description, tags) for the LLM to choose which tool is relevant. The full schema (input parameters, auth, effects) is fetched only after selection, and a second LLM call constructs the actual request using the schema.

```
Agent starts
   │
   ├── OPTIONS /?tags=payments     ← manifest (pre-configured tags)
   │   ← { tools: [charge, refund] }
   │
   │   LLM call 1: "Charge customer £25"
   │   LLM selects: charge (based on name + description)
   │
   ├── OPTIONS /payments/charge    ← full schema array: [{input, auth, effects}]
   │   ← [{ input: {amount, currency, customer_id}, auth: bearer }]
   │
   │   LLM call 2: construct request using schema
   │   LLM outputs: {amount: 2500, currency: "GBP", customer_id: "cust_123"}
   │
   └── POST /payments/charge       ← actual call — direct, no proxy
       ← { charge_id, status }
```

Five interactions: manifest fetch, tool selection (LLM), schema fetch, request construction (LLM), and invocation. On subsequent calls to the same tool, the schema is cached and only the second LLM call is needed.

### 3.6 Intent-Based Filtering

For general-purpose agents that don't know which tools are relevant in advance, the manifest itself provides enough information for the LLM to select:

```python
async def discover_for_task(task: str, base_url: str) -> list:
    # Step 1: fetch manifest — names and descriptions only
    manifest = await options(base_url)

    # Step 2: ask the LLM which tools are relevant to the task
    relevant = await llm.invoke(f"""
        Task: "{task}"
        Available tools: {manifest['tools']}
        Return only the URLs of relevant tools as a JSON array.
        """)

    # Step 3: lazy-load full schemas only for selected tools
    return [await options(url) for url in relevant]
```

Two calls per selected tool: one manifest fetch, then one schema fetch per tool the LLM chose. No redundant filtered discovery call — the manifest is lightweight enough for the LLM to reason over directly.

### 3.7 Caching

The HTTP call costs described above are cold-start costs. In practice, APIs do not change frequently, and both manifests and per-endpoint schemas should be cached at the agent level.

The `HaloClient` reference implementation caches schemas in memory — `get_tool()` fires OPTIONS once per path per session. Implementations should also support HTTP-level caching using standard mechanisms:

- **`Cache-Control`** — the server can set `max-age` on OPTIONS responses to indicate how long schemas remain valid
- **`ETag` / `If-None-Match`** — the client caches schemas with their ETag and revalidates with `If-None-Match` on subsequent requests. If unchanged, the server returns `304 Not Modified` with no body

With caching in place, the common-case flow for a warm agent is: zero HTTP calls for cached schemas, one LLM call to construct the request, one HTTP call to invoke the endpoint. The multi-call lazy loading sequence only applies on first use or after cache invalidation.

> **Protocol recommendation:** Server implementations should set `Cache-Control` and `ETag` headers on `application/llm+json` responses. This is standard HTTP behaviour and requires no HALO-specific mechanism.

---

## 4. Authentication

### 4.1 Schema Describes Shape, Not Secret

The OPTIONS response describes the authentication shape required. Actual credentials live in the agent's secure context and are injected at call time.

| Auth Type | Schema Field | Agent Behaviour |
|---|---|---|
| bearer | `"type": "bearer"` | Inject `Authorization: Bearer {token}` |
| api key | `"type": "apikey", "header": "X-API-Key"` | Inject key into named header |
| oauth | `"type": "oauth", "scopes": ["read:data"]` | Handle flow, inject resulting token |
| basic | `"type": "basic"` | Base64-encode stored credentials |

### 4.2 Auth-Gated Schemas

For APIs where the tool list itself is sensitive, credentials can be required to retrieve the schema (see section 9.1).

### 4.3 Agent Credential Map

```json
{
  "api.stripe.com":    { "type": "bearer", "value": "${STRIPE_KEY}" },
  "api.sendgrid.com":  { "type": "apikey", "header": "X-API-Key", "value": "${SG_KEY}" },
  "api.github.com":    { "type": "bearer", "value": "${GITHUB_TOKEN}" }
}
```

The LLM never handles secrets directly — it decides what to call, the runtime injects the credential.

---

## 5. Framework Integration

Any HALO implementation — regardless of language — needs to map the protocol's schema fields to the tool primitive of the target agent framework. The core adapter logic is always the same three steps: discover via `OPTIONS /`, fetch schema via `OPTIONS /route`, invoke via the real HTTP verb. The wrapping layer is the only thing that varies per framework.

> **Implementation note:** The code examples in this section use Python for consistency with the reference implementation described in Part II, but the same adapter pattern applies in any language. `HaloAgentFrameworkAdapter` and `HaloSemanticKernelAdapter` are implemented in `halo-fastapi` for Microsoft Agent Framework and Semantic Kernel respectively. The remaining adapter classes (`HaloLangChainAdapter`, `HaloLlamaIndexAdapter`) illustrate the target integration pattern for other frameworks but are not yet implemented.

### 5.1 Microsoft Agent Framework

```python
from halo_fastapi import HaloClient, HaloAgentFrameworkAdapter
import agent_framework

# 1. Discover HALO tools
client = await HaloClient(
    base_url='https://api.example.com',
    bearer_token=token,
).discover(tags=['payments'])

# 2. Convert to Agent Framework FunctionTools
adapter = HaloAgentFrameworkAdapter(client)
tools = await adapter.create_tools()

# 3. Create and run the agent
agent = agent_framework.Agent(
    client=chat_client,
    name='payment-agent',
    tools=tools,
)
```

### 5.2 Semantic Kernel

```python
from halo_fastapi import HaloClient, HaloSemanticKernelAdapter
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

kernel = Kernel()
kernel.add_service(AzureChatCompletion(service_id='chat', ...))

# Discover HALO tools and build a Semantic Kernel plugin
client = await HaloClient('https://api.example.com', bearer_token=token).discover(tags=['payments'])
adapter = HaloSemanticKernelAdapter(client)
plugin = await adapter.create_plugin()  # KernelPlugin
kernel.add_plugin(plugin)

result = await kernel.invoke_prompt('Charge customer cust_123 £25')
```

The adapter wraps each discovered HALO tool as a ``@kernel_function``-decorated async function inside a ``KernelPlugin``. The ``why`` field becomes the function description, enabling Semantic Kernel's automatic function calling via ``FunctionChoiceBehavior.Auto()``.

### 5.3 LangChain

```python
adapter = HaloLangChainAdapter('https://api.example.com', credentials)
tools = await adapter.create_tools(tags=['payments'])

agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
result = await executor.ainvoke({'input': 'Charge customer £25'})
```

### 5.4 LlamaIndex

```python
from llama_index.core.agent import ReActAgent
from halo_fastapi import HaloLlamaIndexAdapter

adapter = HaloLlamaIndexAdapter(
    base_url='https://api.example.com',
    credentials=credentials
)
tools = await adapter.create_tools(tags=['payments'])

agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)
response = agent.chat('Send a welcome email to the new customer')
```

### 5.5 Framework Comparison

| Framework | Tool Primitive | Key Pattern | Notable Mapping |
|---|---|---|---|
| Microsoft Agent | `FunctionTool` | Agent Framework tools | `create_tools()` builds tools from schema |
| Semantic Kernel | `KernelFunction` | Central kernel, plugins | `why` → description, `next` → planner hints |
| LangChain | `BaseTool / StructuredTool` | Toolkit pattern | Pydantic `ArgsSchema` from input fields |
| LlamaIndex | `FunctionTool` | `ToolMetadata` object | Pydantic schema from input fields |

---

## 6. Full Schema Specification

### 6.1 Core Fields

**Manifest fields** (root `OPTIONS /` response):

| Field | Purpose |
|---|---|
| `api` | Name of the API |
| `version` | API version string |
| `description` | What this API does — helps LLMs decide whether to explore its tools |
| `tools` | Array of tool entries (see below) |

**Tool entry fields** (each element in the `tools` array):

| Field | Required | Purpose |
|---|---|---|
| `url` | Yes | Endpoint path |
| `method` | Yes | HTTP method (GET, POST, etc.) |
| `name` | Yes | Short human-readable tool name |
| `description` | Yes | What the tool does |
| `tags` | No | Tags for filtering (defaults to empty array) |

**Per-endpoint fields** (`OPTIONS /route` response):

Each HALO schema describes a single method on a single path. The `call.method` and `call.url` fields together identify the operation. When a path supports multiple HTTP methods (e.g. `GET /resource` and `POST /resource`), the `OPTIONS /resource` response should return an array of schemas — one per method:

```json
[
  { "call": { "method": "GET",  "url": "/resource" }, "description": "Retrieve a resource", ... },
  { "call": { "method": "POST", "url": "/resource" }, "description": "Create a resource", ... }
]
```

When only one method exists on the path (the common case), the response is still a one-element array for consistency.

| Field | Purpose |
|---|---|
| `description` | Natural language description of what the endpoint does |
| `call.method` | HTTP verb: GET, POST, PUT, PATCH, DELETE |
| `call.url` | Endpoint URL — relative or absolute |
| `auth` | Auth shape: type, header name, required scopes |
| `input` | JSON Schema describing request parameters |
| `output` | JSON Schema describing the response structure |
| `tags` | Array of strings for filtering and agent scoping |

### 6.2 LLM-Native Fields

These fields exist to improve LLM reasoning and routing. Most have no direct equivalent in OpenAPI or MCP tool schemas (see section 2.4 for a detailed comparison).

| Field | Purpose |
|---|---|
| `why` | Routing hint for LLM selection — when to use this vs alternatives |
| `effects.reversible` | Boolean. Action can be undone. |
| `effects.undo` | URL of the endpoint that reverses this action. |
| `limits.rate` | Rate limit — e.g. `100/hour`. Enables agent to debounce or batch. |
| `limits.idempotent` | Boolean. Calling twice has the same effect as calling once. |
| `next` | Conditional next-step suggestions: `[{ when, suggest }]`. Enables workflow chaining. |
| `examples` | Concrete input/output examples. Most reliable way to ensure correct call construction. |

### 6.3 Operational Fields

| Field | Purpose |
|---|---|
| `resilience.retry` | Boolean. Agent should retry on failure. |
| `resilience.backoff` | Backoff strategy: `linear`, `exponential`, `none`. |
| `resilience.timeout_ms` | Expected maximum response time in milliseconds. |
| `resilience.fallback` | URL of a fallback endpoint if this one fails. |
| `trust.signed` | Boolean. Schema is cryptographically signed. |
| `trust.jwks` | URL of JWKS endpoint for signature verification. |
| `status` | Lifecycle: `active`, `deprecated`, `sunset`. |
| `sunset` | ISO date when deprecated endpoint will be removed. |
| `replace_with` | URL of the replacement endpoint. |
| `observe.trace_header` | Header name for trace ID injection. |
| `observe.explain` | Boolean. Agent should include a call reason header for audit. |

---

## 7. Skills vs the OPTIONS Protocol

Skills — structured descriptions of business rules, domain knowledge, and tool orchestration logic — are an increasingly important layer in agent architecture. Understanding where skills and protocol-level tool description each belong is critical to building a well-structured agent system.

### 7.1 Honest Comparison

For most dimensions, skills win. They are faster to create, more expressive, and more flexible. The protocol's advantages are narrow but important: structural accuracy, automated auth detection, and explicit failure modes.

| Dimension | Skills | OPTIONS Protocol | Winner |
|---|---|---|---|
| Implementation effort | Write text — minutes | Add OPTIONS handler — hours | Skills |
| Expressiveness | Natural language — can capture business rules, edge cases, judgment | Structural JSON schema — mechanical fields only | Skills |
| Multi-source orchestration | Can compose tools from APIs, MCP servers, scripts, and other sources into cohesive workflows | Describes individual HTTP endpoints only | Skills |
| Domain knowledge | SMEs can draft and maintain skills without touching code | Requires developer involvement for LLM-native fields | Skills |
| Behavioural guidance | Natural — text is expressive | Not possible — schemas are structural | Skills |
| Structural accuracy | As good as the author — can drift silently | Structural fields always correct — derived from code | Protocol |
| Auth description | Prose — easy to get wrong | Detected and typed automatically | Protocol |
| Validation | None — it is text | Testable in CI against live endpoint | Protocol |
| Failure mode | Silent incorrect calls | Explicit 400/422 with structured error | Protocol |
| Token cost | All loaded upfront always | Lazy, filtered, on demand | Protocol |

### 7.2 Skills as an Abstraction Layer

The industry is moving towards skills as a higher-level abstraction above raw tool definitions. In this model, skills capture business rules and domain knowledge, and orchestrate tools from multiple sources — API endpoints, MCP servers, scripts — behind a single cohesive interface. The LLM interacts with the skill, not directly with the underlying tools.

In this architecture, the drift concern changes shape. When a skill mediates between the LLM and the underlying tools, the separation between skill author (often a domain expert) and tool implementer (a developer) becomes a deliberate decoupling — not an accidental liability. The skill author describes *what should happen* in business terms; the developer ensures the tools *work correctly* at the mechanical level.

HALO's LLM-native fields (`why`, `effects`, `next`) occupy the space between these two layers. In a skills-first architecture, these fields may be less relevant to the LLM — which sees skills, not raw tools — but remain valuable in the developer loop: they document the API's behaviour for the skill author, and they provide structured metadata that skill orchestration engines can consume programmatically.

HALO describes what each API endpoint does, mechanically and precisely. Skills describe what the agent should do, contextually and expressively. When skills orchestrate HALO-described tools, the combination gives the skill author a precise, drift-free contract to build on — rather than prose documentation that may be stale.

### 7.3 Where Each Belongs

| Approach | What It Handles |
|---|---|
| Skills | Business rules, domain knowledge, judgment, edge cases, tone. Things that require context and expressiveness. |
| OPTIONS Protocol | Mechanical capability — what a single API endpoint does, exactly how to call it, what auth it needs, what side effects it has. Things that must be precise and must stay in sync with the live system. |

> **Key principle:** Skills and schemas are not competing alternatives — they operate at different layers. Skills describe *what the agent should do*. Schemas describe *what the API can do*. When both are in skills the system is fragile at the mechanical layer. When both are in schemas the system is rigid at the behavioural layer. The combination is where the system becomes robust.

---

## 8. Why This Is a Solid Foundation

### 8.1 Direct Call Path and Zero Operational Overhead

HALO's architectural advantages — no proxy layer, no sidecar service, direct agent-to-API call path — are detailed in sections 1.3 and 1.4. The key property is that schema accuracy and zero operational overhead are the same thing: because the HALO handler lives inside the API, it cannot be separately broken, separately outdated, or separately unavailable.

### 8.2 Conditional Guarantees

HALO's core guarantees — no structural drift, no additional service, direct call path — are conditional on the API implementing the protocol natively. When an API serves its own HALO schema from inside its own process, these properties hold by construction.

For third-party APIs you do not control, it is technically possible to write a proxy that serves HALO schemas on behalf of the upstream API. This reintroduces drift risk (the schema is no longer derived from the same code) and operational overhead (an additional service to maintain). This is no different from the problems HALO solves for native implementations — it is simply the unavoidable cost of describing an API you do not own. Treat the proxy pattern as a last resort for legacy or third-party integrations where native adoption is not possible.

### 8.3 The Schema Is Testable

Because the schema lives on an HTTP endpoint it can be validated in CI:

```bash
curl -X OPTIONS https://api.example.com/payments/charge \
     -H 'Accept: application/llm+json' | jq .
```

Catch drift before it reaches production. Static schema files (like OpenAPI specs) can also be validated in CI, but they test the *file* — not the live endpoint. HALO's testability advantage is that the schema under test is the same one agents will receive at runtime.

### 8.4 Additional Properties

| Property | Detail |
|---|---|
| Version control | When the API changes, the OPTIONS response changes with it — same deployment, same commit, same version. Structural fields are derived from code and cannot describe v1 behaviour while the API is on v2. The drift caveat for LLM-native fields is covered in section 7.2. |
| Observability | OPTIONS requests appear in existing access logs. Agents can be monitored, rate-limited, and traced using the existing observability stack. |
| Trust boundary | OPTIONS responses come from the same authenticated server as the API calls themselves — consistent security perimeter (section 9.1). |
| Familiar primitive | OPTIONS is a well-established HTTP method with clear semantics. No novel mechanism to learn. |
| Multi-tenant scoping | Auth-scoped discovery (section 3.4) means different callers see different tool manifests. |
| API owner control | An API that serves `application/llm+json` from OPTIONS declares: *I am ready to be used by machines, on my own terms.* |

---

## 9. Security Considerations

HALO's OPTIONS handlers expose API metadata — endpoint paths, parameter names and types, auth requirements, rate limits, side effects, and workflow hints. This is the same information carried by any tool description mechanism (OpenAPI specs, MCP tool definitions, skill documents). The security implications are not unique to HALO, but they are worth calling out explicitly.

### 9.1 Auth-Gate Discovery in Production

If the API itself requires authentication, the OPTIONS handlers should too. An unauthenticated OPTIONS endpoint on an authenticated API creates an information asymmetry — callers who cannot invoke endpoints can still discover them.

The mitigation is straightforward: require the same credentials for discovery that the API requires for invocation. HALO's auth-aware discovery (section 3.4) already supports this — when credentials are passed with the OPTIONS request, the manifest reflects only what those credentials permit. In production, this should be the default, not an optional enhancement.

> **Recommendation:** If your API requires authentication, require it on OPTIONS as well. The `tool_filter` callback in `HaloRegister` (or equivalent in other implementations) can enforce this at the handler level. This is the same principle as any production system — do not expose metadata to callers who cannot act on it.

### 9.2 Information Disclosure

Without auth-gating, OPTIONS handlers expose the full API surface to any client that sets `Accept: application/llm+json`. This includes endpoint paths, parameter schemas, auth types, rate limits, and — via `effects.undo` and `next` — relationships between endpoints that reveal internal workflow logic.

This is not a HALO-specific concern. An OpenAPI spec, an MCP server's tool list, or a skill document all expose the same information. The difference is that HALO serves this information from the live API rather than a separate file or service. Auth-gating OPTIONS requests (section 9.1) addresses this directly.

### 9.3 Schema Poisoning

If a HALO-compliant API is compromised or intercepted, the `next` and `effects.undo` fields could redirect an agent to malicious endpoints. The `why` and `description` fields could be altered to influence tool selection in unintended ways.

This is a transport-level concern, not a HALO-specific one. Any source of tool definitions consumed by an LLM — MCP tool descriptions, OpenAPI specs, skill documents — is subject to the same risk if the source is compromised. The mitigations are standard:

- **TLS** — ensures schema responses are not tampered with in transit
- **Schema signing** — HALO's `trust.signed` and `trust.jwks` fields (section 6.3) allow cryptographic verification of schema integrity
- **Source trust** — if you trust the API enough to call it, you are already trusting its self-description. HALO's trust boundary is consistent: the schema and the endpoint share the same security perimeter (section 9.1)

### 9.4 Prompt Injection via Schema Fields

The `why`, `description`, and `examples` fields are free text consumed by the LLM. A malicious or compromised API could embed adversarial instructions in these fields that influence agent behaviour beyond the intended scope — for example, instructing the LLM to ignore its system prompt or call unrelated tools.

This is inherent to LLM tool consumption, not specific to HALO. Every tool description mechanism — MCP, OpenAPI, LangChain tools, skills — carries free-text fields that the LLM interprets. The mitigations are the same as for any LLM system that consumes external input:

- Treat schema content as untrusted input in the agent's prompt construction
- Apply output filtering and validation on the agent side
- Use auth-gated discovery to ensure schemas only come from trusted, authenticated sources

### 9.5 Rate Limiting Discovery

OPTIONS requests are cheap to serve but could be abused for endpoint enumeration or discovery-based denial of service. Standard rate limiting applies — the same controls used for any API endpoint. HALO's OPTIONS handlers appear in existing access logs and can be rate-limited separately from invocation using standard middleware.

### 9.6 Tool Surface Trust

A server trusted today could add new tools tomorrow. The agent discovers them automatically — no human approval required. This creates two risks:

- **Surface expansion** — new tools appear between discovery calls. An agent that trusted five tools yesterday now sees six. The sixth could perform actions the consumer never anticipated.
- **Tool shadowing** — a server adds a tool whose name or description competes with tools from other servers. The LLM selects based on description quality, not provenance, so a well-described malicious tool can displace a legitimate one.

This is not HALO-specific. MCP's `tools/list` returns whatever the server chooses at call time, with the same exposure. OpenAPI specs are slightly less dynamic in practice but carry the same risk when re-fetched.

Mitigations are consumer-side:

- **Manifest pinning** — snapshot the manifest and diff on re-discovery; alert or block on new or changed tools
- **Tool allowlists** — maintain a list of approved tool URLs and ignore additions until explicitly approved
- **Schema signing** (section 9.3) — covers integrity of existing tools but does not prevent new tools from appearing

---

## 10. What This Replaces

HALO replaces the tool discovery and invocation layer — not the full scope of MCP (see scope note in section 2).

| Current World | With HALO |
|---|---|
| MCP server process (remote) | OPTIONS handler runs inside the existing API — no sidecar, no separate deployment. (When MCP is embedded in-process, both share the same deployment.) |
| Separation of concerns violation | OPTIONS is a native HTTP mechanism — self-description is not a separate concern |
| MCP proxy layer (remote) | Agent calls the API directly — no intermediate network hop. (Embedded MCP also avoids the extra hop, but retains protocol coupling — see section 1.3.) |
| Tool registry with hand-written definitions | The API is the registry. Root OPTIONS returns the full manifest. Tool definitions are derived from code, not maintained separately. (MCP also supports dynamic tool lists via `tools/list` and `list_changed` notifications — the difference is where the definitions originate, not whether they can update.) |
| Schema files (OpenAPI) | Schema lives on the route itself, versioned with the code |
| Structural schema drift | Eliminated for auto-derived fields — schema is generated from the code that handles requests. LLM-native fields (`why`, `tags`, `effects`) are co-located but still hand-written. |
| Auth in tool config | Auth shape served with schema, secrets in agent credential map |
| Hardcoded retry logic | `resilience` fields declare the API's own retry contract |
| Workflow definitions | `next` field creates emergent workflows from API metadata |
| Skill separation | In a skills-first architecture, the separation between skill (business logic) and tool (mechanical contract) is a deliberate decoupling benefit, not a drift liability. HALO provides the precise contract that skills build on (see section 7.2). |

---

## 11. Prior Art and Naming

### 11.1 The Name: HAL vs HALO

The most important naming consideration is HAL — Hypertext Application Language — a well-established hypermedia standard from 2012 with the media type `application/hal+json`. The similarity to HALO and `application/llm+json` is close enough to require explicit differentiation.

| | HAL | HALO |
|---|---|---|
| Full name | Hypertext Application Language | HTTP API Language for Operations |
| Media type | `application/hal+json` | `application/llm+json` |
| Purpose | Hypermedia navigation — linking resources together in API responses | Capability discovery — describing how to call an endpoint to an LLM agent |
| Mechanism | Links embedded in response bodies for human and machine navigation | OPTIONS request returns schema before any call is made |
| Consumer | HTTP clients navigating resource graphs | LLM agents discovering and invoking tools |
| Relationship | Complementary — a HAL API could also implement HALO | — |

HAL and HALO are not competing standards. A REST API using HAL for hypermedia navigation could simultaneously implement HALO for LLM capability discovery. They operate at different layers and serve different consumers.

### 11.2 Related Standards and Prior Art

| Standard | Relationship to HALO |
|---|---|
| HAL (Hypertext Application Language) | Hypermedia links in response bodies for API navigation. No LLM-native fields. Complementary. |
| OpenAPI / Swagger | Comprehensive API description. Modern frameworks auto-generate it from code, reducing structural drift. However, OpenAPI is designed for code generators and human developers — not LLM agents. It lacks LLM-native reasoning fields, is served as a monolithic document with no standard subsetting mechanism, and requires non-trivial transformation for LLM consumption (`$ref` resolution, nesting traversal, parameter merging). See section 2.4 for a detailed comparison. |
| agents.json | Structured contract format at `/.well-known/agents.json`. Closest in intent to HALO — covers tool schemas, authentication flows, and API-level rate limits. However, it is a static file that must be maintained separately from the code, inheriting drift risk for structural fields. HALO’s per-endpoint OPTIONS approach derives structural schemas from the code at runtime. |
| MCP (Model Context Protocol) | Comprehensive agent protocol covering tools, resources, prompts, sampling, and sessions. HALO targets only the tool discovery and invocation layer — the dominant MCP use case. HALO and MCP are complementary: an MCP server can consume HALO schemas at runtime for drift-free tool definitions (see section 1.3). For consumer clients coupled to MCP (section 2.5), HALO serves as a backing store, not a replacement. |
| HAL MCP Server | An MCP server wrapping HTTP APIs for LLMs. Adds the MCP layer rather than removing it. |
| GraphQL Introspection | Runtime schema discovery — live and self-describing, but locked to GraphQL. HALO addresses this gap for REST. |
| HATEOAS | Next-action links in responses. Spiritually similar to HALO's `next` field but designed for human navigation. |
| llms.txt | Site-level AI-readable content convention. Site-level only, not per-endpoint. |

> **The gap:** Everything that exists describes APIs for humans or code generators, stored separately from the API. Nothing describes APIs for LLMs, living on the endpoint itself, aware of runtime context like auth scope. That is the space HALO occupies.

---

# PART II — The Python Reference Implementation

*`halo-fastapi` — a FastAPI plugin and agent adapter package implementing the HALO protocol*

---

## 12. halo-fastapi: Server-Side Implementation

### 12.1 Overview

`halo-fastapi` is a PyPI package that implements the HALO protocol for FastAPI servers. It is one implementation of the protocol — the same convention could be implemented as a Django Ninja plugin, a Flask extension, a Rails gem, or an Express middleware. `halo-fastapi` is the Python reference implementation.

```bash
uv add halo-fastapi
```

The package exposes two primary objects:

- **`HaloRegister`** — the server-side FastAPI plugin
- **`HaloClient`** — the client-side agent adapter

Together they are the complete HALO integration: `HaloRegister` makes an API HALO-compliant, `HaloClient` makes an agent capable of consuming any HALO-compliant API.

### 12.2 The HaloRegister Plugin

A single line added to any FastAPI application makes every route HALO-compliant. The plugin introspects the existing application at startup and derives everything it needs from metadata that already exists. No routes change. No models change. No decorators are required.

### 12.3 What HaloRegister(app) Actually Does

When `HaloRegister(app)` is called at startup, it performs the following steps automatically:

#### Step 1 — Route Introspection

The plugin walks FastAPI's internal route table — the same data structure FastAPI uses to generate its OpenAPI docs:

```python
# What the plugin reads from FastAPI's route table
for route in app.routes:
    method    = next(iter(route.methods or {'GET'})).upper()
    path      = route.path                    # /api/payments/charge
    # FastAPI registers separate routes for different methods on the
    # same path. Schemas are stored as a list per path to support this.
    endpoint  = route.endpoint               # the async def function
    docstring = endpoint.__doc__             # the docstring
    hints     = get_type_hints(endpoint)     # request/response types
    body_type = hints.get('body')            # ChargeRequest
    resp_type = route.response_model         # ChargeResponse
```

#### Step 2 — Pydantic Model Schema Extraction

For each request body type, the plugin calls Pydantic's built-in `model_json_schema()` method:

```python
# Pydantic generates the schema — the plugin just reads it
raw_schema    = ChargeRequest.model_json_schema()
llm_overrides = raw_schema.get('llm', {})    # from json_schema_extra

# raw_schema already contains:
# - field names and Python types mapped to JSON Schema types
# - required field list (fields without defaults)
# - descriptions from Field(description=...)
# - enum values from Literal['GBP', 'USD', 'EUR']
# - constraints from Field(gt=0, max_length=50, etc.)
# - nested model schemas (recursive)
```

#### Step 3 — Dependency Tree Auth Detection

The plugin walks the `Depends()` tree and maps FastAPI security types to HALO auth shapes:

```python
from fastapi.security import HTTPBearer, APIKeyHeader, OAuth2PasswordBearer

def detect_auth(endpoint) -> dict:
    for dep in get_dependencies(endpoint):
        if isinstance(dep, HTTPBearer):
            return {'type': 'bearer'}
        if isinstance(dep, APIKeyHeader):
            return {'type': 'apikey', 'header': dep.model.name}
        if isinstance(dep, OAuth2PasswordBearer):
            return {'type': 'oauth', 'tokenUrl': dep.model.tokenUrl}
    return {'type': 'none'}
```

#### Step 4 — Schema Assembly

The plugin assembles the final `application/llm+json` object, merging `llm` overrides from `json_schema_extra` on top of derived values:

```python
def build_halo_schema(route, body_type, resp_type, auth) -> dict:
    pydantic_schema = body_type.model_json_schema()
    llm_extra       = pydantic_schema.get('llm', {})

    schema = {
        'description': route.endpoint.__doc__ or '',
        'call':        {'method': method, 'url': route.path},
        'auth':        auth,
        'input':       extract_input_fields(pydantic_schema),
        'output':      resp_type.model_json_schema() if resp_type else {},
        'tags':        llm_extra.get('tags', []),
        'why':         llm_extra.get('why', route.endpoint.__doc__ or ''),
        'effects':     llm_extra.get('effects', {}),
        'next':        llm_extra.get('next', []),
        'examples':    llm_extra.get('examples', []),
    }
    return {k: v for k, v in schema.items() if v}  # strip empty fields
```

#### Step 5 — OPTIONS Handler Registration

Finally, the plugin registers OPTIONS handlers dynamically — one per route, and one for the root manifest:

```python
def register_options_handlers(app, schemas: dict[str, list]):
    # Root manifest handler
    @app.options('/')
    async def root_manifest(request: Request):
        if request.headers.get('accept') != 'application/llm+json':
            return Response(status_code=204)
        # Auth-aware: filter tools by what this token can see
        token   = extract_token(request)
        visible = filter_by_scope(schemas, token)
        tools = []
        for path, schema_list in visible.items():
            for s in schema_list:
                tools.append({
                    'url': path,
                    'method': s['call']['method'],
                    'name': path.strip('/').split('/')[-1],
                    'description': s.get('description', ''),
                    'tags': s.get('tags', []),
                })
        return JSONResponse({
            'api':     app.title,
            'version': app.version,
            'description': getattr(app, 'description', ''),
            'tools':   tools,
        })

    # Per-route handler — returns an array of schemas (one per method)
    for path, schema_list in schemas.items():
        def make_handler(response_list):
            @app.options(path)
            async def handler(request: Request):
                if request.headers.get('accept') != 'application/llm+json':
                    return Response(status_code=204)
                return JSONResponse(response_list)
        make_handler(schema_list)
```

> **The complete picture:** `HaloRegister(app)` is five steps: walk the route table, extract Pydantic schemas, detect auth from dependencies, assemble the HALO schema objects, and register OPTIONS handlers. The developer writes none of this — it happens automatically at app startup from metadata that already exists.

### 12.4 Complete Server Example

The example below is annotated to show exactly where each HALO field comes from.

```python
from halo_fastapi import HaloRegister
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

app = FastAPI(title='Payments API', version='1.0.0')
HaloRegister(app)  # ← registers OPTIONS handlers for every route at startup


class ChargeResponse(BaseModel):
    charge_id: str
    status:    Literal['success', 'pending', 'failed']


class ChargeRequest(BaseModel):
    # ─── INPUT SCHEMA ───────────────────────────────────────────────────────
    # Field type             → JSON Schema type in HALO input
    # Field(description=...) → description shown to the LLM per field
    # gt=0, max_length etc   → constraints in HALO input schema
    # Literal[...]           → enum values in HALO input schema
    # Fields without default are marked required: true automatically
    amount:      int   = Field(..., description='Amount in minor units (pence/cents)', gt=0)
    currency:    Literal['GBP', 'USD', 'EUR']    # → enum: [GBP, USD, EUR]
    customer_id: str   = Field(..., description='Customer identifier')

    model_config = ConfigDict(json_schema_extra={
        # ─── HALO LLM-NATIVE FIELDS ─────────────────────────────────────────
        # These are the ONLY fields that cannot be derived automatically.
        # All other HALO fields come from the route and model definitions above.
        'llm': {
            # TOOL DESCRIPTION (why) ────────────────────────────────────────
            # This is what the LLM reads when deciding which tool to call.
            # Write it as routing guidance, not as documentation.
            # If omitted, the function docstring is used as a fallback.
            'why': 'Use to charge a customer immediately after order confirmation. '
                   'Prefer /authorise if the charge amount may change before capture.',

            # TAGS ───────────────────────────────────────────────────────────
            # Tags control which agents can discover this tool.
            # An agent calling OPTIONS /?tags=payments sees this endpoint.
            # An agent calling OPTIONS /?tags=read does not.
            # Use the read/write convention plus a domain tag as a minimum.
            'tags': ['payments', 'write'],

            'effects': { 'reversible': True, 'undo': '/api/payments/refund' },
        }
    })


# ─── ROUTE ──────────────────────────────────────────────────────────────────
# @app.post      → call.method: POST in the HALO schema
# path           → call.url in the HALO schema
# response_model → output schema derived from ChargeResponse
@app.post('/api/payments/charge', response_model=ChargeResponse)
# ─── AUTH ───────────────────────────────────────────────────────────────────
# HTTPBearer in Depends()       → auth.type: bearer in the HALO schema
# APIKeyHeader would            → auth.type: apikey
# OAuth2PasswordBearer would    → auth.type: oauth
async def charge(body: ChargeRequest, token: HTTPBearer = Depends()):
    # ─── FALLBACK DESCRIPTION ───────────────────────────────────────────────
    # If 'why' is not set in json_schema_extra, this docstring is used
    # as the tool description instead. Always write a useful docstring.
    '''Charge a payment method for a given amount.'''
    ...
```

> **Description vs why:** The docstring is the fallback description — what the endpoint does, written for developers. The `why` field is the LLM routing hint — when to call this tool vs alternatives, written for the model. If both are present, `why` takes precedence in the HALO schema.

> **Tags rule:** Tags are the single most impactful field for agent performance. They determine which agents discover the tool at all. At minimum, every endpoint should have a domain tag (`payments`, `email`, `calendar`) and a `read`/`write` tag. Without tags, the tool appears in all discovery requests regardless of relevance.

> **Implementation note — GET endpoints with query parameters:** HALO derives input schemas and LLM metadata (`why`, `tags`, `effects`) from Pydantic request body models. For GET endpoints that use query parameters instead of a request body, implementations should also inspect dependency-injected Pydantic models (e.g. FastAPI's `Depends()` pattern). In `halo-fastapi`, a GET endpoint can carry full LLM metadata by using a Pydantic model as a query dependency:
>
> ```python
> @app.get('/api/books', response_model=BookSearchResponse)
> async def search_books(params: BookSearchRequest = Depends()):
>     ...
> ```
>
> The `BookSearchRequest` model carries `json_schema_extra` with `why`, `tags`, and `examples` — the same pattern used for POST body models. HALO introspects the dependency and extracts the schema automatically. Without this pattern, GET endpoints will have no input schema, no tags, and the `why` field will fall back to the docstring.

### 12.5 What halo-fastapi Derives Automatically

| Field | Source |
|---|---|
| URL and HTTP method | Route decorator |
| Description / why | Docstring (fallback) |
| Input schema | Pydantic model fields and types |
| Field descriptions | `Field(description=...)` metadata |
| Enums and constraints | `Literal` types and Pydantic validators |
| Output schema | `response_model` annotation |
| Auth type | `Depends()` tree — `HTTPBearer`, `APIKey`, etc. |
| Required scopes | OAuth2 scope declarations |
| Tags | `json_schema_extra['llm']['tags']` |
| `why` (routing hint) | `json_schema_extra['llm']['why']` or docstring |

> **Zero required additions:** Every field HALO needs can be derived from existing route definitions, Pydantic models, docstrings, and dependency injection. The only optional enrichments are the LLM-native fields — `why`, `tags`, `effects`, and `next` — which are additive improvements, not baseline requirements.

### 12.6 Implementing HALO in Other Languages

The following are minimal reference implementations showing that the protocol requires no special library — any HTTP server can implement it by adding a single OPTIONS handler per route. `halo-fastapi` automates this for FastAPI; these examples show the manual equivalent.

#### Node.js / Express

```javascript
app.options('/api/payments/charge', (req, res) => {
  if (req.headers['accept'] !== 'application/llm+json')
    return res.set('Allow', 'POST').status(204).send();
  res.json({
    description: 'Charge a payment method',
    call:    { method: 'POST', url: '/api/payments/charge' },
    auth:    { type: 'bearer', scopes: ['payments:write'] },
    input:   { amount: { type: 'number', required: true }, currency: { type: 'string', required: true } },
    tags:    ['payments', 'write'],
    effects: { reversible: true, undo: '/api/payments/refund' }
  });
});
```

#### ASP.NET Core

```csharp
[HttpOptions("/api/payments/charge")]
public IActionResult ChargeSchema() {
    if (Request.Headers["Accept"] != "application/llm+json") return NoContent();
    return Ok(new {
        description = "Charge a payment method",
        call        = new { method = "POST", url = "/api/payments/charge" },
        tags        = new[] { "payments", "write" },
        effects     = new { reversible = true }
    });
}
```

### 12.7 OpenAPI Bridge

For teams with existing OpenAPI specs, a bridge auto-generates `application/llm+json` responses by transforming the existing schema — zero manual work for the structural fields. The LLM-native fields (`why`, `tags`, `effects`) must still be added manually as they have no OpenAPI equivalent.

---

## 13. halo-fastapi: Client-Side Agent Adapter

The same `halo-fastapi` package provides `HaloClient` — the client-side adapter that discovers any HALO-compliant API, caches schemas, injects credentials, and invokes tools directly.

### 13.1 HaloClient Core

```python
from halo_fastapi import HaloClient

client = HaloClient(
    base_url='https://api.example.com',
    bearer_token=os.getenv('API_KEY'),
)

# Discover all tools, or filter by tag
await client.discover()                    # all tools
await client.discover(tags=['payments'])   # filtered

# Schemas are cached — OPTIONS only fired once per route per session
schema = await client.get_tool('/api/payments/charge')

# Invoke a tool directly — credentials injected automatically
result = await client.invoke('/api/payments/charge', body={'amount': 1000})
```

### 13.2 What HaloClient Does Internally

When `discover()` is called, `HaloClient` performs the following sequence:

1. Fires `OPTIONS /` with `Accept: application/llm+json` — receives the root manifest with tool URLs, names, descriptions, and tags
2. If tags were requested, the query `?tags=tag1,tag2` is appended and server-side filtering applies
3. Stores the tool list from the manifest as `client.tools`
4. On `get_tool(path)`, fires `OPTIONS /route` to fetch the full schema array and caches it. Accepts an optional `method` parameter to select a specific schema when multiple methods exist on the same path.
5. On `invoke(path, body)`, fetches the schema (cached), injects credentials from the credential map based on the target domain, and fires the real HTTP call using the method and URL from the schema. For GET requests, `body` is sent as query parameters; for other methods, it is sent as a JSON body.
6. Failed requests are retried with exponential backoff on connection errors, HTTP 429, and 5xx responses

### 13.3 Credential Injection

For the common case of a single API with a bearer token, use the `bearer_token` convenience parameter:

```python
client = HaloClient(base_url='https://api.example.com', bearer_token=os.getenv('API_KEY'))
```

For advanced scenarios (multiple hosts, API keys, basic auth), pass a credential map keyed by domain (with optional port):

```python
credentials = {
    'api.example.com':      {'type': 'bearer', 'value': os.getenv('API_KEY')},
    'api.internal.com:8443': {'type': 'apikey', 'header': 'X-API-Key', 'value': os.getenv('INTERNAL_KEY')},
}
client = HaloClient(base_url='https://api.example.com', credentials=credentials)
```

Supported credential types:

| Type | Behaviour |
|---|---|
| `bearer` | Injects `Authorization: Bearer {value}` |
| `apikey` | Injects the value into the named header (default `X-API-Key`) |
| `basic` | Injects `Authorization: Basic {value}` |

### 13.4 Framework Integration

`halo-fastapi` includes adapters for Microsoft Agent Framework and Semantic Kernel.

**Agent Framework** — install with `halo-fastapi[agent-framework]`:

```python
from halo_fastapi import HaloClient, HaloAgentFrameworkAdapter

client = await HaloClient(base_url, bearer_token=token).discover()
adapter = HaloAgentFrameworkAdapter(client)
tools = await adapter.create_tools()  # list[FunctionTool]
```

**Semantic Kernel** — install `semantic-kernel` separately (transitive dependency conflict with `agent-framework-core` prevents a shared extra):

```python
from halo_fastapi import HaloClient, HaloSemanticKernelAdapter

client = await HaloClient(base_url, bearer_token=token).discover()
adapter = HaloSemanticKernelAdapter(client)
plugin = await adapter.create_plugin()  # KernelPlugin
kernel.add_plugin(plugin)
```

Both adapters follow the same pattern: discover via `HaloClient`, pass the client to the adapter, and call the adapter's creation method. For other frameworks — LangChain, LlamaIndex — the same pattern applies: wrap `client.invoke()` in the framework's tool primitive.

> **Package boundary:** `halo-fastapi` is one implementation of the HALO protocol. A developer building a Node.js agent would use a separate `halo-node` package that performs identical OPTIONS calls and maps the same schema fields to its framework primitives. The protocol is the contract. The packages are convenient implementations of that contract.

---

## 14. Summary

**The Convention**

Send `HTTP OPTIONS` with `Accept: application/llm+json` to any API endpoint. Receive a compact JSON schema describing what it does, how to call it, what auth it needs, what effects it has, and what tags categorise it. The API describes itself — no separate tool definitions to maintain.

**The Loop**

```
1. OPTIONS /?tags=payments  →  discover relevant tools only
2. OPTIONS /tool            →  fetch schema lazily when selected
3. POST /tool               →  call with correct input and auth — direct, no proxy
4. Check next               →  chain to next action if suggested
```

**Skills vs Protocol**

Skills and schemas operate at different layers. Skills describe business rules, domain knowledge, and multi-tool orchestration — they win on expressiveness, flexibility, and accessibility to domain experts. The OPTIONS protocol describes mechanical API capability with structural accuracy that cannot drift. The migration is not skills *to* protocol but skills *on top of* protocol.

**What it removes**

Sidecar MCP servers (for thin wrappers) · Hand-written tool definitions · Structural schema drift · Auth sync · Upfront token cost · Silent failures

**What it adds**

One OPTIONS handler · Self-describing APIs · Tag-filtered discovery · Auth-aware scoping · Side effect contracts · Lazy schema loading · Testable schemas · Direct call path · Zero new infrastructure

---

*HALO Protocol Specification — CC BY 4.0*
*halo-fastapi Reference Implementation — Apache 2.0*
*https://github.com/irarainey/halo*

*For version history, see [CHANGELOG.md](CHANGELOG.md).*
*https://github.com/irarainey/halo*