# PatchLoop

PatchLoop is being built to turn failures in tool-using agents into generated guard patches, regression tests, and reviewable evidence.

**Status — 5 October 2026:** live Nemotron repair on Nebius Token Factory, with Tavily guidance, passed isolated validation and was activated locally. Bounded generation, validation, trusted dispatch, replay and version promotion work. Agent conversations, confirmation, PR publication, dashboard, deployment and RL remain pending. See [implementation status](docs/IMPLEMENTATION_STATUS.md) and the [candid research review](docs/RESEARCH_WEAKNESSES.md).

## Run locally

Linux, Python 3.10+, `/usr/bin/python3`, and **bubblewrap** (`bwrap`, user namespaces enabled). On Debian/Ubuntu: `sudo apt install bubblewrap`. Python runtime uses the standard library; tests require pytest. Candidate execution fails closed if isolation is unavailable.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m patchloop.replay
python -m patchloop.demo --output artifacts/reference-comparison.json
python -m patchloop.replay --guarded
```

The baseline reproduces 635 reference tasks with 1,375 scheduled calls. Guarded replay compares **outputs and final state** and applies the hash-bound utility manifest. It reports 634 matching tasks and the contained `test-64` identity conflict, then exits 0. An unexplained preservation failure, baseline mismatch, executed violation or added execution error still exits 1, including in the conflict case. All 635 outcomes remain visible: the task declares Harper while its lookup and subsequent actions concern James.

The offline demo compares two unauthorized attempts against the handwritten guard. Validate the actual saved model-generated candidate without API calls or activation:

```bash
python -m patchloop.repair --verify examples/guards/ownership.py
```

The candidate is copied unchanged from the model response. [Historical live evidence](docs/evidence/live-repair-2026-10-05.json) records request IDs, usage and source hash. Its original fixed-case gate was vulnerable to identity memorization and is superseded. Current verification adds per-run randomized development and sealed identity panels, actual tool-effect checks, and complete utility replay. This remains one exploratory deterministic repair, not an agent campaign or transfer study.

## Runtime integrations

Clients use [Nebius Token Factory's inference API](https://docs.tokenfactory.nebius.com/) and [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search). Configure keys in environment variables; do not commit them. `.env.example` lists required names. The application does not automatically load `.env` files.

```bash
python -m patchloop.providers models    # needs NEBIUS_API_KEY
# Set NEBIUS_MODEL to an exact NVIDIA Nemotron ID returned by your catalog.
python -m patchloop.providers smoke     # actual inference call; records model/id/usage
python -m patchloop.providers guidance  # needs TAVILY_API_KEY; actual Tavily search
```

Both services were verified live. Integrated repair used `nvidia/nemotron-3-super-120b-a12b`, with three Tavily public references supplied as untrusted guidance. Generation used 4,821 prompt and 245 completion tokens. Retrieval's contribution to repair quality is unmeasured.

```bash
set -a
source .env  # local ignored credentials, following .env.example
set +a
python -m patchloop.repair --attempts 3
```

The worker reproduces the incident, retrieves guidance, generates at most three candidates, validates outside the broker process, and activates only accepted source under a locked parent-version check. Failed attempts retain evidence and usage. Contained versions are revalidated without inference/search. Use a new `--store artifacts/separate-versions` to explicitly start another experiment from baseline; this sends paid requests.

Each run creates a private 32-byte random seed and freezes two disjoint identity panels using actual IDs from the synthetic fixture. Each panel covers all nine protected tools, authorized/cross-user/unauthenticated calls, unknown orders and public tools. The model receives aggregate development diagnostics only, never seeds, sealed diagnostics or archive conflict identities. Sealed checks run once on the first development-passing candidate; failure or incomplete execution ends the run without further model feedback. The private `security-seed` stays in ignored artifacts with permissions 0600. Panels share the public benchmark and owner-authored oracle; they do not establish independent-domain generalization.

Traces, diffs, responses, guidance, validation and immutable versions remain under ignored `artifacts/`. Subsequent runs save exact provider request payloads without credentials; the first live run retained reconstructable inputs and response but did not save the payload separately. Tavily failure is recorded, never fabricated; required Nebius inference must succeed. No additional keys are needed locally.

## Trust and scope

The dispatcher gets identity from the first successful benchmark lookup and locks it for that conversation. A later lookup cannot replace it. Identity is not accepted from tool arguments. Reference replay explicitly seeds the task user because many recorded tasks omit login turns; this does not test authentication or consent in conversations.

Benchmark lookup by email or name/ZIP is **not production authentication**. Anyone knowing those details can identify that fixture user. The guard covers user/order authentication and ownership; confirmation, duplicate operations and concurrency need additional contracts. Existing tool business checks remain in place. Generated Python runs in a separate bubblewrap namespace, without project/data/test/credential mounts or external network access. It receives only broker-resolved JSON context and returns decisions. The broker independently evaluates actual effects and utility; candidate output cannot supply validation scores. Resource limits bound execution. These finite tests do not prove universal sandbox security or establish readiness for arbitrary repository execution/public hosting.

Replay batches decisions per task, reusing them only if the actual trusted context matches. Every context executes in a fresh child process and namespace, including fresh imported-module state. Randomized checks also exercise singleton calls, so behaving safely only in a batch is insufficient. Whole-database snapshots/hashes remain to detect unexpected mutations.

**Repair scope:** this is a contract-to-code baseline. The broker already chooses protected tools and resolves ownership, and the prompt supplies the intended comparison. Those difficult integration choices are handwritten, not discovered by Nemotron. A richer adapter-repair experiment needs its own read-only capability contract and separate evaluation before extending candidate data access.

## Application and license

The first application is derived from [Sierra's τ-bench retail environment](https://github.com/sierra-research/tau-bench), pinned in [NOTICE.md](patchloop/apps/tau_retail/NOTICE.md). Its prompt-only policy rules are an intentional benchmark design. This project modifies its own wrapper, preserves the vendored source/data, and makes no vulnerability claim against Sierra.

Original project code: [MIT](LICENSE). Vendored source: [Sierra MIT license](patchloop/apps/tau_retail/LICENSE.sierra).

## Repository layout

| Path | Purpose |
|---|---|
| `patchloop/apps/tau_retail/` | Pinned tools, policy, synthetic data, reference tasks |
| `patchloop/policy.py` | Handwritten ownership/authentication checks and state-effect evaluator |
| `patchloop/dispatcher.py` | Session lock, trusted state, tool trace, observation/enforcement modes |
| `patchloop/replay.py` | Baseline state replay and guarded output/state comparison |
| `patchloop/demo.py` | Deterministic before/after evidence export |
| `patchloop/providers.py` | Nebius/Tavily clients and explicit live smoke commands |
| `patchloop/repair.py` | Bounded generation, validation, offline verification and promotion |
| `patchloop/sandbox.py`, `patchloop/_guard_worker.py` | Isolated decisions and resource limits |
| `patchloop/versions.py` | Immutable artifacts and stale-parent rejection |
| `patchloop/utility_manifest.json` | Archive hash and explicit conflict disposition |
| `patchloop/security.py`, `patchloop/manifest.py` | Private randomized checks, effect checks and shared archive contract |
| `examples/guards/ownership.py`, `docs/evidence/` | Unchanged generated candidate and credential-free live evidence |
| `tests/` | Regression and negative cases |
| `scripts/vendor_tau_bench.py` | Rebuild vendored files from the pinned upstream commit |
| `docs/PRD.md` | Current product plan; future requirements remain marked as pending |
| `docs/IMPLEMENTATION_STATUS.md` | Verified scope, document corrections, next acceptance gates |
| `docs/paper/` | Earlier research protocol, standalone LaTeX/PDF, illustrative calculations |

## Research status

The manuscript describes a proposed study, including an optional later RL branch. Its v0.3 status is a historical snapshot: a narrow frozen-model repair now works, but no training, transfer result or RL improvement exists. The PRD supersedes its earlier toy-fixture plan. A handwritten guard solves this subset too; added value requires a controlled comparison. Local replay is engineering evidence, not a completed empirical paper.

```bash
python docs/paper/statistics_calculations.py
cd docs/paper
tectonic --keep-logs --outdir build PATCHLOOP_RL_Research_Paper.tex
```

LaTeX compilation and planning arithmetic are separate from application experiments. Training remains conditional on a validated evaluator, suitable data, measured reward signal, and an affordable hardware pilot.
