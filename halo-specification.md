# HALO — HTTP API Language for Operations

**`application/llm+json`**

*Self-Describing APIs for LLM Agents — Without MCP*

**Version: 0.2.0-draft**

## Specification, Implementation & Framework Integration Guide

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

Some frameworks auto-generate structural schemas from code (FastAPI's OpenAPI generation, for example, eliminates structural drift for the fields it covers). But even auto-generated OpenAPI is not designed for agent consumption — it lacks fields like `why`, `tags`, `effects`, and `next`, and is not served per-endpoint at runtime. The remaining approaches — MCP servers, tool registries, skill documents, and agent config files — are secondary artifacts that describe an API but have no binding relationship to it.

### 1.1 How It Works Today

Current agent frameworks — LangChain, Semantic Kernel, Microsoft Agent Framework, and MCP — generally follow a similar pattern:

- A developer writes or decorates a tool definition describing what the API does
- That definition is registered in a tool registry, MCP server, or agent config (some frameworks derive structural schemas from type hints, reducing boilerplate)
- The LLM reads all definitions at inference time and decides which to call
- The framework translates that decision into an actual API call

Even when structural schemas are auto-derived from code, the tool definitions still live in the agent's codebase — separate from the API they describe. Each layer can drift independently. Each adds maintenance overhead.

### 1.2 The Drift Problem

Schema drift is the default outcome of the current approach. The API changes, the tool description does not, and the LLM confidently calls the endpoint with stale parameters. No error surfaces at the description layer — just downstream failures that require log forensics to diagnose. In production systems with dozens of APIs maintained by different teams, this is not an edge case. It is what happens.

When API descriptions are maintained separately from the code — whether as OpenAPI specs, MCP server definitions, or tool descriptions — they tend to diverge over time.

| Problem | Consequence |
|---|---|
| Schema drift | Tool descriptions in registries diverge from the real API as it evolves |
| Version mismatch | The tool description describes v1 behaviour but the API is on v2 |
| Maintenance burden | Every new API requires a new tool wrapper, schema, and registration |
| Token cost | All tool descriptions loaded upfront burning context regardless of use |
| Auth complexity | Auth handled separately from discovery, creating synchronisation problems |
| Silent failures | Stale descriptions cause incorrect calls with no schema-level error |

> **Core insight:** The API already knows everything about itself — inputs, outputs, auth, rate limits, side effects. The problem is that nothing asks it. Every secondary artifact that describes an API is a liability. The API itself is the only source of truth for its structural contract.

### 1.3 The Architecture Problem

Beyond drift, MCP creates a structural architecture problem that has no clean resolution.

To maintain clean architecture and proper separation of concerns, an MCP server should be a standalone service — its own codebase, its own repository, its own deployment pipeline, its own infrastructure. This is the architecturally correct approach. It is also significant additional development and operational overhead: another service to build, another service to deploy, another service to monitor, another service to scale, another service to wake up to at 3am when it goes down.

The alternative — embedding MCP directly inside the existing API — avoids the operational overhead but introduces a different problem. MCP is a transport and tool-description protocol. An API is a domain service. Bundling protocol concerns into a domain service conflates two distinct responsibilities: serving domain logic and acting as an agent transport layer. These have different reasons to change and different lifecycles. If MCP evolves, is versioned, or is replaced by a successor protocol, your domain service has to change with it. In a microservices architecture this also contaminates service boundaries that were deliberately drawn.

> **Note on in-process MCP:** MCP supports an in-process stdio transport that avoids the network hop and sidecar deployment. In this mode the latency and failure-point arguments in section 1.4 do not apply. However, the architecture concern remains — the MCP protocol layer is still embedded in (or tightly coupled to) the API process, and the tool descriptions are still maintained as separate artifacts from the code that handles requests.

> **The MCP dilemma:** With MCP you face an unavoidable choice — either maintain a separate service and accept the operational overhead, or embed MCP in your API and accept the separation of concerns violation. There is no clean option. HALO dissolves this dilemma entirely. An OPTIONS handler is not a foreign concern bolted onto the API — it is the API describing itself using a standard HTTP mechanism it already supports. No new protocol layer is introduced. No new service is required. Domain logic and self-description are not two separate concerns: every well-designed API should be able to answer the question "how do I call you?"

### 1.4 The Proxy Problem

When deployed as a remote service, MCP does not just describe APIs — it proxies calls to them. Every tool invocation by an LLM travels through the MCP server before reaching the actual API. This introduces a network hop that would not otherwise exist.

> **Fair acknowledgement:** MCP's stdio transport runs in-process and avoids the network hop entirely. The latency and failure-point concerns below apply specifically to remote MCP deployments — which are the recommended architecture for production multi-agent systems.

In isolation, one extra network call seems trivial. In practice it compounds into several distinct problems:

- **Latency** — every tool call carries the overhead of an additional network round-trip through the MCP layer before the real API is reached
- **New failure point** — the MCP server can be down, overloaded, or misconfigured independently of the API it represents. A healthy API can be unreachable because its MCP proxy has failed
- **Harder failure attribution** — when a tool call fails, the error could originate from the LLM, the MCP server, the network between them, or the underlying API. Distributed call chains make root cause analysis significantly harder
- **Timeout stacking** — timeouts compound across hops. A call that would have succeeded directly may fail because the combined MCP-to-API round-trip exceeds a client timeout

HALO has no proxy layer. The LLM agent calls the API directly — OPTIONS to discover, then the real verb to invoke. The call path is two hops: agent to API. Failures are immediately attributable. Latency is the minimum possible. There is no intermediate service to operate, monitor, or blame.

---

## 2. The Solution

> **Protocol note:** Everything in Part I describes the HALO protocol itself — a convention that can be implemented in any language on any platform. Python, Node.js, Go, Java, .NET, Ruby — any HTTP server can implement HALO by following this specification. The protocol has no dependency on any specific runtime, framework, or library.

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

Servers that do not implement HALO return a 406 or their standard OPTIONS response. No conflict. No breakage.

### 2.3 The Schema Response

```json
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
```

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
  "tools": [
    { "url": "/api/payments/charge",   "name": "charge",  "description": "Charge a payment method",          "tags": ["payments", "write"] },
    { "url": "/api/payments/refund",   "name": "refund",  "description": "Refund a previous charge",          "tags": ["payments", "write"] },
    { "url": "/api/customers/lookup",  "name": "lookup",  "description": "Look up customer details",           "tags": ["customers", "read"] },
    { "url": "/api/email/send",        "name": "send",    "description": "Send an email to a recipient",       "tags": ["comms", "write"] },
    { "url": "/api/admin/users",       "name": "users",   "description": "Manage admin user accounts",         "tags": ["admin", "write"] }
  ]
}
```

The agent now has a complete capability map from a single cheap call. Tags are free-form strings. The API owner defines the taxonomy. Nothing needs to be registered centrally.

### 3.2 Tag Filtering

The client passes tags as a query parameter to receive only the relevant subset of tools:

```http
# Discover only payment tools
OPTIONS /?tags=payments

