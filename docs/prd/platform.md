# PatchLoop Platform PRD: SDK, API access, documentation website, organizations and pricing

**Owner:** platform partner. **Status:** draft for review, 5 October 2026.
**Related:** [engine PRD](engine.md) (how PatchLoop finds, repairs and proves), [RL environment PRD](rl-environment.md) (separate workstream).

## 1. Problem and goal

The PatchLoop engine works on this repository's machine: it tests a tool-using agent, finds access-rule violations by their real effects, generates a guard, proves the guard with replayed legitimate traffic and secret panels, and promotes it. Today a customer cannot use it: there is no released package, no generic integration for their own agent, no access control, no documentation website and no way to pay.

**Goal:** turn the engine into a product that a team can install, connect to its own agents, operate as an organization, and buy.

**Positioning:** "Authorization remediation for AI agents: find, fix, prove." PatchLoop is not code review (CodeRabbit) and not functional test generation (TestSprite). Its closest neighbours are agent red-teaming tools, which find problems but do not repair them, and runtime guardrails, which block calls with rules that people write. PatchLoop's difference is the closed loop with proof. Accept findings from other tools, such as Promptfoo red-team reports, as incidents rather than competing on finding.

## 2. Users

| User | Need |
|---|---|
| Agent developer | Install in minutes, connect an agent, see findings and a proposed guard |
| Platform or security engineer | Run PatchLoop in CI, review guards as pull requests, keep evidence |
| Security lead or auditor | Exportable evidence: what was attacked, what was blocked, what still works |
| Organization admin | Members, roles, API keys, usage, billing |

## 3. Scope

**In scope:** the SDK and CLI release, the public SDK API, the hosted control plane (organizations, projects, members, API keys, runs, evidence, webhooks), the documentation website, pricing, billing, and the business operations listed in section 11.

**Out of scope:** engine internals (owned by the engine PRD), RL training (RL PRD), running customer tools or customer guard code in our cloud, and on-premises control plane installs before the Enterprise tier exists.

## 4. Architecture: runner and control plane

| Component | Where it runs | Responsibility |
|---|---|---|
| **Runner** (open source, the `patchloop` package) | Customer laptop, CI or private cloud | Executes the customer's tools against their test environment, runs campaigns and repairs, runs guards in the sandbox, produces evidence |
| **Control plane** (hosted, `services/api/`) | PatchLoop cloud | Organizations, keys, run history, evidence storage, dashboards, GitHub App, webhooks, usage and billing |

The control plane never receives customer source code or customer data unless the customer exports it in an evidence bundle. Evidence bundles contain hashes, guard source, redacted traces and validation summaries. They never contain provider keys, private seeds or sealed panel contents.

## 5. SDK and CLI

| ID | Requirement | Acceptance |
|---|---|---|
| S1 | Publish `patchloop` to PyPI with trusted publishing (OIDC) from GitHub Actions. The name is currently free. | A tagged release builds and publishes without a stored PyPI token |
| S2 | Semantic versioning, `CHANGELOG.md`, GitHub Releases | Each release has notes and a matching tag |
| S3 | One `patchloop` command with stable subcommands (`replay`, `demo`, `campaign`, `compare`, `reproduce`, `repair`, `export`, `dashboard`, `providers`), already present in `src/patchloop/cli.py` | Documented commands and exit codes stay stable within a major version |
| S4 | A small, typed public SDK API exported from `patchloop/__init__.py`. Everything else is internal. | `services/api/` and examples import only the public API |
| S5 | Move the τ-bench retail environment (2.3 MB of data) into a separate package, for example `patchloop-tau-retail`, so the core wheel carries no example data. Python extras add dependencies, not files, so an extra alone cannot do this. | The core wheel installs and runs without example data |
| S6 | Container images on `ghcr.io` for the runner and the sandbox worker | Images are pinned by digest in the docs |
| S7 | CI on every pull request: tests with the Docker sandbox backend, because GitHub runners may block the user namespaces that bubblewrap needs | The required check blocks merges on failure |
| S8 | A GitHub Action that runs a campaign on a pull request, fails on executed violations, and attaches evidence | A sample repository shows a failing and a passing run |

## 6. Generic integration (dependency on the engine)

The SDK has little value until it works with agents other than τ-bench retail. The full specification is in the [agent integration PRD](agent-integration.md). **Owner:** proposed Mitudru Dutta, to be confirmed.

What the platform needs from it:
- the Environment interface, the configuration file (`patchloop.yaml`) and the connectors (Python first, then MCP) as public SDK API;
- **level A** support (tools, identity hook, resource map, recordings; no test environment) so that most customers can start;
- **level B** support (plus a resettable test environment) for the full find, repair and retest loop;
- evidence bundles that state which level produced them.

## 7. Organizations, members and roles

| Requirement | Detail |
|---|---|
| Organization | Billing owner. Contains projects and members. |
| Project | One protected agent or agent system. Holds runs, guards, evidence and keys. |
| Roles | Owner (billing, delete), Admin (members, keys), Member (runs, evidence), Viewer (read only) |
| Single sign-on | Business tier and above (SAML or OIDC) |
| Audit log | Every key, member, guard-promotion and billing event, with actor and time. Exportable. |

## 8. API keys

| Requirement | Detail |
|---|---|
| Format | `pl_live_` or `pl_test_` followed by 32 random bytes (base62). Show the full key once, at creation. |
| Storage | Store only a SHA-256 hash plus the last 4 characters for display |
| Scope | Per project. Scopes: `runs:write`, `runs:read`, `evidence:read`, `admin`. |
| Life cycle | Optional expiry, rotation with overlap, immediate revocation, "last used" time |
| Limits | Per-key and per-organization rate limits, with usage metering for billing |
| Leak response | Register the key prefix with GitHub secret scanning when public. Revoke automatically on a confirmed leak report. |
| Model provider keys | Keep them on the runner side by default (bring your own key). The control plane stores them only for the optional managed-credits plan, encrypted with a key-management service. |

