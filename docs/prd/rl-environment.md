# PatchLoop RL Environment PRD

**Owner:** Mitudru Dutta. **Status:** draft for review, 5 October 2026.
**Related:** [engine PRD](engine.md), [research weaknesses](../research/weaknesses.md), [research protocol](../research/paper/PATCHLOOP_RL_Research_Manuscript.md), [platform PRD](platform.md).

## 1. Goal

Build a reinforcement-learning environment in which a model learns to write guards that pass PatchLoop's validation gates. Then measure whether RL improves guard writing over frozen models and supervised fine-tuning at matched budgets.

**Non-goals:** RL is not on the product's critical path. No claim that RL helps is made without matched controls, held-out environments and recorded costs.

## 2. Current evidence (5 October 2026)

| Fact | Source |
|---|---|
| Live adapter repair with `nvidia/nemotron-3-super-120b-a12b`: accepted on attempt 3 of 3 in one run, and on attempt 2 in each of 3 live cycles | `artifacts/adapter-live-2026-10-05-v2/`, `artifacts/cycle-*` (local, not yet exported to `docs/evidence/`) |
| Typical first-attempt failure: denying unknown orders, which the contract says must keep the tool's native error | Same runs |
| 2 of 8 live adapter candidates accepted (about 25%). Attempts used feedback and temperature 0, so this is not a pass-rate measurement. | Same runs |
| One repair attempt costs about 10,000–12,000 tokens. Full validation of one candidate takes about 50–80 seconds. | Same runs |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` is available on Nebius Token Factory | Catalog check, 5 October 2026 |
| NVIDIA's NeMo RL GRPO-LoRA example for Nano 30B-A3B uses 2 nodes × 8 GPUs, 2 prompts × 8 generations, sequence cap 2,048 | `docs/research/paper` reference [27] |

**Main limit today:** there is essentially **one task family**: τ-bench retail, with authentication, ownership and consent rules. RL needs many distinct tasks.

## 3. Environment specification

### 3.1 Episode

| Element | Definition |
|---|---|
| Task | One environment plus one incident: policy text, tool schemas, read-only data schema, incident trace, and optionally earlier diagnostics |
| Observation | The same JSON that the adapter repair prompt uses today. That prompt is now built inline in `run_repair` (`patchloop.repair.loop`). First move it into one function, then use that function for both the product and the environment, so their inputs cannot drift apart. |
| Action | One guard source: a single `def allow(context)` function |
| Reward | Binary: 1 only if every training gate passes (section 3.2), otherwise 0. Log each gate's pass fraction as diagnostics, never as weighted reward. |
| Length | One step per episode first (one patch per context). A multi-step variant with diagnostics comes later and is reported separately. |

### 3.2 Training gates (the reward)

1. **Shape:** `patchloop.sandbox.validate_source` accepts the source.
2. **Training panel:** a panel built from the **training identity pool only**, with the same case types as the development panel: cross-user, unauthenticated, authorized, unconfirmed and unknown resources, plus public tools.
3. **Incident replay:** the task's incident is blocked and its legitimate call still completes.
4. **Utility:** the guard denies no reference call of the training environment's utility suite.

The **sealed panel and the held-out environments never enter the reward.** They are for final evaluation only.

### 3.3 Reward speed

Full validation takes 50–80 seconds per candidate. GRPO needs many candidates per step, so this is too slow.

**Target: under 5 seconds per reward, measured.** Methods:
- Compute all utility guard contexts once per environment and cache them.
- Evaluate the decisions in one sandbox batch. Each context already runs in a fresh child process.
- A guard can only deny, and the tools are deterministic. So when it denies no reference call, the utility result is exact without replaying tool effects.
- Run rewards in parallel worker processes.

**Acceptance:** for every saved candidate in `artifacts/`, the fast reward must equal the full `validate_candidate` decision on the same gates.

### 3.4 Safety and reward hacking

- Candidates run only through `patchloop.sandbox`: a fresh process per decision, a read-only filesystem, no network, no secrets.
- Rewards come from the trusted process, never from candidate output.
- A new random identity panel is drawn per reward call, so memorized IDs fail (this was already demonstrated).
- Inspect accepted guards for hardcoded IDs, and add a check to the evaluation report.

## 4. Tasks and splits

| Source | Status | Use |
|---|---|---|
| τ-bench retail, current rules | Ready | Development |
| Retail variants: subsets of rules, renamed fields, removed or added tools, different consent requirements | To build | Training diversity |
| τ-bench airline (50 tasks; `send_certificate` can credit any user) | To vendor | Training or held-out |
| τ²-bench retail, airline, telecom (2,285 telecom tasks) | To vendor (different framework) | Held-out transfer |
| Agents that are not benchmarks, from the platform's generic integration | Later | Final transfer test |

**Split rule:** split by environment lineage. Variants of one environment stay in one split. Hold out whole environments for transfer.

**Target before any GPU spend (hypothesis):** at least 30 distinct task contexts across at least 3 environments.

## 5. Interfaces and layout

| Path | Content |
|---|---|
| `src/patchloop/rl/` | `RepairEnv(split, seed)` with `reset() -> observation` and `step(guard_source) -> (reward, info)`. Standard library only, so it ships in the SDK. |
| `rl/scripts/export_episodes.py` | Export every logged repair attempt as JSONL: observation, completion, reward, diagnostics |
| `rl/configs/` | NeMo RL configuration with a pinned framework commit and the full inherited configuration |
| `rl/scripts/` | Reward-parity check, pass-rate measurement, smoke run, evaluation |
| `rl/data/`, `rl/runs/` | Exported data and run outputs. Ignored by git. |

## 6. Experiments

| Condition | Purpose |
|---|---|
| Frozen Nano 30B-A3B | Starting point of the trainable model |
| Frozen Super 120B, and optionally Ultra 550B | Practical upper references through Token Factory |
| Supervised fine-tuning on accepted guards | Shared initialization and primary control |
| Iterated rejection-sampling fine-tuning at matched compute | Tests whether RL beats more imitation |
| GRPO from the fine-tuned checkpoint | The treatment |

All conditions get the same inference budget per task.

**Metrics:**
- acceptance on the first attempt, and within k attempts;
- held-out environment acceptance;
- valid-shape rate;
- share of training groups with mixed rewards;
- utility failures;
- tokens, GPU-hours and cost.

Report per environment, with the independent unit being the environment lineage.

## 7. Go/no-go gates

| Gate | Exit criterion |
|---|---|
| G0 Environment API | `reset`/`step` work. Reward parity holds on all saved candidates. |
| G1 Reward speed | Median under 5 seconds per reward |
| G2 Signal | Nano through Token Factory, at least 8 samples per task at temperature about 0.7: enough tasks have a pass rate between about 0.1 and 0.9. Mixed-group probability is symmetric around 0.5, so very easy tasks and very hard tasks both give little signal. |
| G3 Diversity | The section 4 target is met, with a frozen split manifest |
| G4 GPU smoke run | On Nebius AI Cloud with a spending cap: rollout, reward, update, save, reload, fresh generation. Finite losses and changed trainable weights are logged. |
| G5 Pilot | Section 6 comparison on held-out environments with several seeds. A negative or inconclusive result is reported as such. |

## 8. Compute and budget

The NVIDIA recipe (2 nodes × 8 GPUs) is a candidate configuration, not a measured minimum. Estimate the cost from the G4 profile before any longer run. Gates G0–G3 need no GPUs: only local compute and Token Factory inference.

## 9. Milestones

| Milestone | Target | Gates |
|---|---|---|
| M1 | October 2026 | G0, G1, episode export |
| M2 | Late October 2026 | G2 Nano signal report |
| M3 | November 2026 | G3: retail variants and airline vendored |
| M4 | December 2026 | G4 GPU smoke run, if GPU access and budget exist |
| M5 | Q1 2027 | G5 pilot and a report from the observed results |

## 10. Risks

| Risk | Response |
|---|---|
| Reward hacking through gaps in the evaluator | Fresh panels per reward, sealed final evaluation, inspection of accepted guards |
| One task family leads to overfitting | Gate G3 before GPU spend |
| Validator errors become training targets | Reward-parity tests. Independent review of the policy and the panels. |
| Feedback in prompts differs between training and product | One prompt builder for both. Report the multi-step variant separately. |
| Compute cost | Spending cap per gate. Stop if the signal is absent. |

## 11. Open questions

1. Does the first RL version train with single-step episodes only, or include feedback steps?
2. Which environment is held out first: τ-bench airline or τ²-bench telecom?
3. Can the platform's generic integration provide one non-benchmark agent for the final transfer test?