# Discover only safe read operations
OPTIONS /?tags=read

# Discover tools matching multiple tags
OPTIONS /?tags=payments,read
```

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
  { "url": "/api/customers/lookup", "name": "lookup", "description": "Look up customer details", "tags": ["customers","read"] }
] }

// Full-access token:
{ "tools": [
  { "url": "/api/payments/charge",  "name": "charge", "description": "Charge a payment method",   "tags": ["payments","write"] },
  { "url": "/api/customers/lookup", "name": "lookup", "description": "Look up customer details",  "tags": ["customers","read"] },
  { "url": "/api/admin/users",      "name": "users",  "description": "Manage admin user accounts", "tags": ["admin","write"] }
] }
```

The LLM never learns that restricted tools exist.

### 3.5 Two-Phase Lazy Loading

```
Agent starts
   │
   ├── OPTIONS /?tags=payments     ← cheap — names, descriptions, and tags
   │   ← { tools: [charge, refund] }
   │
   │   LLM receives: "Charge customer £25"
   │   LLM selects:  charge
   │
   ├── OPTIONS /payments/charge    ← lazy — only when selected
   │   ← { full schema }
   │
   └── POST /payments/charge       ← actual call — direct, no proxy
       ← { charge_id, status }
```

Three HTTP calls total. Two OPTIONS, one POST. No registry, no MCP server. The agent still needs the base URL configured, but no per-tool definitions or framework-specific wiring is required.

