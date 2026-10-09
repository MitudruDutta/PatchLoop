# PatchLoop Agent Integration PRD: support any tool-using agent

**Owner:** proposed Mitudru Dutta (engine and RL), to be confirmed. **Status:** draft for review, 5 October 2026.
**Related:** [engine PRD](engine.md), [platform PRD](platform.md) (depends on this document), [RL environment PRD](rl-environment.md) (needs many environments from this document).

## 1. Problem

The PatchLoop loop works: it finds an access-rule violation by its real effect, generates a guard, proves the guard and promotes it. But every part that **understands an agent** is written for one example, the τ-bench retail environment:

| What PatchLoop must know | How it is done today | Where |
|---|---|---|
| Which tools exist, and which change data | Hand-written tool lists | `runtime/policy.py` |
| Who is logged in | τ-bench lookup by email or name and ZIP code | `runtime/dispatcher.py` |
| Who owns which resource | Hardcoded `orders[order_id].user_id` | `runtime/policy.py`, `repair/validation.py` |
| What normal use looks like | τ-bench's 1,375 reference calls | `evaluation/replay.py`, `environments/tau_retail/` |

Retail-specific references counted on 5 October 2026: `policy.py` 27, `validation.py` 22, `repair/loop.py` 19, `dispatcher.py` 17, `demo.py` 16, `replay.py` 10, `campaign.py` 7, `agent.py` 6. The sandbox, version store, export, providers, dashboard and CLI have none.

**A packaged SDK does not fix this.** It would only deliver an engine that works on τ-bench retail.

## 2. Goal and non-goals

**Goal:** PatchLoop works on a customer's own tool-using agent without changes to engine code. τ-bench retail becomes the first implementation of a general interface, not a special case.

**Non-goals for version 1:**
- Rules other than authentication, ownership, tenant isolation and consent. Roles, amount limits and time windows come later (section 10).
- Agents that have neither recorded legitimate traffic nor a test environment. PatchLoop cannot prove anything about them.
- Running customer tools or customer data in PatchLoop's cloud. See the platform PRD, section 4.

## 3. Principles

1. **Trusted facts come from the customer's systems.** Identity, ownership data and recorded traffic come from the customer's authentication, data and logs, never from model output.
2. **The model proposes, recordings verify, a human confirms once.** The model can draft the tool classification and the resource map. PatchLoop checks the draft against recorded legitimate traffic. A person approves it before use.
3. **Discover before asking.** Read what the agent already declares (tool schemas, annotations, specifications) before asking the customer to write anything.
4. **One interface.** Every engine module depends only on the Environment interface (section 5), never on a specific environment.

## 4. The four things PatchLoop must understand

### 4.1 Tools

PatchLoop discovers tools automatically from the place where the agent already defines them:

| The agent uses | PatchLoop reads |
|---|---|
| MCP servers | `tools/list`: names, descriptions, JSON input schemas, and tool annotations |
| OpenAI-style function calling | The tool definitions the agent sends to the model |
| Python functions | Signatures, type hints and docstrings, through `inspect` |
| REST APIs | The OpenAPI specification |

Each tool gets one class: **public** (no login needed), **read** (returns private data), or **write** (changes data). The class is decided in this order:

1. A class that the customer declared in the configuration.
2. Evidence from recordings: a recorded call that changed data is a write.
3. MCP annotations (`readOnlyHint`, `destructiveHint`). The MCP specification treats annotations from untrusted servers as hints, so they are suggestions only.
4. A model proposal, which a human must confirm.

### 4.2 Identity

| Context | Source of the logged-in principal |
|---|---|
| Production | An identity hook that reads the customer's real session: for example a JWT `sub` claim, a session object, or the OAuth token of an MCP connection |
| Tests | A customer function `login_as(principal)` that opens a session as a chosen test user |

The tester logs in as user A through `login_as` and then attacks user B's resources. The model never sets or changes the session principal. This is the rule the dispatcher already enforces today.

### 4.3 Resource ownership

A **resource map** links each tool argument to the resource it names, and that resource to its owner:

```yaml
resources:
  customer_id:   {principal: true}                                     # the argument is the user
  ticket_id:     {table: tickets, owner: customer_id}                  # direct owner field
  attachment_id: {path: attachments.ticket_id -> tickets.customer_id}  # owner through another record
  org_id:        {tenant: true}                                        # tenant isolation
  product_id:    {public: true}                                        # no owner
```

**Kinds of resources:** the principal itself, a record with a direct owner field, a record owned through a path of records, a tenant, or a public resource.

**Three sources, used together:**
1. **Declared:** the customer writes the map. A typical agent needs about 10 lines.
2. **Inferred:** the model reads the tool schemas, sample test records and the policy, then proposes a map.
3. **Verified:** PatchLoop checks every proposed entry against recorded legitimate traffic (section 4.4). In a legitimate call, the resolved owner must equal the logged-in principal, or the resource must be public. Each mismatch is shown, with examples, before a human confirms the map.

### 4.4 Normal use

**Record mode** captures legitimate tool calls, one JSON line per call:

```json
{"tool": "get_ticket", "arguments": {"ticket_id": "T-1042"}, "principal": "cus_77",
 "owner_facts": {"tickets.T-1042.customer_id": "cus_77"}, "outcome": "ok",
 "recorded_at": "2026-10-05T10:12:03Z", "source": "staging"}
```

- **Sources:** staging traffic, the customer's existing integration tests, or legitimate tasks that the model generates and a human approves.
- **Privacy:** the runner removes personal values that the check does not need before it stores the recording. Recordings stay in the customer's environment unless they export them.
- **`owner_facts`** stores the ownership data the guard needed at the time of the call. This makes the recording usable without the live database.

**Decision-level utility.** A guard only allows or denies. So a guard preserves utility exactly when it **allows every recorded legitimate call** in that call's recorded context. This check needs no re-execution of tools and no test environment.

## 5. The Environment interface

Every engine module depends on this interface. `environments/tau_retail` becomes the first implementation.

```python
class Environment(Protocol):
    policy: str                                        # the customer's rules, plain text
    tools: dict[str, ToolSpec]                         # name -> schema, class, callable (callable for level B)
    resources: ResourceMap                             # confirmed map (section 4.3)

    def identify(self, session) -> str | None: ...     # trusted principal (section 4.2)
    def owner(self, state, tool, arguments) -> str | None: ...  # resolve through the resource map
    def recordings(self) -> Iterable[Recording]: ...   # legitimate traffic (section 4.4)

    # Level B only: a resettable test environment
    def login_as(self, principal) -> Session: ...
    def reset(self) -> State: ...
    def call(self, state, session, tool, arguments) -> str: ...
    def snapshot(self, state) -> dict: ...             # read state, to measure real effects
```

## 6. Support levels

| Level | The customer provides | PatchLoop can do |
|---|---|---|
| **A: decision level** | Tools, an identity hook, a resource map, recordings | Generate a guard and **prove** it: it allows every recorded legitimate call, and it denies mutated attacks (section 7). No test environment is needed. |
| **B: full loop** | Level A plus `login_as`, `reset`, `call` and `snapshot` | Everything at level A, plus the live tester, finding violations by their real effects, effect checks during validation, and retesting after repair. τ-bench retail is at level B today. |

Level A is how PatchLoop reaches many agents quickly. Level B is the strongest evidence.

## 7. Validation panels generated from recordings

Panels must not depend on hand-written arguments for one environment, as `repair/validation.py` does today. PatchLoop builds them by **mutating recorded legitimate calls**:

| Case | How it is made | Expected decision |
|---|---|---|
| Authorized | The recorded call, unchanged | Allow |
| Cross-user | Replace the resource with one owned by another principal from the identity pool | Deny |
| Unauthenticated | Remove the principal | Deny |
| Unconfirmed | A write call without matching consent | Deny |
| Unknown resource | Replace the resource identifier with one that does not exist | As the policy states, for example native error for orders and deny for users |
| Public | A call to a public tool | Allow |

Keep the existing protections: development and sealed panels use separate identity pools drawn from a secret seed, sealed results never return to the model, and every decision runs in a fresh sandbox process.

## 8. Onboarding flow

1. **`patchloop init`:** discover the tools, read the policy file, and write a draft `patchloop.yaml`.
2. **Review:** one screen with the class of each tool and the proposed resource map, plus every conflict found in the recordings. A person confirms.
3. **Record:** import or capture legitimate traffic.
4. **`patchloop run`:** level A, or level B if the test environment exists. The result is a guard with evidence, later as a pull request.

