# PatchLoop

PatchLoop is being built to turn failures in tool-using agents into generated guard patches, regression tests, and reviewable evidence.

**Status — 5 October 2026:** Local HTML dashboard, native Nemotron conversations, adversarial tester, action-bound consent, repair/retest loop and reproduction bundles are implemented. Live conversations and a small tester campaign completed on Nebius Token Factory. The original generated ownership guard passes current checks. Richer adapter repair works with a scripted test provider, but all six live adapter candidates were rejected and none activated. Public hosting, a measured four-condition study and RL remain pending. See [current evidence](docs/evidence/local-product-2026-10-05.json), [implementation status](docs/status/implementation.md) and [research weaknesses](docs/research/weaknesses.md).

## Run locally

Linux, Python 3.10+, `/usr/bin/python3`, and **bubblewrap** (`bwrap`, user namespaces enabled). On Debian/Ubuntu: `sudo apt install bubblewrap`. Python runtime uses the standard library; tests require pytest. Candidate execution fails closed if isolation is unavailable.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
patchloop --help
patchloop replay
patchloop demo --output artifacts/reference-comparison.json
patchloop replay --guarded
```

The baseline reproduces 635 reference tasks with 1,375 scheduled calls. Guarded replay compares **outputs and final state** and applies the hash-bound utility manifest. It reports 634 matching tasks and the contained `test-64` identity conflict, then exits 0. An unexplained preservation failure, baseline mismatch, executed violation or added execution error still exits 1, including in the conflict case. All 635 outcomes remain visible: the task declares Harper while its lookup and subsequent actions concern James.

The offline demo compares two unauthorized attempts against the handwritten guard. Validate the actual saved model-generated candidate without API calls or activation:

```bash
patchloop repair --verify examples/guards/ownership.py
```

The candidate is copied unchanged from the model response. [Historical live evidence](docs/evidence/live-repair-2026-10-05.json) records request IDs, usage and source hash. Its original fixed-case gate was vulnerable to identity memorization and is superseded. Current verification adds per-run randomized development and sealed identity panels, actual tool-effect checks, and complete utility replay. This is one exploratory deterministic repair. Separate conversation evidence exists; no transfer study has been completed.

## Runtime integrations

Run the local product after exporting your provider variables:

```bash
patchloop dashboard --store artifacts/versions
# Open http://127.0.0.1:8080
```

The dashboard shows conversations, actual record changes, and guard source/test results. "Challenge this version" runs one bounded scenario. Checking "Repair a finding and test again" starts a repair only when a complete campaign observes a violation. "Reproduce locally" downloads the exact run's guard, recorded input and observed effects; replay requires no model calls. With no keys, the page still displays the current source and explains configuration. The service binds to loopback, rejects foreign origins/hosts, limits sessions/jobs, serializes each conversation, and caps inference at 80 calls per server process. This is a local workspace, not a public tenant service.

The default `artifacts/product-versions` store starts with an explicitly labelled unrepaired baseline. `--store artifacts/versions` uses the previously generated fixed-rule guard; consent is independently enforced for that comparison. Conversations keep their initial guard even if a later job promotes another version. Keys remain in the Python orchestration process.

```bash
patchloop campaign challenge --reference --cases 1 --turns 1
patchloop campaign challenge --baseline --cases 1 --turns 1
patchloop campaign cycle --store artifacts/product-versions
```

These commands make paid runtime inference calls. A cycle has a shared 40-request budget, at most three customer challenges per scenario and three repair candidates. A zero-finding run is saved honestly; no fixed incident is substituted. Missing observations are marked partial/indeterminate. Large campaigns and public deployment remain a separate verification step.

Optional browser checks use a scripted provider and make no paid requests:

```bash
python -m pip install playwright
python -m playwright install chromium
python scripts/check_dashboard_browser.py
```

For hosts where bubblewrap is unavailable, build the standalone candidate image and explicitly select Docker:

```bash
docker build -f docker/sandbox.Dockerfile -t patchloop-guard:local .
PATCHLOOP_SANDBOX=docker python -m pytest -q tests/test_sandbox.py
PATCHLOOP_SANDBOX=docker patchloop dashboard
```

The candidate container has a read-only root, no shared-memory mount, no network, no capabilities, a non-root user and process/memory/CPU limits. Only the standalone worker enters its image; `.dockerignore` excludes keys, fixtures and project files. Cleanup removes timed-out workers. The trusted host owns Docker access; never mount the Docker socket into a publicly accessible frontend. AI Cloud deployment is deferred until the project configuration is available.

Clients use [Nebius Token Factory's inference API](https://docs.tokenfactory.nebius.com/) and [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search). Configure keys in environment variables; do not commit them. `.env.example` lists required names. The application does not automatically load `.env` files.

```bash
patchloop providers models    # needs NEBIUS_API_KEY
# Set NEBIUS_MODEL to an exact NVIDIA Nemotron ID returned by your catalog.
patchloop providers smoke     # actual inference call; records model/id/usage
patchloop providers guidance  # needs TAVILY_API_KEY; actual Tavily search
```

Both services were verified live. Integrated repair used `nvidia/nemotron-3-super-120b-a12b`, with three Tavily public references supplied as untrusted guidance. Generation used 4,821 prompt and 245 completion tokens. Retrieval's contribution to repair quality is unmeasured.

```bash
set -a
source .env  # local ignored credentials, following .env.example
set +a
patchloop repair --attempts 3
```

The worker reproduces the incident, retrieves guidance, generates at most three candidates, validates outside the broker process, and activates only accepted source under a locked parent-version/interface check. Failed attempts retain evidence and usage. Contained versions are revalidated without inference/search. Use a new `--store artifacts/separate-versions` to explicitly start another experiment from baseline; this sends paid requests.

`--interface adapter` supplies raw arguments, tool schemas, policy text, selected read-only rows and trusted consent metadata. It omits computed ownership/protection flags and does not provide the fixed-rule guard as an answer. The generated function chooses tool protection and record relationships. All six exploratory live candidates failed the gate; the gate was not weakened to accept them. `--interface fixed` retains the earlier contract-to-code comparison.

The comparison runner freezes separate discovery/evaluation conversations and shares private panels, candidate limits and generation temperature across independent draws and feedback repair:

```bash
patchloop compare --cases 1 --turns 1 --attempts 2 --requests 80
```

It compares unrepaired, independent generation, feedback repair and handwritten enforcement. If discovery finds no complete incident, repair conditions are marked not run. Tokens/request IDs and unsuccessful repairs are retained; dollar costs stay unknown until provider prices/billing are supplied. The runner is implemented, but a measured live four-condition result has not been produced.

Export accepted evidence for review without private cases or seeds:

```bash
patchloop export --guard examples/guards/ownership.py \
  --validation artifacts/YOUR_VERIFICATION_RUN/validation.json \
  --output artifacts/reviewable-patch