### 3.6 Intent-Based Filtering

```python
async def discover_for_task(task: str, base_url: str) -> list:
    # Step 1: fetch manifest only — just names and tags, very cheap
    manifest = await options(base_url)
    all_tags = extract_unique_tags(manifest)

    # Step 2: ask the LLM which tags are relevant
    relevant = await llm.invoke(f"""
        Task: "{task}"
        Available categories: {all_tags}
        Return only relevant category names as JSON array.
        """)

    # Step 3: fetch only the tools that match
    filtered = await options(base_url, tags=relevant)

    # Step 4: lazy-load schemas only for filtered tools
    return [await options(t['url']) for t in filtered['tools']]
```

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

For APIs where the tool list itself is sensitive, credentials can be required to retrieve the schema. When the same token is valid for both discovery and the actual call, the schema signals this with `"already": true`.

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

### 5.1 Semantic Kernel

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

### 5.2 LangChain

```python
adapter = HaloLangChainAdapter('https://api.example.com', credentials)
tools = await adapter.create_tools(tags=['payments'])

agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
result = await executor.ainvoke({'input': 'Charge customer £25'})
```

### 5.3 Microsoft Agent Framework

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
| Semantic Kernel | `KernelFunction` | Central kernel, plugins | `why` → description, `next` → planner hints |
| LangChain | `BaseTool / StructuredTool` | Toolkit pattern | Pydantic `ArgsSchema` from input fields |
| Microsoft Agent | `FunctionTool` | Agent Framework tools | `create_tools()` builds tools from schema |
| LlamaIndex | `FunctionTool` | `ToolMetadata` object | Pydantic schema from input fields |

---

## 6. Full Schema Specification

### 6.1 Core Fields

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

These fields have no equivalent in OpenAPI or existing standards. They exist solely to improve LLM reasoning and routing.

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

Skills — blocks of text injected into context describing how the LLM should behave — are the most common lightweight alternative to formal tool registration. Understanding where each approach belongs is critical to building a well-structured agent system.

### 7.1 Honest Comparison

| Dimension | Skills | OPTIONS Protocol | Winner |
|---|---|---|---|
| Implementation effort | Write text — minutes | Add OPTIONS handler — hours | Skills win initially |
| Maintenance over time | Manual — drifts silently | Structural schema cannot drift; LLM fields (`why`, `tags`) still manual | Protocol wins at scale |
| Accuracy | As good as the author | Structural fields always correct — derived from code. LLM hints (`why`, `effects`) are hand-written but co-located with the model | Protocol wins |
| Auth description | Prose — easy to get wrong | Detected and typed automatically | Protocol wins |
| Schema changes | Someone must update manually | Structural changes reflect instantly — same deploy. LLM metadata changes require a code edit to the model's metadata annotations | Protocol wins |
| Token cost | All loaded upfront always | Lazy, filtered, on demand | Protocol wins |
| Validation | None — it is text | Testable in CI against live endpoint | Protocol wins |
| Failure mode | Silent incorrect calls | Explicit 400/422 with structured error | Protocol wins |
| Behavioural guidance | Natural — text is expressive | Not possible — schemas are structural | Skills win |

### 7.2 The Drift Problem Is Worse Than It Looks

Skills fail silently and at the worst possible time. The API changes, the skill doesn't, and the LLM confidently calls the endpoint with stale parameter names. The failure surfaces as incorrect agent behaviour — not as a schema error — and requires log forensics to diagnose.

