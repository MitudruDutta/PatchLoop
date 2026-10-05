# Implementation status and document audit

**Reviewed:** 5 October 2026 (Asia/Kolkata). **Scope:** README, PRD v0.4, manuscript/LaTeX/PDF v0.3 snapshot, source/reference data and local implementation. Local engineering checks, live conversations and exploratory generations do not establish a completed research study. See [current evidence](../evidence/local-product-2026-10-05.json) and [research weaknesses](../research/weaknesses.md).

## Acceptance-gate correction

The original gate accepted a guard that enforced ownership only for `customer-*` and two known fixture IDs. Regression tests confirm that it passed the old fixed boundaries and incident, then failed the new randomized gate. The old live-run summary is historical evidence of inference/execution, not sufficient security validation.

The unchanged generated guard passed [revalidation](../evidence/review-validation-2026-10-05.json): 230 development and 230 sealed cases, 108 singleton checks, 72 actual-effect checks, 43 fixed boundary checks, and all 635 archive tasks/1,375 calls. All nine protected tools are covered. All 634 preservation cases passed; the explicit conflict remained contained.

Per-run private seeds freeze disjoint development/sealed identity pools from the synthetic benchmark. Seeds are stored outside candidate mounts in ignored files with mode 0600. Development feedback uses an aggregate allowlist; identity-conflict records, seeds and sealed diagnostics never enter model feedback. Sealed checks execute once after development selection; rejection or incomplete execution ends repair without another model call. This is randomized local verification, not independently authored final evaluation.

Replay batches contexts per task, uses cached decisions only for identical trusted contexts, and falls back to an actual call when context changes. Each context gets a fresh child process/namespace and imported-module state. Security checks also exercise the real singleton interface, rejecting guards that behave correctly only in batches. Full database snapshots/hashes are retained to detect unexpected mutations; record-level optimization is deferred.

## Historical live repair evidence

The first integrated repair completed with `nvidia/nemotron-3-super-120b-a12b` on Nebius Token Factory. It consumed three Tavily guidance results and activated its first candidate after validation. Source is copied unchanged to [ownership.py](../../examples/guards/ownership.py); the credential-free [run summary](../evidence/live-repair-2026-10-05.json) includes provider request IDs and source/version hashes.