```

The bundle contains the exact source, an applicable source/evidence diff and a PR description. Export requires matching hashes, complete utility coverage and accepted development/sealed checks; it relies on trusted validation files. It does not independently prove model origin.

Each run creates a private 32-byte random seed and freezes two disjoint identity panels using actual IDs from the synthetic fixture. Each panel covers all nine protected tools, authorized/cross-user/unauthenticated calls, unknown orders and public tools. The model receives aggregate development diagnostics only, never seeds, sealed diagnostics or archive conflict identities. Sealed checks run once on the first development-passing candidate; failure or incomplete execution ends the run without further model feedback. The private `security-seed` stays in ignored artifacts with permissions 0600. Panels share the public benchmark and owner-authored oracle; they do not establish independent-domain generalization.

Traces, diffs, responses, guidance, validation and immutable versions remain under ignored `artifacts/`. Subsequent runs save exact provider request payloads without credentials; the first live run retained reconstructable inputs and response but did not save the payload separately. Tavily failure is recorded, never fabricated; required Nebius inference must succeed. No additional keys are needed locally.

## Trust and scope

The dispatcher gets identity from the first successful benchmark lookup and locks it for that conversation. A later lookup cannot replace it. Identity is not accepted from tool arguments. Reference replay explicitly seeds the task user because many recorded tasks omit login turns; this does not test authentication or consent in conversations.

Benchmark lookup by email or name/ZIP is **not production authentication**. Anyone knowing those details can identify that fixture user. Consent requires the external user's exact "yes" after an exact proposal, expires after ten minutes, binds action/arguments/identity/version, and is consumed once. Model/tool text grants no permission. Recorded timestamps preserve expiry during offline replay. Adapter guards decide whether to enforce this trusted metadata; the independent evaluator records unconfirmed effects. Fixed-rule guards use separate handwritten consent enforcement. Duplicate operations, concurrency and broader business policy still need additional contracts.

Generated Python runs in an isolated bubblewrap namespace or an explicitly selected Docker worker, without project/test/credential mounts or external network. Adapter mode receives selected synthetic fixture rows through JSON; it has no database write capability. The broker independently evaluates actual effects and utility; candidate output cannot supply validation scores. Resource limits bound execution. These finite tests do not establish readiness for arbitrary repository execution or public hosting.

Replay batches decisions per task, reusing them only if the actual trusted context matches. Every context executes in a fresh child process and namespace, including fresh imported-module state. Randomized checks also exercise singleton calls, so behaving safely only in a batch is insufficient. Whole-database snapshots/hashes remain to detect unexpected mutations.

**Repair scope:** fixed mode is a contract-to-code baseline: the broker selects protected tools and resolves ownership. Adapter mode removes those answers from its context, while preserving trusted identity, consent and independent effect checking. Its prototype works with scripted protocol fixtures; live generation has not yet produced an accepted adapter. Neither condition demonstrates general repair ability or superiority to direct enforcement.

## Application and license

The first application is derived from [Sierra's τ-bench retail environment](https://github.com/sierra-research/tau-bench), pinned in [NOTICE.md](src/patchloop/environments/tau_retail/NOTICE.md). Its prompt-only policy rules are an intentional benchmark design. This project modifies its own wrapper, preserves the vendored source/data, and makes no vulnerability claim against Sierra.

Original project code: [MIT](LICENSE). Vendored source: [Sierra MIT license](src/patchloop/environments/tau_retail/LICENSE.sierra).

## Repository layout

```
src/patchloop/              The engine and SDK (pip package "patchloop")
  cli.py                    The `patchloop` command
  providers.py              Nebius Token Factory and Tavily clients
  runtime/                  Trusted tool boundary: dispatcher, policy, consent, guard inputs
  sandbox/                  Isolated guard execution (bubblewrap or Docker) and its worker
  repair/                   Repair loop, validation panels, version store, patch export
  evaluation/               Agent sessions, tester campaigns, replay, comparison, reproduction
  dashboard/                Local workspace server and its web assets
  environments/tau_retail/  Vendored τ-bench retail environment, reference tasks, utility manifest