When implemented natively, the OPTIONS protocol cannot drift *structurally* because the schema is derived from the same code that handles requests. In a framework like FastAPI, the Pydantic model that validates the incoming request is the same model that generates the OPTIONS response. In other languages, the same principle applies whenever the schema is generated from the route and type definitions rather than maintained as a separate artifact. If the code changes, the structural schema changes atomically with it in the same deployment.

> **Honest caveat:** HALO's LLM-native fields — `why`, `tags`, `effects`, `next`, and `examples` — are hand-written metadata. These can drift from reality in the same way any documentation can. The difference is that they are co-located with the code that defines the endpoint, making staleness visible during code review. Structural fields (inputs, outputs, types, constraints, auth) are auto-derived in implementations that support it and cannot drift.

### 7.3 Where Each Belongs

| Approach | What It Handles |
|---|---|
| Skills | Behavioural guidance and judgment — how to handle edge cases, what tone to use, when to escalate. Things that cannot be expressed as a JSON schema. |
| OPTIONS Protocol | Mechanical capability — what the agent can do, exactly how to do it, what auth it needs, what side effects it has. Things that must be precise and must stay in sync with the live system. |

> **Key principle:** Behavioural guidance belongs in skills. API contracts belong in schemas. When both are in skills the system is fragile. When both are in schemas the system is rigid. The combination is where it gets genuinely robust.

### 7.4 Migration Path

Most teams will start with skills because the upfront cost is lower. The natural migration path is to start with skills for early prototyping and migrate to OPTIONS as APIs stabilise and the maintenance cost of skills becomes visible in production. The migration is straightforward — the skill is essentially prose describing what the OPTIONS schema will contain formally.

---

## 8. Why This Is a Solid Foundation

### 8.1 Direct Call Path — No Proxy, No Extra Hop