## 9. Configuration file

```yaml
# patchloop.yaml
agent:
  tools:
    source: mcp                      # mcp | openai | python | openapi
    server: "stdio:./tickets-mcp"
  identity:
    from: session.claims.sub         # trusted principal in production
  login_as: "myapp.testing:login_as" # level B only
policy: ./policy.md
resources: ./resources.yaml          # confirmed resource map
recordings: ./recordings/*.jsonl
environment:                         # level B only
  reset: "myapp.testing:reset"
  snapshot: "myapp.testing:snapshot"
```

## 10. Rule scope

| Version | Rules |
|---|---|
| 1 | Authentication before private access, ownership, tenant isolation, consent for write calls |
| Later | Role permissions, amount limits, rate and time windows, cross-resource business rules |

Version 1 targets ownership first, because ownership failures caused every violation in our live tests: the agent read another customer's order or profile.

## 11. Requirements

| ID | Requirement | Acceptance |
|---|---|---|
| I1 | Environment interface. All engine modules use it; none imports a specific environment. | A search finds no `tau_retail` import outside `environments/` and tests. All current tests pass. |
| I2 | τ-bench retail implements the interface | Replay 635/635 and guarded replay exit 0, unchanged |
| I3 | Resource map format and resolver: principal, direct owner, path, tenant, public | Unit tests for each kind, including paths of two or more steps |
| I4 | Recording format and decision-level utility check | A guard that denies one recorded legitimate call fails. Allow-all fails the security panel. |
| I5 | Panels generated by mutating recordings (section 7) | Hand-written panel arguments are removed. The overfit guard from earlier tests is still rejected. |
| I6 | A second example agent that is not τ-bench, for example a multi-tenant helpdesk | The same loop runs on it with no engine change |
| I7 | Python connector (middleware for in-process tools) | Example agent I6 uses it |
| I8 | Resource-map inference, verification against recordings, human confirmation | Conflicts are reported with examples. Nothing is used before confirmation. |
| I9 | MCP connector and record mode | One existing open-source MCP server works at level A |
| I10 | Documentation for integrators | The platform website's Guides section covers I7 and I9 |

## 12. Build order

| Step | Content | Unlocks |
|---|---|---|
| 1 | I1, I2 | No engine code depends on τ-bench any more |
| 2 | I3, I4, I5 | **Level A for any agent with recordings** |
| 3 | I6, I7 | Proof of generality |
| 4 | I8 | Faster onboarding |
| 5 | I9, I10 | Most real agents |
| 6 | Ownership paths of more steps, tenant hierarchies | More complex data models |

Steps 1–3 come first. They also give the RL workstream more environments to train on.

## 13. Interfaces with other workstreams

- **Platform:** the SDK exposes the Environment interface, the configuration file and the connectors as public API. The control plane receives level A and level B evidence bundles. Neither receives customer recordings unless the customer exports them.
- **RL:** each Environment implementation is a source of tasks. Panels generated from recordings give the training reward for any environment, not only retail.

## 14. Risks and open questions

| Risk or question | Response |
|---|---|
| The inferred resource map is wrong | Verify against recordings. Human confirmation is required. Report conflicts with concrete examples. |
| Recordings contain personal data | Redact in the runner. Keep only the ownership facts needed. Data stays in the customer's environment by default. |
| MCP annotations are wrong or missing | Treat them as hints. Recordings and human confirmation decide. |
| Level A has no effect evidence | Label level A results as decision-level proof. Recommend level B for high-risk agents. |
| Ownership changes over time | Store `owner_facts` per recorded call. Re-record after data-model changes. |
| Who owns this work? | Proposed: Mitudru Dutta, because the RL work needs the same environments. Confirm. |

## 15. Terms

- **Principal:** the logged-in user or service that the session belongs to.
- **Resource map:** the declaration of which argument names which resource, and who owns that resource.
- **Recording:** one captured legitimate tool call, with its principal and ownership facts.
- **Decision-level utility:** the guard allows every recorded legitimate call.
- **Level A / level B:** support without and with a resettable test environment.