tests/                      Test suite (pytest)
examples/guards/            Saved model-generated guard
scripts/                    Vendoring and browser-check scripts
docker/                     Sandbox worker image
rl/                         RL environment and training workstream
services/api/               Hosted API and API-key access workstream
website/                    Public documentation website workstream
docs/
  prd/                      engine.md, agent-integration.md, platform.md, rl-environment.md
  status/                   Implementation status and acceptance gates
  research/                 Research weaknesses and the protocol manuscript (paper/)
  evidence/                 Credential-free live evidence
```

Each workstream directory has a README that names its owner, scope and the PRD it follows.

## Research status

The manuscript describes a proposed study, including an optional later RL branch. Its v0.3 status is a historical snapshot: a narrow frozen-model repair now works, but no training, transfer result or RL improvement exists. The PRD supersedes its earlier toy-fixture plan. A handwritten guard solves this subset too; added value requires a controlled comparison. Local replay is engineering evidence, not a completed empirical paper.

```bash
python docs/research/paper/statistics_calculations.py
cd docs/research/paper
tectonic --keep-logs --outdir build PATCHLOOP_RL_Research_Paper.tex
```

LaTeX compilation and planning arithmetic are separate from application experiments. Training remains conditional on a validated evaluator, suitable data, measured reward signal, and an affordable hardware pilot.
