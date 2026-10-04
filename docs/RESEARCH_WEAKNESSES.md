# Candid research assessment and practical improvements

Reviewed 5 October 2026 against PRD v0.4, manuscript/LaTeX/PDF v0.3 and the current implementation. This is an internal assessment, not peer review. [Live evidence](evidence/live-repair-2026-10-05.json) establishes one narrow frozen-model repair; it does not establish the proposed study.

## Verdict

The idea is implementable as repair tooling. Its research contribution is still unproven. Today it translates an explicit authentication/ownership comparison into code. The broker already labels protected tools and resolves ownership; those harder integration choices are handwritten. A human can implement the same guard directly. Calling this an adaptive security system, a new RL method, or a demonstrated general repair policy would exceed the evidence.

RL should stay outside the product critical path. There is no measured training signal, independent corpus, checkpoint, costed hardware pilot or matched learning comparison. A rushed training run would consume time without fixing the central novelty and evaluation problems.

## Weaknesses that can sink the paper

| Weakness | Why it matters | Concrete improvement |
|---|---|---|
| Executable policy already contains the answer | Direct enforcement can achieve the same security and utility with less machinery | Keep the handwritten comparator; measure total specification, integration, repair and maintenance effort |
| One easy guard and one incident | A few conditionals from a full contract do not establish general repair ability | Collect distinct adapter defects and unfamiliar implementations; report each family separately |
| Original acceptance gate accepted an ID-specific bypass | Fixed synthetic IDs and one fixed incident cannot establish ownership enforcement for other users | Replaced with per-run secret-seeded fixture cases covering all nine tools, disjoint sealed identities, real singleton/effect checks and no sealed feedback; independently authored final cases are still needed |
| All archived cases are visible | Passing public development checks can reflect test fitting or model contamination | Freeze independently authored sealed cases before comparing methods; keep defect descendants together |
| Oracle and tests share implementation authorship | Isolation cannot prevent a mistaken contract from becoming a mistaken score | Record authorship, obtain independent policy review and adjudicate oracle disagreements |
| No real target-agent campaign | Direct tool misuse does not demonstrate how often an agent violates policy or responds to injection | Add bounded conversations; distinguish direct malicious requests from indirect tool-content injection |
| Authentication and consent are incomplete | Email/name/ZIP identifies synthetic users, and action archives lack confirmation turns | Keep that limitation explicit; define action-bound trusted consent and fresh conversation tests |
| Known archive contradiction | Silently discarding `test-64` would inflate utility claims | Preserve all 635 outcomes and the explicit 634-case preservation denominator; require conflict containment |
| Retention checks are enforced by selection | Passing the same gate used to select a patch is not independent evidence of retention generalization | Evaluate frozen snapshots on sealed historical-family companions without feeding scores into repair |
| One successful generation | A single first-attempt pass provides no success-rate, reliability or statistical comparison | Prespecify repeated incident trials, budgets, missing-outcome treatment and raw reporting |
| Unproven Tavily benefit | Supplying guidance is functional use, but the complete contract already specifies this repair | Compare retrieval versus no retrieval at matched budgets; retain failed and irrelevant searches |
| Code/schema isolation is narrow | Bubblewrap negative tests do not prove safety for arbitrary Python/repositories or hosted tenants | Keep the narrow guard interface; audit deployment boundaries separately before public execution |
| Runtime overhead and full cost are unmeasured | Per-call subprocesses may make a secure demonstration impractical | Measure latency and complete inference/retrieval/test/human costs before optimizing |
| RL effects could be SFT/data effects | A better trained checkpoint does not identify reinforcement learning as the cause | Shared SFT initialization, matched inference, continued-SFT/extra-compute control and training seeds |
| Protocol exceeds demonstrated scope | Proposed two-integration training/transfer design is much larger than the prototype | Keep protocol claims proposed; write an engineering report first if larger evidence is unavailable |

## Papers that matter to positioning

[CodeRL](https://arxiv.org/abs/2207.01780) is prior work on learning code generation using a functional-correctness critic and test feedback. It prevents treating execution-based learning as a new contribution by itself. [RLEF](https://arxiv.org/abs/2410.02089) trains models to use execution feedback over multiple steps; it directly motivates comparing feedback repair against independent sampling at matched budgets. Both are already in the current manuscript, references 25 and 26; they are not currently missing.

[AgentSpec](https://arxiv.org/abs/2503.18666) is a runtime-enforcement precedent. It sharpens the question of when generated source repairs justify their added complexity over direct enforcement. These sources were rechecked on 5 October. Their published results are not comparable to our current retail replay without a compatible evaluation.

## Practical next improvements

1. Keep the verified generated guard, exact-source promotion and complete replay as the runnable core. Present the two unsafe effects, actual diff, preserved legitimate task and known conflict clearly.
2. Add the bounded target-agent/tool conversation loop with clean and adversarial scenarios. Record complete model/tool traces and executed effects; use fixed spending and turn limits.
3. Collect a small honest usefulness pilot: unrepaired, independent sampling, feedback repair and handwritten direct enforcement. Count failed repairs and human contract/checker labor. Do not infer broad transfer from a single domain.
4. Obtain independent contract review and fresh final cases. Lock cases and analysis before final scoring. Report missing observations separately and conservatively.

RL becomes reasonable only after valid patches vary in success across sufficiently diverse training incidents, the protected reward is reliable, and a measured rollout/update/save/reload pilot fits a declared budget. Otherwise publish the protocol plus a reproducible frozen-model evaluation and state explicitly that RL was deferred.

## What can be claimed now

The historical live candidate passed its original fixed suite and public archive, but that gate accepted identity-specific bypasses and is insufficient security evidence. The saved candidate is unchanged; current offline verification applies randomized development/sealed panels, actual effects and full replay. This demonstrates the narrow contract-to-code workflow on finite checks, not superiority, attack robustness, generalization, research novelty or RL improvement. Richer adapter repair remains a separate experiment requiring a read-only capability design.