## 9. Control plane API v1

| Endpoint | Purpose |
|---|---|
| `POST /v1/projects/{id}/runs` | Register a run started by a runner; returns an upload target |
| `GET /v1/runs/{id}` | Status, findings summary, accepted guard hash |
| `POST /v1/runs/{id}/evidence` | Upload an evidence bundle |
| `GET /v1/runs/{id}/findings`, `GET /v1/runs/{id}/patches` | Findings and accepted guards |
| `POST /v1/projects/{id}/keys`, `DELETE /v1/keys/{id}` | Key management |
| Webhooks: `run.completed`, `finding.created`, `patch.accepted` | Signed with HMAC-SHA256, retried with backoff |

Requirements: an OpenAPI specification as the source of truth, idempotency keys on `POST`, cursor pagination, one error format, and versioning by URL prefix.

## 10. Documentation website

Build with MkDocs Material from `website/`, publish to GitHub Pages, and keep a version selector per release.

| Section | Content |
|---|---|
| Get started | Install, run the offline demo, connect a first agent, in under 15 minutes |
| Concepts | Target agent, tester, guard, violation by effect, utility proof, development and sealed panels, consent |
| Guides | Python tools, OpenAI tool schemas, MCP, CI and the GitHub Action, reviewing a guard pull request |
| Reference | CLI (generated from the command definitions), SDK (generated from docstrings), REST API (generated from OpenAPI) |
| Security model | What runs where, sandbox guarantees and limits, data handling, key handling |
| Limitations | What PatchLoop does not check: answer quality, facts, tone. Known test limits. |
| Changelog and pricing | Linked from every page footer |

Acceptance: a CI job checks links and runs every code sample against the released package.

## 11. Pricing and packaging

Every price below is a **starting hypothesis** to test with 3–5 design partners before launch. None is a decision.

| Tier | Price hypothesis | Includes |
|---|---|---|
| Open source | Free | Runner, CLI, SDK, local dashboard, bring your own model key, community support |
| Team | $99 per month per organization, 3 protected agents included, $29 per extra agent | Hosted runs and evidence history, GitHub Action, guard pull requests, 30-day retention |
| Business | $499 per month, 15 agents included | Single sign-on, audit-log export, scheduled campaigns, 1-year retention, email support with a response target |
| Enterprise | Custom | Self-hosted control plane, private networking, data-processing agreement, uptime commitment, security review support |

**Usage unit:** one protected agent per month, plus campaign runs above an included quota. **Model costs:** free of markup when customers bring their own key. Managed credits are passed through with a stated margin.

**Billing:** Stripe Billing with metered usage. Enterprise is invoiced annually. Decide the merchant of record and sales-tax handling before the first paid customer.

**Validation plan:** ask each design partner (1) whether they would accept a generated guard if it came with this proof, (2) which unit they expect to pay for, (3) their budget owner. Change the tiers from the answers.

## 12. Business operations

| Item | Requirement |
|---|---|
| Legal | Company entity, terms of service, privacy policy, data-processing agreement template |
| Licenses | Keep the MIT core. Keep third-party notices such as the vendored τ-bench `NOTICE.md`. Check the Nebius Token Factory terms for commercial use. |
| Security | A public security page, `SECURITY.md` with a disclosure address, a SOC 2 readiness plan before the Business tier sells |
| Support | A community channel for open source, email for paid tiers, a public status page |
| Brand | Domain, logo, social preview image for the repository |

## 13. Non-functional requirements

- **Security:** no customer code execution in the control plane, hashed API keys, encryption at rest and in transit, least-privilege service roles, dependency scanning in CI.
- **Privacy:** evidence is redacted by the runner before upload. Retention follows the tier.
- **Reliability:** paid-tier availability target 99.5% at launch. Runners must work when the control plane is unreachable.
- **Observability:** structured logs, request IDs, per-organization usage dashboards.

## 14. Milestones

| Milestone | Target | Exit criteria |
|---|---|---|
| P1: SDK 0.1 | October 2026 | On PyPI, `patchloop --help` works after a clean install, documentation website live with Get started and Concepts |
| P2: Generic integration and CI | November 2026 | Steps 1–3 of the agent integration PRD are done: one agent other than τ-bench works through the Python connector. The GitHub Action runs in a sample repository. |
| P3: Control plane alpha | December 2026 | Organizations, projects, roles, API keys, run and evidence upload, webhooks |
| P4: Paid beta | Q1 2027 | Billing live, 3–5 design partners on Team or Business, pricing revised from their feedback |

## 15. Metrics

Install to first finding (time), weekly active projects, runs per project, share of proposed guards accepted by reviewers, conversion from open source to Team, design-partner retention.

## 16. Risks and open questions

| Risk or question | Response |
|---|---|
| Who owns the generic integration? | Proposed: Mitudru Dutta (see the agent integration PRD). Confirm before P2. Without it, the SDK only demonstrates τ-bench. |
| MCP gateway before or after the Python connector? | Recommended after. Revisit if design partners use MCP mostly. |
| Overlap with red-teaming tools | Import their findings. Compete on repair and proof. |
| Buyers may not trust generated guards | The guard pull request with evidence is the main feature. Test this in interviews first. |
| Model-provider terms | Confirm commercial use and data handling before the paid beta |

## 17. Interfaces with other workstreams

- **Engine:** exposes the public SDK API, evidence-bundle format and connector contract. Changes to these require a note in the changelog.
- **RL:** may later supply a trained repair model as an option. The platform treats it as another model choice and does not depend on it.