When MCP is deployed as a remote service, it acts as a proxy — every tool invocation travels through the MCP server before reaching the API. (MCP's in-process stdio transport avoids this hop but retains the protocol coupling described in section 1.3.) HALO eliminates the proxy layer entirely — the agent calls the API directly, always.

| | MCP (remote) | HALO |
|---|---|---|
| Call path | Agent → MCP server → API | Agent → API |
| Latency | MCP round-trip added to every call | Minimum possible — direct |
| Failure points | LLM, MCP server, MCP-to-API network, API | LLM and API only |
| Timeout behaviour | Timeouts compound across hops | Single timeout, single hop |
| Failure attribution | Which layer failed — MCP or API? | Unambiguous — only one service |
| Observability | Requires tracing across two services | Single service logs tell the whole story |

In distributed systems, every additional hop is not just latency overhead — it is a new surface for failure, a new place to add instrumentation, and a new layer to reason about when something goes wrong.

### 8.2 No Additional Service to Deploy or Maintain

When deployed as a remote service (the recommended production architecture), MCP requires a sidecar server process — a separate deployment, a separate codebase, a separate thing that can go down, drift out of sync, or be forgotten when the underlying API changes. MCP's in-process stdio transport avoids this but retains the protocol coupling described in section 1.3.

HALO has none of this. The OPTIONS handler runs inside the existing API process. It shares the same deployment pipeline, the same infrastructure, the same uptime guarantees, the same authentication middleware, and the same codebase. There is nothing new to operate. If the API is running, HALO is running. If the API is down, there is nothing for the agent to call anyway.

> **Key strength:** Schema accuracy and zero operational overhead are the same property. Because the HALO handler lives inside the API, it cannot be separately broken, separately outdated, or separately unavailable. Tight coupling is not a tradeoff — it is the point.

### 8.3 Conditional Guarantees

HALO's core guarantees — no structural drift, no additional service, direct call path — are conditional on the API implementing the protocol natively. When an API serves its own HALO schema from inside its own process, these properties hold by construction.

For third-party APIs you do not control, it is technically possible to write a proxy that serves HALO schemas on behalf of the upstream API. This reintroduces drift risk (the schema is no longer derived from the same code) and operational overhead (an additional service to maintain). This is no different from the problems HALO solves for native implementations — it is simply the unavoidable cost of describing an API you do not own. Treat the proxy pattern as a last resort for legacy or third-party integrations where native adoption is not possible.

### 8.4 The Schema Is Testable

Because the schema lives on an HTTP endpoint it can be validated in CI:

```bash
curl -X OPTIONS https://api.example.com/payments/charge \
     -H 'Accept: application/llm+json' | jq .
```

Catch drift before it reaches production. Static schema files (like OpenAPI specs) can also be validated in CI, but they test the *file* — not the live endpoint. HALO's testability advantage is that the schema under test is the same one agents will receive at runtime.

### 8.5 Version Controls Itself

When the API changes, the OPTIONS response changes with it — same deployment, same commit, same version. Structural fields (inputs, outputs, types, auth) are derived from the code that handles requests, so a tool definition describing v1 behaviour while the API is on v2 cannot happen for those fields. LLM-native fields (`why`, `tags`, `effects`, `next`) are hand-written metadata and can still drift, but they live alongside the model definition, making staleness visible during code review.

### 8.6 Monitorable Out of the Box

OPTIONS requests appear in your existing access logs. You can see exactly which agents are discovering which tools, how often, from where. You can rate-limit discovery separately from invocation. Your existing observability stack handles it automatically.

### 8.7 Closes the Trust Boundary

Because OPTIONS responses come from the same authenticated server as the API calls themselves, the trust boundary is consistent — if you trust the API enough to call it, you trust the schema enough to read it. The description and the endpoint share the same security perimeter.

### 8.8 OPTIONS Is a Familiar HTTP Primitive

OPTIONS is a well-established HTTP method with clear semantics: capability negotiation and introspection. Developers, HTTP clients, and documentation tooling already understand it. Using OPTIONS for HALO means the protocol builds on an existing, widely understood mechanism rather than introducing a novel one — lowering the barrier to adoption for both humans implementing it and tools consuming it.

### 8.9 Multi-Tenant Tool Scoping Is Natural

In systems where different users have different permissions, the OPTIONS response varies per request based on the auth token — different permitted fields, different rate limits, different available actions. Other approaches can achieve this (an API that filters its OpenAPI spec by auth token, for example), but it requires bespoke implementation. With HALO, auth-scoped discovery is the default pattern — it falls out naturally from the fact that the server already knows what the caller is allowed to do.

### 8.10 The API Owner Regains Control

An API that serves `application/llm+json` from OPTIONS is making a declaration: *I am ready to be used by machines, on my own terms, without an intermediary.* This gives control back to the people who actually know the API — the people who built it.

---

## 9. What This Replaces

| Current World | With HALO |
|---|---|
| MCP server process | OPTIONS handler runs inside the existing API — no sidecar, no separate deployment |
| Separation of concerns violation | OPTIONS is a native HTTP mechanism — self-description is not a separate concern |
| MCP proxy layer | Agent calls the API directly — no intermediate network hop |
| Distributed call chain | Two-hop call path: agent to API. Failures immediately attributable. |
| Tool registry | The API is the registry. Root OPTIONS returns the full manifest. |
| Schema files (OpenAPI) | Schema lives on the route itself, versioned with the code |
| Structural schema drift | Eliminated for auto-derived fields — schema is generated from the code that handles requests. LLM-native fields (`why`, `tags`, `effects`) are co-located but still hand-written. |
| Auth in tool config | Auth shape served with schema, secrets in agent credential map |
| Hardcoded retry logic | `resilience` fields declare the API's own retry contract |
| Workflow definitions | `next` field creates emergent workflows from API metadata |
| Static tool definitions | Dynamic discovery — tools appear when APIs implement the convention |
| Skill drift | Structural schema cannot drift — same artifact as the code that validates requests. LLM-native hints are co-located with the model. |

---

## 10. Prior Art and Naming

### 10.1 The Name: HAL vs HALO

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

### 10.2 Related Standards and Prior Art

| Standard | Relationship to HALO |
|---|---|
| HAL (Hypertext Application Language) | Hypermedia links in response bodies for API navigation. No LLM-native fields. Complementary. |
| OpenAPI / Swagger | Comprehensive API description. Modern frameworks auto-generate it from code, reducing structural drift. However, OpenAPI is designed for code generators and human developers — not LLM agents. It lacks LLM-native fields (`why`, `tags`, `effects`, `next`) and is not served per-endpoint at runtime. |
| agents.json | Structured contract format at `/.well-known/agents.json`. Closest in intent to HALO — covers tool schemas, authentication flows, and API-level rate limits. However, it is a static file that must be maintained separately from the code, inheriting drift risk for structural fields. HALO’s per-endpoint OPTIONS approach derives structural schemas from the code at runtime. |
| HAL MCP Server | An MCP server wrapping HTTP APIs for LLMs. Adds the MCP layer rather than removing it. |
| GraphQL Introspection | Runtime schema discovery — genuinely live and self-describing, but locked to GraphQL. HALO fills this gap for REST. |
| HATEOAS | Next-action links in responses. Spiritually similar to HALO's `next` field but designed for human navigation. |
| llms.txt | Site-level AI-readable content convention. Site-level only, not per-endpoint. |

> **The gap:** Everything that exists describes APIs for humans or code generators, stored separately from the API. Nothing describes APIs for LLMs, living on the endpoint itself, aware of runtime context like auth scope. That is the space HALO occupies.

---

# PART II — The Python Reference Implementation

*`halo-fastapi` — a FastAPI plugin and agent adapter package implementing the HALO protocol*

---

## 11. halo-fastapi: Server-Side Implementation

### 11.1 Overview

`halo-fastapi` is a PyPI package that implements the HALO protocol for FastAPI servers. It is one implementation of the protocol — the same convention could be implemented as a Django Ninja plugin, a Flask extension, a Rails gem, or an Express middleware. `halo-fastapi` is the Python reference implementation.

```bash
uv add halo-fastapi
```

The package exposes two primary objects:

- **`HaloRegister`** — the server-side FastAPI plugin
- **`HaloClient`** — the client-side agent adapter

Together they are the complete HALO integration: `HaloRegister` makes an API HALO-compliant, `HaloClient` makes an agent capable of consuming any HALO-compliant API.

### 11.2 The HaloRegister Plugin

A single line added to any FastAPI application makes every route HALO-compliant. The plugin introspects the existing application at startup and derives everything it needs from metadata that already exists. No routes change. No models change. No decorators are required.

### 11.3 What HaloRegister(app) Actually Does

When `HaloRegister(app)` is called at startup, it performs the following steps automatically:

#### Step 1 — Route Introspection

The plugin walks FastAPI's internal route table — the same data structure FastAPI uses to generate its OpenAPI docs:

```python
# What the plugin reads from FastAPI's route table
for route in app.routes:
    method    = list(route.methods)[0]       # POST, GET, etc.
    path      = route.path                    # /api/payments/charge
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
        'description': llm_extra.get('why') or route.endpoint.__doc__ or '',
        'call':        {'method': method, 'url': route.path},
        'auth':        auth,
        'input':       extract_input_fields(pydantic_schema),
        'output':      resp_type.model_json_schema() if resp_type else {},
        'tags':        llm_extra.get('tags', []),
        'why':         llm_extra.get('why', ''),
        'effects':     llm_extra.get('effects', {}),
        'next':        llm_extra.get('next', []),
        'examples':    llm_extra.get('examples', []),
    }
    return {k: v for k, v in schema.items() if v}  # strip empty fields
```

#### Step 5 — OPTIONS Handler Registration

Finally, the plugin registers OPTIONS handlers dynamically — one per route, and one for the root manifest:

```python
def register_options_handlers(app, schemas: dict):
    # Root manifest handler
    @app.options('/')
    async def root_manifest(request: Request):
        if request.headers.get('accept') != 'application/llm+json':
            return Response(status_code=204)
        # Auth-aware: filter tools by what this token can see
        token   = extract_token(request)
        visible = filter_by_scope(schemas, token)
        return JSONResponse({
            'api':     app.title,
            'version': app.version,
            'tools':   [{
            'url': url,
            'name': url.strip('/').split('/')[-1],
            'description': s.get('description', ''),
            'tags': s.get('tags', []),
        } for url, s in visible.items()]
        })

    # Per-route handler for each registered endpoint
    for path, schema in schemas.items():
        def make_handler(s):
            @app.options(path)
            async def handler(request: Request):
                if request.headers.get('accept') != 'application/llm+json':
                    return Response(status_code=204)
                return JSONResponse(s)
        make_handler(schema)
```

> **The complete picture:** `HaloRegister(app)` is five steps: walk the route table, extract Pydantic schemas, detect auth from dependencies, assemble the HALO schema objects, and register OPTIONS handlers. The developer writes none of this — it happens automatically at app startup from metadata that already exists.

### 11.4 Complete Server Example

The example below is annotated to show exactly where each HALO field comes from. Tags and the tool description are the two fields most commonly misunderstood.

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

### 11.5 What halo-fastapi Derives Automatically

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

### 11.6 Implementing HALO in Other Languages

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

### 11.7 OpenAPI Bridge

For teams with existing OpenAPI specs, a bridge auto-generates `application/llm+json` responses by transforming the existing schema — zero manual work for the structural fields. The LLM-native fields (`why`, `tags`, `effects`) must still be added manually as they have no OpenAPI equivalent.

---

## 12. halo-fastapi: Client-Side Agent Adapter

The same `halo-fastapi` package provides `HaloClient` — the client-side adapter that discovers any HALO-compliant API, caches schemas, injects credentials, and invokes tools directly.

### 12.1 HaloClient Core

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

### 12.2 What HaloClient Does Internally

When `discover()` is called, `HaloClient` performs the following sequence:

1. Fires `OPTIONS /` with `Accept: application/llm+json` — receives the root manifest with tool URLs, names, descriptions, and tags
2. If tags were requested, the query `?tags=tag1,tag2` is appended and server-side filtering applies
3. Stores the tool list from the manifest as `client.tools`
4. On `get_tool(path)`, fires `OPTIONS /route` to fetch the full schema and caches it
5. On `invoke(path, body)`, fetches the schema (cached), injects credentials from the credential map based on the target domain, and fires the real HTTP call using the method and URL from the schema
6. Failed requests are retried with exponential backoff on connection errors, HTTP 429, and 5xx responses

### 12.3 Credential Injection

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

### 12.4 Framework Integration

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

## 13. Summary

**The Convention**

Send `HTTP OPTIONS` with `Accept: application/llm+json` to any API endpoint. Receive a compact JSON schema describing what it does, how to call it, what auth it needs, what effects it has, and what tags categorise it. The API describes itself. No MCP. No registry. No shim.

**The Loop**

```
1. OPTIONS /?tags=payments  →  discover relevant tools only
2. OPTIONS /tool            →  fetch schema lazily when selected
3. POST /tool               →  call with correct input and auth — direct, no proxy
4. Check next               →  chain to next action if suggested
```

**Skills vs Protocol**

Skills describe behaviour and judgment — use them for that. The OPTIONS protocol describes mechanical API capability — use it for that. Skills drift silently. Structural schemas derived from code cannot drift. LLM-native fields are co-located with the model but remain hand-written. Use both, for the right purpose.

**What it removes**

MCP server · Tool registry · Structural schema drift · Skill drift · Auth sync · Sidecar processes · Static tool definitions · Upfront token cost · Silent failures · Extra network hop · Distributed call chain complexity

**What it adds**

One OPTIONS handler · Self-describing APIs · Tag-filtered discovery · Auth-aware scoping · Side effect contracts · Lazy schema loading · Testable schemas · Direct call path · Zero new infrastructure

---

*HALO Protocol Specification — CC BY 4.0*
*halo-fastapi Reference Implementation — Apache 2.0*
*https://github.com/irarainey/halo*