- Before: two executed violations (private profile disclosure and another user's order cancellation).
- After: both unsafe calls denied, zero executed violations/errors, legitimate cancellation completed.
- Boundary checks: 43/43 passed.
- Archive: all 635 tasks and 1,375 calls ran. All 634 policy-consistent tasks preserved outputs and final state. `test-64` remained reported and contained; it is explicitly excluded only from preservation.
- Generation: 4,821 prompt + 245 completion = 5,066 tokens; candidate generation/validation took 64.893 seconds. This excludes initial reproduction and Tavily retrieval and is not a full cost benchmark.

The run started at `2026-10-04T18:46:21Z`, which is 5 October in the workspace timezone. Full traces, guidance, response, diff and outcomes remain under ignored `artifacts/repair/2232c3580b3840e4a08e4657fbb89ef1/`. That first run did not separately save the exact request payload; reconstructable inputs remain available. Subsequent runs save `request.json` without credentials. No model weights were updated.

## What works

The local product now connects native conversations, a model-driven tester, trusted effects, bounded repair, version promotion and retesting. A full scripted-provider integration passed the actual private panels and complete archive gate. This proves orchestration behavior; the scripted source is not live model evidence. A live reference-condition campaign used six model calls and 27,069 tokens, with one tester turn and no observed violation.

The richer adapter experiment made six live generation calls across three exploratory runs. All candidates failed boundaries: nested-record interpretation, native-error preservation, public-tool overblocking and, in one earlier candidate, cross-user profile/address access. None reached promotion. The gate was not weakened. Each run made a functional Tavily search with three results. The final run was explicitly continued from two to three total candidates on the same private suite.

The last candidate's fresh post-rejection panels also failed authorized address changes because it assumed a `user_id` field inside user records; real user identifiers are dictionary keys. These diagnostics did not override its failed boundary or authorize promotion. Boundary-schema/native-error expectations need independent review. The current prompt derives actual record fields from the fixture; that improvement is locally tested without claiming another live generation. An accepted live adapter and a live discovered-incident repair/retest remain open gates.

| Component | Evidence | Limit |
|---|---|---|
| Baseline replay | All 635 tasks reproduce the pinned reference final-state hashes | State equality alone cannot detect disclosures or changed outputs |
| Trusted session | First successful lookup binds identity; failed lookup does not; subsequent lookup cannot replace it | Email/name/ZIP lookup is benchmark identification, not verified real-world authentication |
| Reference guard | Nine user/order tools reject unauthenticated or cross-user access before invocation; conversations enforce exact-action consent | Handwritten; broader retail-policy enforcement is pending |
| State evaluator | Compares actual user/order/product changes; records changes even when tools raise | Trusted broker interpreter is separate from candidate execution; scope is known retail effects |
| Disclosure evaluator | Records unauthorized successful profile/order reads without requiring a state change | Scoped to the two known JSON-returning read tools |
| Tool trace | Copies arguments/results, identities, record changes, state hashes, attempted/executed labels and guard hash | Broker is trusted; candidate process supplies decisions, never evaluation scores |
| Offline comparison | Two unauthorized attempts execute in baseline; guard contains both; legitimate cancellation succeeds | Deterministic recorded tool calls, not stochastic agent behavior |
| Guarded utility replay | 634/635 tasks preserve every output and final state; the remaining identity conflict is exposed | Fixture users are seeded; no confirmation turns exist; public cases are not sealed final tests |
| Provider clients | Catalog and live inference verified; integrated repair consumed three Tavily results | No measured benefit from retrieved guidance; failed calls are exposed |
| Candidate executor | Read-only bubblewrap root/dev, no temporary directory; optional candidate-only Docker image; clean environment/network and resource limits | Linux-only; finite probes do not establish universal isolation or public-host readiness |
| Repair worker | Up to three candidates; recorded tester incident plus fixed regression, complete coverage/output/state checks, development/sealed checks and failures retained | Accepted live repair remains the fixed-rule condition; richer live candidates were rejected |
| Version activation | Exact source hash, immutable artifacts, locked compare-and-swap parent/interface check | Local trusted orchestration; no automatic production deployment |
| Support agent | Native Nemotron tool calls through dispatcher; complete messages, request accounting, trace and changed records | Live smoke completed; one synthetic domain and bounded sessions |
| Consent | External exact yes, single use, exact arguments/identity/version, ten-minute expiry and timestamped replay | Fixed guard uses separate enforcement; adapter decides from trusted consent metadata |
| Adversarial tester | Nemotron customer messages; signatures derived from executed tool effects; zero findings retained | One small live reference campaign; no robust attack-rate estimate |
| Closed loop | Tester finding starts repair; exact recorded calls are checked; accepted version is challenged again | Full gate demonstrated with a scripted provider, not live adapter success |
| Dashboard | Local HTML views for conversation/effects/source/checks; challenge and reproduction actions | Desktop/mobile browser checks use a scripted provider; binds only to loopback |
| Reproduction/export | Frozen run source and observed effects; private-material-free patch/evidence/PR-description bundle | Relies on trusted saved validation files; does not certify provider origin |
| Four-condition runner | Frozen discovery/evaluation conversations, matched candidate limits/temperature and shared private panels | No measured live four-condition study yet; dollar cost is unknown |

The final local counts are recorded in [current evidence](../evidence/local-product-2026-10-05.json). Tests cover the ID-specific bypass, development-ID memorization, batch-dependent behavior, filesystem state channels, private seeds, feedback exclusions, sealed failure stopping, manifest/coverage integrity, native provider envelopes, consent spoofing/expiry, actual adapter effects, complete discovery/repair/retest, shared budgets, origin/host/path boundaries, frozen bundles and public evidence filtering. Passing these cases does not establish universal security.

Before correction, an installed wheel reproduced the full archive under the original gate. The corrected wheel was separately built and installed into a fresh temporary directory: from `/tmp` with an empty environment, it loaded the manifest/archive, generated both 230-case panels and executed a stateful guard batch with isolated contexts. Full corrected-gate revalidation ran from the workspace without provider calls. Saved source, historical model response and active artifact agree on hash `c38fa12f2aeb244d1795e40f5447907de5fd8cdbd99b2728d4dd50471ed605de`. Vendored tools/data remain unchanged. Installation checks are not treated as security evidence.

## Reference identity conflict: `test-64`

The unchanged archive records:

- Task user: `harper_moore_6183`.
- First action: `find_user_id_by_name_zip(first_name="James", last_name="Sanchez", zip="60623")`.
- Actual lookup result: `james_sanchez_3954`.
- Subsequent profile, order, and exchange calls target James's records, including order `#W7464385`.

Seeding the declared task user and also allowing these calls would violate the one-user contract. The handwritten guard rejects the identity switch and those accesses. Guarded replay reports the original mismatch and applies the manifest: contained known conflict exits **0**; an unexpected preservation failure, baseline mismatch, executed violation or extra execution error exits **1**, including in the conflict case. No identity rebinding is permitted to manufacture preservation.

The baseline archive and its expected hashes remain unchanged. All 635 original tasks stay in reported denominators. The other 634 match under the scoped guard. No task is silently removed, relabelled, or granted privileged access to manufacture a perfect score.

The local [utility manifest](../../src/patchloop/environments/tau_retail/utility_manifest.json) binds the unchanged archive hash and records the conflict's disposition: execute/report it and require containment, but do not require contradictory authorized behavior. Independent human review remains pending and is explicitly recorded. Every candidate must return all expected IDs and call counts, with no added execution errors. A corrected derived case may be added with provenance; it cannot replace the original record. This is a local reference-data/contract inconsistency, not a security claim against τ-bench; no upstream issue/PR was created.

## Document findings and corrections

| Previous assertion or gap | Correction | Consequence |
|---|---|---|
| All 1,375 reference actions are policy-correct | `test-64` conflicts with task-user seeding; actions are a reference archive requiring review | Freeze utility semantics before using them as a patch-acceptance oracle |
| Final-state equality establishes legitimate behavior | A denied private read can leave identical state | Compare outputs and state; test unauthorized disclosure explicitly |
| Earlier README implied a complete repair/publication workflow | Local conversations, repair/retest, HTML dashboard and review bundles exist; public hosting remains pending | Keep current capabilities and planned services explicit |
| PRD says no implementation exists | Partial baseline now exists | Status points here; G0 remains incomplete until evaluator/executor boundaries are validated |
| Confirmation transcript is exclusive to agents | Non-agent systems also have conversation/consent state | Specify trusted, action-bound consent; do not use transcript presence as novelty |
| Reference calls can test confirmation | They contain actions, not the required explanation and user confirmation turns | Add separately authored consent conversations before claiming confirmation enforcement |
| Prompt-only policy removes the direct-enforcement objection | A manual guard still solves this subset | Measure repair effort/cost and utility against it; do not drop the comparator to save demo time |
| Video promises every later attempt will be blocked | Unmeasured future result | Show actual rates, failures, denominators and scope |
| Unchanged benchmark failures require planted defects | Observation can measure its intentional prompt-only policy design | Keep fault-injection settings separately labelled |
| Public benchmark train/dev/test calls are a final held-out evaluation | They are all visible and used for regression here | Author fresh sealed cases; one codebase does not establish cross-implementation transfer |
| The paper's original toy-fixture plan matches this product | Current PRD uses retail benchmark; manuscript is an earlier protocol snapshot | Synchronize a future empirical manuscript from real experiments; do not imply current prototype completed that protocol |

The standalone manuscript/LaTeX/PDF remain v0.3 historical protocol artifacts and were not rebuilt in this step. Current engineering evidence is recorded here and in the live summary; it is not retroactively presented as their planned empirical study.

## Reproduction

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
patchloop demo --output artifacts/reference-comparison.json
patchloop replay
patchloop replay --guarded
patchloop repair --verify examples/guards/ownership.py
```

Guarded replay keeps the known conflict visible while treating its manifest-defined containment as success. Offline verification adds fresh private identity panels and effect checks without provider requests or activation. The JSON demo contains synthetic results and before/after hashes.

Provider checks require separately configured environment variables:

```bash
patchloop providers models
patchloop providers smoke
patchloop providers guidance
```

Set `NEBIUS_API_KEY`, an exact catalog-selected NVIDIA Nemotron `NEBIUS_MODEL`, and `TAVILY_API_KEY`. These commands send real requests; they have no automatic fallback or fabricated success. Keys are not written into reports. Tavily success requires usable results, not merely HTTP 200. Guidance is untrusted public reference text.

For integrated repair, export ignored `.env` configuration with `set -a; source .env; set +a`, then run `patchloop repair --attempts 3`. The default local version is already repaired, so reruns revalidate without provider calls. To intentionally regenerate from baseline, use a fresh `--store` directory. Offline `--verify` requires no keys and does not activate a version.

## Next implementation gates

| Priority | Concrete next artifact | Acceptance condition |
|---|---|---|
| Implemented locally | Utility manifest and isolated candidate execution | Hash-bound conflict semantics and negative cases exist; independent review and broader hosting integrity tests remain pending |
| Implemented locally | Bounded Nemotron target-agent loop | Real runtime call smoke and complete traces; serial tools; fixed budgets; fixture identification limitation disclosed |
| Implemented locally | Frozen-model guard generation and Tavily guidance | Actual diff, bounded budget, complete public replay, retained failures, exact-source promotion and runtime guidance are verified; multiple incident streams and independent final cases remain pending |
| Next | Accepted live adapter and discovered-incident cycle | Preserve current gates; retain failed attempts; obtain a complete live discovery/repair/retest without a fixed-demo substitute |
| Next | Measured four-condition pilot | Runner exists; collect matched-budget results, costs and human reference labor before making usefulness claims |
| Implemented locally | Dashboard/reproduction/review output | Browser-tested local viewer and frozen source/effects bundle; public multi-user hosting and deployment remain pending |
| Later | RL | Consent semantics are implemented; RL still requires data, signal, pinned training/update/save/reload evidence, measured costs and matched SFT controls |

User-provided credentials remain in ignored local `.env` with restrictive permissions, never source or published evidence. Live conversations, tester inference, Tavily use, fixed-rule generation and local promotion occurred. A local demo experience and review bundles exist. Public deployment/test access, measured service feedback and RL remain pending. Release materials are maintained outside this repository.
