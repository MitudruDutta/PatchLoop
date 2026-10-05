# PATCHLOOP

## Product requirements, architecture, and research protocol

**Status (updated 5 October 2026):** Native Nemotron conversations, adversarial testing, action-bound consent, a repair/retest loop, a local HTML dashboard and offline reproduction/review bundles are implemented. A live conversation and one small tester campaign completed. The original fixed-rule generated guard remains valid under the corrected gate. The richer adapter mode passes a full scripted-provider workflow, but six live candidates were rejected; none activated. The four-condition runner exists without measured live comparison results. Public hosting, AI Cloud deployment, independent final evaluation and RL remain pending. All 635 archive outcomes stay visible, including `test-64`; all 634 policy-consistent cases remain the preservation denominator. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), [current evidence](evidence/local-product-2026-10-05.json) and [research weaknesses](RESEARCH_WEAKNESSES.md).

**Prepared:** 3 October 2026, Asia/Kolkata.

**Revision:** Version 0.4, 4 October 2026. Section 0 adopts the upgraded plan: the first application is a copy of the public τ-bench retail environment instead of a toy shop with a planted defect. Sections 2, 4, 7, 8, 9, 11, and 16 follow Section 0. The product baseline remains a frozen-model repair loop. PATCHLOOP-RL is a separate, proposed training phase; it has not been implemented or measured.

**One sentence (planned product):** PATCHLOOP tests tool-using agents, finds prompt-only policy rules, generates guard patches, and records whether legitimate work still succeeds on specified tests.

**Research extension:** Train the repair model from executed patch outcomes, then test whether that learned ability transfers to unfamiliar applications while preserving legitimate behavior and earlier repairs. Detailed requirements appear in Sections 13–16 and the companion `paper/PATCHLOOP_RL_Research_Manuscript.md`. The manuscript still describes the earlier two-integration pilot; update it from real data once the MVP runs.

**Public demo hook (use only after demonstrated):** “Watch this agent act on another customer's account, inspect its generated guard, and replay both versions.”

## 0. Current plan (version 0.4)

### 0.1 Problem

τ-bench is a public benchmark from Sierra for tool-using agents (MIT license; [S29]). Its retail domain has a support agent, 16 tools, and a written policy. Its successor τ²-bench keeps the same retail tool design (MIT license, last updated 28 September 2026; [S30]). Inspection on 4 October 2026 found that the tool code enforces some policy rules and leaves others to the model:

| Enforced in tool code | Present only in the policy text |
|---|---|
| Order status (pending or delivered) | Authenticate the user before helping |
| Permitted cancellation reasons | Help one user per conversation and refuse requests about other users |
| Item existence and same product type | Obtain explicit confirmation ("yes") before any change |
| Gift-card balance; refund destination | |

The tools take `order_id` or `user_id` and have no session. For example, `cancel_pending_order(order_id, reason)` acts on any user's order, `modify_user_address(user_id, …)` changes any user's address, and `get_user_details(user_id)` returns any user's payment methods.

This is a deliberate benchmark design: τ-bench measures whether an agent obeys a written policy. It is not a τ-bench defect. Do not describe it as a τ-bench vulnerability, and do not open issues or pull requests on the Sierra repositories. Work only in this repository's copy.

The same design is common in real agents: developers write the rules in the prompt and trust the model. One persuasive customer or one prompt injection can then change another customer's account.

### 0.2 What PATCHLOOP does

1. **Test.** An automated adversarial tester, a Nemotron model acting as a dishonest customer, talks to the target agent in a sandboxed copy. Its goals are to act on another user's order or address, to read another user's private data, and to make a change without explicit confirmation.
2. **Record.** A trusted dispatcher records every tool call, the session, and every data change. Neither model can alter it. The session's authenticated user comes from the result of `find_user_id_by_email` or `find_user_id_by_name_zip`, never from model arguments.
3. **Detect.** The protected evaluator flags four violation types: action on another user's data, disclosure of another user's private data, change without explicit confirmation, and action before authentication.
4. **Reproduce.** Replay the violating tool call from a clean database.
5. **Repair.** The repair worker sends the policy, the tool code, and the failure to Nemotron, which writes a guard patch.
6. **Validate in the sandbox.** Check the original violation, historical regressions, and authorized utility cases. The archive contains 1,375 scheduled calls across 635 tasks; `test-64` has conflicting task/login identities. Preserve and report that conflict rather than treating every reference as policy-correct. Compare outputs as well as final database state. Freeze a reviewed utility-case manifest before generated-repair acceptance; keep all original task outcomes visible. The model gets at most three attempts.
7. **Promote.** Keep a passing patch as a new version; otherwise keep the old version.
8. **Publish.** Open a pull request in this project's own repository with the patch, the new tests, and an evidence report.
9. **Test again.** The adversarial tester runs against the new version. The dashboard shows before and after.

Confirmation must be tied to a particular action and its arguments in trusted user turns; a model-supplied `yes` is insufficient. Conversation-bound confirmation also exists in non-agent systems and is not itself a novelty claim. Reference action lists omit confirmation turns, so they cannot validate this rule. Ship authentication and ownership first.

**Fixed-rule comparison:** this condition translates an explicit contract into code. The trusted broker supplies tool protection labels and resolved owner IDs, and the model prompt specifies the comparison. Keep it for measuring translation/replay cost; it does not demonstrate discovery of the tool-to-resource mapping. The original fixed-ID gate was vulnerable to memorization and has been replaced by per-run secret-seeded real-fixture identity checks.

**Implemented adapter experiment:** the model receives policy text, tool schemas, incident evidence and selected read-only synthetic rows. Candidate code chooses tool protection and resource relationships; identity, consent metadata, data immutability, effects and promotion remain trusted. Computed ownership labels, evaluator files, secret seeds and sealed cases are excluded. A full scripted-provider workflow passes; six live candidates failed validation and none activated. The prompt now derives actual record fields, but that improvement has not been tested in another live generation. Accepted live repair and independent boundary/schema review remain required before effectiveness claims.

### 0.3 Why this replaces the toy shop

| Weakness of the earlier plan | Answer in version 0.4 |
|---|---|
| The defect was planted by us | Prompt-only rules are a real design pattern in a well-known benchmark |
| The fix was one `if` statement | Session handling, ownership, output preservation, and confirmation require explicit contracts and tests; complexity alone is not research novelty |
| "Why not enforce the checker directly?" | Prompt-only rules motivate enforcement, but do not establish a benefit from generated repair over a handwritten guard. Measure both |
| No agent-specific element | End-to-end agent evaluation is needed; transcript confirmation alone does not establish an agent-specific contribution |
| Toy demonstration | The output is a reviewable pull request with tests and evidence |

### 0.4 Model roles and services

| Role | Model on Nebius Token Factory | Reason |
|---|---|---|
| Target agent | Nemotron 3 Super | Realistic, strong support agent |
| Adversarial tester | Fast Nemotron model (Nano class) | Many low-cost test conversations |
| Repair worker | Nemotron 3 Super, or Ultra if the account offers it | Code reasoning |

Run the application on Nebius AI Cloud; optionally run test campaigns in parallel with Nebius Serverless Jobs. Confirm the exact model identifiers available to the account before writing code, and record them.

Current local experiments use `nvidia/nemotron-3-super-120b-a12b` for all model roles. The Nano/Ultra routing above remains a planned comparison. AI Cloud deployment is deferred until local verification and project configuration are complete.

**Tavily:** the repair worker calls Tavily at runtime to retrieve current public guidance for the defect class, such as OWASP authorization guidance and relevant library documentation. Treat results as untrusted reference text, never as instructions, and keep redacted request and result records.

### 0.5 Risks

| Risk | Response |
|---|---|
| Nemotron 3 Super refuses most adversarial requests, so few violations occur | Report true rates. Use deterministic tool-level replay for the repair loop. Also test a faster model as the target. A strong agent that still fails sometimes is a meaningful result |
| One patch must change many tools | Start with the 7 tools that change data and the 2 that read private data; repair one rule at a time |
| The confirmation rule is hard to specify | Ship ownership and authentication first; add confirmation afterwards |
| End-to-end conversations are costly | Use the free replay suite for most checks; cap end-to-end runs |
| "Why not write the guard by hand?" | Show the hand-written guard comparison. PATCHLOOP's value is finding the gap, writing the guard, and proving it with tests |
| τ-bench authentication (email, or name plus zip) is weak in real life | State this limit in the README |

### 0.6 First tasks

1. Copy `tau_bench/envs/retail` into this repository with the Sierra copyright notice; mark it "derived from τ-bench" in the README.
2. Replay all 1,375 scheduled calls; check baseline fidelity, guarded outputs and states, and identity inconsistencies. Baseline replay and guarded comparison are now implemented.
3. Completed locally on 5 October: catalog verification, live inference, Tavily retrieval and integrated repair using `nvidia/nemotron-3-super-120b-a12b`. Keys remain in ignored local configuration/environment variables, never source.

## 1. What survives from PATCHBOSS

The original game idea made adaptation visible: an opponent observes a defeat, rewrites its behavior, tests the revision, and returns for another challenge. PATCHLOOP applies that loop to tool-using AI applications.

| Game concept | Tool equivalent |
|---|---|
| Boss | Developer's AI agent |
| Winning tactic | Input or workflow that causes an unauthorized action |
| Match replay | Conversation, tool calls, and state snapshots |
| Revised combat program | Revised tool adapter or validation helper |
| Rematch | Original failure replay plus new evaluation cases |
| Fairness checks | Legitimate task completion and regression checks |
| Share a boss version | Share a reproducible before/after experiment |

This project is developer infrastructure with a public, interactive demonstration. Its attraction comes from observing an actual failure become a tested source-code change. Revenue is secondary to a credible demonstration and useful open-source tool.

## 2. First application: the τ-bench retail agent

Use this repository's copy of the τ-bench retail environment: synthetic users, orders, products, and payment methods, with 16 registered tools and a written policy (Section 0.1). No real payments or customer accounts are connected.

The policy text is the owner's contract. Its rules (authenticate first, help one user per conversation, confirm before changes, plus the rules the tools already enforce) are application requirements. The repair worker may not invent or relax them.

No defect is planted. The baseline is the unmodified τ-bench tool code, labelled as such. The adversarial tester or a visitor produces a conversation in which the agent acts on another user's data or changes data without confirmation.

PATCHLOOP then follows Section 0.2: capture the conversation, session, and state change; evaluate them with the protected checker; reproduce the violating call from a reset database; build a regression case; ask the coding model for a guard; run the violation test, the 1,375-call replay suite, and earlier regressions; promote or retain; and show both versions on the same input.

The decisive final scene is a legitimate return or cancellation succeeding for the authenticated user after the cross-user action is blocked. A patch that blocks all changes fails the 1,375-call replay suite and therefore fails the demonstration.

### An important distinction

The model may still propose an unauthorized tool call after the patch. The repaired adapter can reject that call before it changes state. Report these as separate outcomes: **unsafe action attempted** and **unsafe action executed**. Containment does not establish that the language model has become resistant to manipulation.

## 3. Who uses the actual tool

Initial users are independent developers and researchers building Python agents with explicit tool functions. The hosted τ-bench retail copy is one example application; the reusable deliverable is a Python package, CLI, and report viewer.

A developer supplies:

- An agent entry point and registered tool dispatcher.
- Disposable fixtures plus reset and snapshot functions.
- A trusted policy checker over actions and environment state.
- A legitimate task suite with concrete expected outcomes.
- Source paths the repair process is permitted to edit.

Integration requires access to tool execution and editable source. A remote chat endpoint alone can support limited testing, but it cannot support verified source-code repair. Do not market universal, one-line integration.

The local workflow runs an evaluation against a developer-owned test environment, attempts repair, and produces a patch file, tests, and report. The developer reviews and applies the patch through their normal workflow. Automatic activation is limited to the isolated demonstration environment.

### Proposed integration contract

These are planned interfaces, not an existing installable API.

| Interface | Responsibility |
|---|---|
| run_agent(request, dispatcher) | Run a task through the instrumented tool boundary |
| reset(fixture_id) | Restore a deterministic starting environment |
| snapshot() | Return application state needed by evaluators |
| evaluate_transition(before, action, after, trusted_context) | Detect a policy violation mechanically |
| evaluate_task(final_state, expected) | Determine whether the legitimate objective succeeded |
| editable_paths | Limit repair to specific adapters and helpers |

Authenticated identity, balances, ownership, and approval state come from trusted application state. Arguments generated by the model are not evidence of authorization.

## 4. MVP requirements

| Priority | Requirement | Acceptance condition |
|---|---|---|
| P0 | τ-bench retail fixture | Real Nemotron calls and real synthetic database transitions are visible; the Sierra MIT notice is kept |
| P0 | Session-aware dispatcher | The authenticated user comes from trusted tool results, never from model arguments |
| P0 | Replay suite | Baseline preserves upstream state; candidate preserves outputs and state for reviewed authorized cases; report all 635 original outcomes and the `test-64` identity conflict |
| P0 | Adversarial tester | A Nemotron tester runs against a sandboxed copy and its violations are recorded |
| P0 | Trace recorder | Every tool attempt includes version, arguments, result, and state references |
| P0 | Protected evaluators | The repair process cannot alter policies, expected outcomes, or evaluation infrastructure |
| P0 | Failure reproduction | Report deterministic action replay separately from stochastic end-to-end replay |
| P0 | Candidate repair | Produces an inspectable source diff confined to allowlisted paths |
| P0 | Validation | Original exploit, prior regressions, and development utility cases all run |
| P0 | Honest failure state | Failed or timed-out repair is shown; no fabricated success animation |
| P0 | Version comparison | A visitor can compare baseline and candidate from identical fixtures |
| P0 | Pull request output | Each accepted repair opens a pull request in this project's repository with patch, tests, and evidence |
| P0 | Export | Experiment bundle contains enough information to replay deterministic checks |
| P1 | AgentDojo adapter | Compatible tasks retain original benchmark semantics and evaluators |
| P1 | External projects | Several developers integrate their own test agents and report friction |
| P1 | Further domains | Add the τ-bench airline domain (same authors, so not an independent implementation) and one separately authored integration |
| P1 | Tavily guidance | The repair worker retrieves current public guidance at runtime and records requests and results |
| R0 | Training episode export | Training contexts, candidate patches, protected scores, and failures can be reproduced without final-test leakage |
| R1 | Bounded RL pilot | Actual training updates and checkpoint hashes exist, with valid-candidate and reward-variation diagnostics |
| R1 | Controlled learning comparison | Frozen, supervised, and RL repairers are compared using the same base checkpoint and inference limits |
| R1 | Transfer and retention evaluation | Held-out implementations and sealed historical-family cases are scored after methods are frozen |

R0 and R1 are research milestones, not MVP gates. A working demo does not depend on completing model training.

The initial release excludes arbitrary hosted repository execution, automatic production deployment, general website scanning, operating-system repair, concurrency claims, and unrestricted agent frameworks. MVP state-changing tool calls are serialized; race-condition and transactional correctness require a separate evaluation.

## 5. Architecture

The current local prototype uses one standard-library Python HTTP service, HTML/CSS/JavaScript, bounded native provider calls and per-run files. It has no relational database or distributed queue yet. Each conversation owns a fresh fixture and immutable initial guard; one background challenge runs at a time. These local limits do not provide public tenant authentication/isolation. The architecture below remains the planned hosted design.

Use one API service, one repair worker, a small relational database, and per-run artifact directories. Keep the SDK independent of the dashboard. Add distributed queues or more orchestration only when the workload requires them.

~~~mermaid
flowchart TD
    A["Agent and registered tools"] --> B["Trace and state recorder"]
    B --> C["Protected policy evaluator"]
    C -->|"Reproduced violation"| D["Repair worker"]
    D --> E["Nemotron on Token Factory"]
    E --> F["Candidate tool adapter"]
    F --> G["Isolated replay and validation"]
    G -->|"Diagnostic feedback"| D
    G -->|"Accepted"| H["Versioned patch and report"]
    H --> I["Sandbox replay or developer review"]
~~~

### Runtime path

All registered tool invocations pass through one instrumented dispatcher. It captures the action and invokes the current adapter. The environment records whether state actually changed.

The research evaluator observes transitions and assigns labels. It must not silently prevent the baseline failure being measured. Public demonstration tools act only on disposable synthetic state.

In a developer's deployment, established backend authorization remains authoritative. PATCHLOOP does not replace existing controls or require removing them to collect failures. Developers can feed it historical failures, fault-injected fixtures, and pre-release test runs.

### Repair path

The worker receives a bounded bundle: relevant source, the owner-authored contract, the reproduced trace, tool schemas, and prior development regressions. It asks the coding model for a small patch and tests the candidate.

Candidate code executes inside a disposable container with resource limits, restricted filesystem access, and no application secrets. The sandbox cannot access the container host, alter evaluator files, install new dependencies, or call live business services. The orchestration service owns model credentials and provides only explicit model access where required.

Reject diffs outside the approved paths, modifications to test discovery, fixture tampering, swallowed errors that falsely report success, and changes that bypass recording. Treat attacker-authored text in traces and source comments as untrusted data.

These controls also protect the repair agent from being redirected by the very attack it is analyzing.

### Model roles

Use NVIDIA Nemotron 3 Super through Nebius Token Factory for diagnosis and candidate code generation. Its documented coding and tool-use capabilities make it a candidate, not a guarantee of performance [S1].

Start with one model and one repair loop. A smaller Nemotron model can later handle trace summaries if an ablation shows that the summaries preserve repair quality and lower cost. Benchmark that change before making it the default.

Token Factory runs model inference. Nebius AI Cloud runs the application, worker, and code execution environments. Record the actual account model identifier, model revision if exposed, region, decoding configuration, and request metadata. Do not invent an Ultra dependency or assume zero retention is enabled by default.

## 6. Repair algorithm

For each confirmed incident:

1. Pin the parent source version, fixture, application contract, and test versions.
2. Replay the exact tool action against the parent adapter.
   If replay is incomplete, record an indeterminate outcome. If a previously validated incident is already contained by this parent, run the mandatory development checks, record the already-contained status if they pass, and skip generation. Do not confuse these outcomes with a newly generated repair.
3. Replay the full conversation separately and record variation in the agent's decisions.
4. Construct a regression case from observed state and the protected oracle.
5. Generate a candidate within a maximum of three model-generation attempts.
6. Run syntax checks, protected-path checks, the triggering regression, earlier regressions, and the development utility suite.
7. Return diagnostics from development tests for revision within the same budget.
8. Accept a candidate only if the required development gates pass. Otherwise retain the parent version.
9. Freeze the candidate before final held-out evaluation.

Serialize promotion per application and use a compare-and-swap against the expected parent version. Activate the exact tested artifact with pinned dependencies and evaluator/policy versions. Revalidate a stale candidate instead of replacing a newer repair. Pin demo sessions to immutable versions. A policy or dependency change requires revalidation and limits any previous retention claim.

A development pass means “candidate accepted for evaluation,” not “secure.” The final test set never becomes repair feedback.

Keep the target agent's base model fixed during an experiment. In the product baseline, the evolving artifact is adapter code and the repair model is also fixed. The RL extension trains the repair model offline on a separate training partition, freezes the resulting checkpoint, and then evaluates it on new applications. Sequential code repair and continual weight training are different claims; the initial research phase does not include public-session weight updates.

### State and artifacts

Store Project, Run, Incident, Candidate, Evaluation, and Version records. Each incident references its parent version, fixture, policy IDs, and trace. Each candidate records its diff, protected-file check, generation budget, test results, and promotion decision.

For research, add TrainingRun, RepairEpisode, and ModelCheckpoint records. An episode binds its training split, rollout-policy checkpoint, group identifier, patch, reward components, token accounting, and evaluator versions. Final evaluation outcomes never enter the training episode store. Retain failed incidents in an unresolved registry; do not label them as repaired historical cases.

Use source and artifact hashes to tie the displayed result to the tested code. Hashes establish artifact identity; they do not establish that an artifact is correct.

## 7. Public demonstration

The three views and two actions below now exist locally. Browser checks exercise conversation, explicit consent, actual record changes, a challenge, evidence download and a mobile viewport using a scripted provider. Live backend smoke checks are separate. Public access and hosting are not verified.

The dashboard has three linked views:

- **Interaction:** user request, agent response, and tool call.
- **Consequence:** the affected users and orders before and after.
- **Repair:** actual diff, actual test results, and version comparison.

A useful short video shows a cross-user change, generation of a guard, the same attempt being blocked, and a legitimate return still completing. Display elapsed repair time; label any accelerated footage.

A visitor can reset a fixture, attempt a failure, inspect an existing repair, and replay a version. Cap submissions and model usage per session. Public visitors may only interact with the provided sandbox, not submit arbitrary URLs or repositories for execution.

Display two clear actions: “Challenge this version” and “Reproduce locally.” A report URL includes the tested version and downloadable evidence rather than a generic security score.

For a concise product walkthrough: show the policy and baseline effect, generated guard and actual replay results, repeated testing and a legitimate task, then measured usage and limits. Show failed attempts and reference conflicts. Do not script “every attempt blocked” before observing that result. Label the current offline handwritten comparison distinctly from the planned generated-repair demo.

## 8. Research question and proposed contribution

**Product-baseline working title:** “From Prompt-Only Policies to Tested Guards: Failure-Guided Repair of Tool-Using Agents.”

**Manuscript title:** “PATCHLOOP: A Protocol for Evaluating Agent Tool-Adapter Repair.” The companion manuscript is a proposed method and experimental protocol, not a completed results paper.

**Primary question:** Under equal repair budgets, does feedback-driven code repair from observed failures reduce unauthorized state changes on unseen test conversations while preserving legitimate task success, compared with independent sampling, direct enforcement, and a hand-written guard?

**RL extension question:** Does SFT followed by execution-reward RL improve held-out repair over the exact SFT checkpoint under matched inference budgets while preserving clean utility? Frozen prompting is a secondary comparator. Separately test whether a direct guard using the existing policy checker solves the problem without repair. Report all collection, training, and validation costs.

**Secondary questions:**

- Does each new repair preserve earlier fixes?
- Do repairs generalize across identities, application states, tool schemas, and attack families?
- How much do immutable policy oracles and regression memory contribute?
- How vulnerable is the repair process to poisoned incident content?
- How much integration work is needed from a developer?

Potential contributions are a method, a sequential evaluation protocol, an auditable corpus of failure/patch/test episodes, and evidence about conditions where the method helps or fails. Novelty and publication acceptance are not established by this proposal.

### Prior work we must acknowledge

| Work | Relevant overlap | Implication |
|---|---|---|
| PATCHAGENT [S2] | Fault localization, patch generation, and validation | General autonomous repair is established work |
| AgentSpec [S3] | Runtime policies and LLM-generated rules | Generating agent guard rules is not itself novel |
| ClawGuard [S4] | Enforcement at tool-call boundaries | Boundary enforcement cannot be our sole novelty claim |
| PromptArmor plugin [S5] | Code-aware testing and patch proposals | There are close public developer tools |
| AgentProof [S6] | Behavioral tests and structural auto-repair | Compare concrete implementations before claiming a unique product workflow |
| AgentDojo [S7] | Agent attack/defense evaluation and task environments | Reuse established evaluation structure |
| InjecAgent [S8] | Indirect injection cases in tool-integrated agents | Possible supplemental evaluation, subject to compatible semantics |
| AttriGuard [S9] | Counterfactual checks of tool-call necessity | Include strong defenses when answering broad defense-performance questions |
| Security repair with RL [S10] | RL-based security-oriented code repair | Adding security rewards to repair is established territory |
| SWE-RL and Self-play SWE-RL [S11, S12] | Learning software repair, including bug injection and repair | Do not claim novelty for “learning by breaking and fixing code” |
| PISmith [S13] | RL-based adaptive prompt-injection testing | An RL attacker alone is not the contribution |
| RETA [S14] | RL-based task-aligned agent defense | Security–utility optimization has close precedent |
| Self-Evolving Defense [S15] | Training-free policies from harmful trajectories | Include a relevant alternative to weight training where compatible |

This is an initial related-work review, not an exhaustive novelty assessment. Repository descriptions are capability claims by maintainers, not independent performance evidence. Do not compare their published numbers with ours across different tasks or budgets.

### The obvious reviewer objection

“Why not write the authorization checks correctly once?”

For a small fixed application, that may be the best solution. Include a manually implemented reference guard and a one-shot repair given the full contract. PATCHLOOP needs to earn its complexity by reducing repair effort or maintaining correctness as adapters and workflows change. If it cannot, report that result and narrow the product claim.

## 9. Experimental design

### Separate the pilot from the paper

The first pilot tests whether the complete loop works on the declared fixtures. Its findings remain local to those integrations.

Start with the τ-bench retail copy in Section 0. Expand only after measured costs and variance justify a larger study; domain count alone is insufficient for a transfer claim.

### Evaluation tracks

**Track A: deterministic tool-adapter repair.** Replay identical action sequences and state against each candidate. This isolates whether the patch changes enforcement correctly.

**Track B: end-to-end agent behavior.** Run the same user goals, initial fixtures, and adversarial observations through the agent for repeated trials. This measures task completion, unsafe intentions, and executed effects.

Report both. Good results on fixed tool calls do not automatically imply robust end-to-end behavior.

**Deferred Track C: external integration.** Ask independent developers to integrate the SDK into their own authorized test agents. Record time, code changes, required oracle authoring, unsupported cases, and failures. This is usability evidence, not a security benchmark.

### Comparators

The first pilot has four main conditions:

1. Unrepaired application, establishing baseline faults and utility.
2. Frozen independent-sampling repair using the initial incident and full contract.
3. Frozen feedback repair using the same initial information plus permitted intermediate diagnostics.
4. Direct policy enforcement at the trusted broker using the same policy and authoritative state.

A manually implemented reference guard tests fixture solvability; record its human effort separately. Apply the common repair resource ceilings and candidate-selection rule in Section 16. Prompt-only defenses and established runtime systems belong to later compatible comparisons; this pilot cannot support superiority claims over untested defenses.

Historical-memory and utility-gate ablations are deferred to the larger study. Any gate-removal ablation remains inside the isolated test harness.

### Data separation

For the frozen-model product pilot, distinguish repair feedback, development selection, and sealed outcomes. For the RL study, explicitly separate four logical pools:

- **Training:** incidents, patch contexts, and execution cases that supply optimizer rewards.
- **Development validation:** model and method selection; separate from optimizer training cases.
- **Final incident inputs:** held-out failures that evaluation-time repair is permitted to observe, plus declared development diagnostics for that application.
- **Sealed final outcomes:** unseen variants, clean tasks, and historical-family companion cases used only to score frozen snapshots.

Showing the evaluation-time repairer its assigned incident is necessary; feeding its sealed outcome scores back into repair or training is leakage. Keep implementation lineages and mutations of the same source fault in one partition.

Split by attack family and underlying scenario, not only by paraphrasing the same prompt. Keep new application schemas and state configurations for transfer tests. State explicitly that public benchmark items may already be in a model's training data; release fresh evaluation items after measurement and report that limitation.

For sequential experiments, reveal one failure at a time. Evaluate frozen snapshots offline without returning final-test scores to the ongoing repair loop. Retain earlier attack families to measure reintroduced vulnerabilities.

Report pass rates on the same fixed panel of sealed companions from earlier failure families. Conditional forgetting rates have different method-specific denominators and are supplementary. Passing the exact historical suite enforced by an acceptance gate is expected by construction and cannot establish learned retention. Separate training-reward memory, model-context memory, and acceptance-gate memory in ablations.

After final evaluation, publish the test material, generated patches, failed candidates, and all scoring code.

### Metrics

| Metric | Definition |
|---|---|
| Executed violation rate | Fraction of attack episodes containing an unauthorized state transition |
| Unsafe proposal rate | Fraction containing a proposed unauthorized tool call, whether executed or blocked |
| Clean task success | Correct completion on legitimate tasks without attack content |
| Task success under attack | Legitimate objective completed with no policy violation despite adversarial content |
| Original-case repair | Whether the triggering deterministic counterexample is contained |
| Held-out generalization | Executed violation rate on unseen families and states |
| Repair regression | Previously contained failures reappearing after later patches |
| Incorrect blocking | Authorized actions rejected by the candidate |
| Repair efficiency | Calls, tokens, elapsed time, and billed cost per scheduled incident, including failed attempts |
| Runtime overhead | Added latency during normal agent/tool execution |

Count failures and timeouts explicitly. Do not silently remove difficult episodes. Report denominators and per-domain results. A refusal of every request can lower violations while destroying utility; it cannot count as overall success.

Incomplete observations are not certified-safe episodes. Report execution coverage and a worst-case bound treating unobserved attack outcomes as violations. Candidate-induced crashes count as repair failures; infrastructure retries follow a fixed policy. An observed violation remains a violation even if execution later crashes.

Use paired cases and repeated model runs. Report uncertainty with confidence intervals and cluster by the highest independent unit relevant to the claim, normally implementation lineage, while preserving nested scenarios and repeated runs. Predeclare the utility non-inferiority margin before final evaluation and justify it from tolerable operational harm, not from budget.

### Pilot scale and costs

Use the τ-bench retail pilot specified in Sections 0 and 16. Record a fixed short incident stream per implementation and separately authored clean and sealed companion cases. Choose actual case counts after measuring run cost; publish the counts before final scoring. The earlier 3,600-episode planning example is retired because it was neither a calibrated sample size nor the lean first experiment.

Report outcomes, actual model usage, candidate and test counts, retries, wall time, integration effort, and oracle-authoring effort. Budget-matched repair conditions share resource ceilings and starting information; intermediate diagnostics are the feedback treatment. One benchmark implementation supports local findings only.

The paper's precision appendix illustrates why a two-point utility margin can require thousands of independent episodes under particular assumptions. These are planning calculations, not required pilot counts. Select margins from acceptable operational harm and calibrate the larger design before making utility-preservation or population-transfer claims.

## 10. What “proof” means

The initial public deliverable is reproducible empirical evidence:

- A specified failure occurs in version A.
- Version B contains a particular generated change.
- Protected checks produce documented outcomes on named cases.
- Unseen cases and legitimate tasks are evaluated separately.
- Others can inspect the artifacts and rerun deterministic tests.

A replay of recorded model outputs reproduces the historical execution. Fresh model calls estimate whether the behavior recurs; they are not guaranteed to yield identical text or actions.

This evidence does not prove the absence of future failures. Formal verification would require an explicitly modeled program, trusted assumptions, and a stated class of invariants. It can be a later bounded extension, but should not be advertised as completed or as proving the entire LLM application secure.

### Release bundle

Include source and version hashes, dependency locks, fixtures, contract and evaluator versions, exact model configurations, prompts, traces, generated diffs, deterministic replay cases, development/final split manifests, raw evaluation outcomes, aggregation scripts, and a limitations statement. Public data should be synthetic or released with permission; omit secrets and private customer content.

## 11. Build sequence

Use dependency gates rather than treating an estimated day count as evidence of feasibility. RL remains outside the MVP critical path.

| Gate | Required artifact | Proceed when |
|---|---|---|
| G0: trusted execution | τ-bench retail copy, session-aware dispatcher, evaluator, 1,375-call replay suite, reference guard, tampering suite | All replay calls pass on the baseline; a hand-made cross-user call is detected; every named negative case is rejected, detected, or correctly marked indeterminate |
| G1: frozen repair | Real Nemotron guard patch, complete trace, tested-version promotion, pull request | Original violation is contained, all 635 archive outcomes are recorded, all 634 policy-consistent preservation cases pass, the explicit conflict remains contained, and history checks pass on the exact activated artifact. Local generation/validation/promotion work; PR output is pending |
| G2: usefulness pilot | Four-condition results on τ-bench retail, adversarial-tester campaign, effort/cost ledger | Measured repair value justifies the complexity in the stated setting; otherwise narrow the claim |
| G3: public demonstration | Resettable sessions, version viewer, reproduction bundle | An independent person reproduces a documented result |
| G4: optional RL feasibility | Pinned smoke run, reward diagnostics, steady-state profile, serving check | Data and signal are adequate and measured costs fit the declared spending cap |
| G5: larger research study | Locked split, calibrated design, controls, seeds | Final evaluation can answer the declared question with adequate independent units |

Failure at G2 can still leave useful repair and evaluation tooling. Failure at G4 keeps RL as future work. A successful smoke run demonstrates execution, not effectiveness.

MVP schedule (G0–G3 only):

| Week | Work | Result at the end of the week |
|---|---|---|
| 1 (4–10 Oct) | Copy the τ-bench retail environment with its MIT notice; session-aware dispatcher; evaluator; replay suite; one Token Factory test call | G0 passes |
| 2 (11–17 Oct) | Target agent and adversarial tester on Nemotron; repair worker, sandbox, test gates; Tavily guidance retrieval | G1 passes |
| 3 (18–24 Oct) | Pull request output; dashboard; deployment on Nebius AI Cloud; tester campaign; hand-written guard comparison | G2 results and a public demo exist |
| 4 (25–29 Oct) | README and demo video; one outside person installs from the README | Release candidate ready (G3) |

If time runs short, defer RL, the airline domain, additional dashboard polish, and optional Tavily integration. Retain direct-enforcement measurements for any claimed repair benefit. Never cut the working repair loop, validated replay cases, setup instructions, license notices, or submission video.

## 12. Release package

Provide the working demo, the public repository with an open-source license, setup instructions, a short demo video, and a record of the Nebius and NVIDIA services actually used. Separate original project code from benchmark and dependency licenses.

The README should identify where NVIDIA Nemotron performs repair, where Nebius Token Factory serves inference, and where code tests run. Include exact reproduction commands once implemented. Keep demo results tied to the released commit.

For the paper, write the introduction, method, protocol, and limitations before collecting final data. Write results and conclusions only from completed experiments. Publish a technical report if findings are useful; venue acceptance remains a separate review process.

## 13. PATCHLOOP-RL requirements and architecture

### What is learned

Train the repair policy to generate better adapter patches. Keep the target assistant fixed. The product's source-code adaptation loop remains available as both the MVP and the principal frozen-model baseline. Do not call prompt feedback, patch ranking, or regression storage weight training.

The initial learning formulation samples one patch per incident context and uses executed outcome rewards. Previous diagnostics may be fixed context. At the patch level this is a contextual reward problem; it does not yet solve long-horizon interactive credit assignment. Multi-attempt repair is evaluated with a frozen checkpoint and a maximum of three attempts per incident.

### Proposed optimizer and reward

Use GRPO as an existing optimizer, with LoRA if a training-compatible Nemotron configuration passes the resource pilot [S16–S18]. For each context, sample a group of candidates, evaluate them, and compute group-relative advantages. Mask prompts and tool outputs out of the policy-gradient loss. Log groups with identical rewards; they provide no reward advantage. Do not hide invalid patches or reward sparsity. All optimizer rewards come only from training cases; development-validation and final outcomes cannot supply these rewards.

Use a binary training reward: R = 1 only when the candidate respects the source boundary, completes trusted evaluation, and passes every mandatory training security, utility, and retained regression case; otherwise R = 0. Log component pass fractions separately. Infrastructure outages follow a bounded retry policy and never supply positive rewards without completed evaluation.

The previous combined reward with a 0.1 token-cost term is withdrawn. In a group with equal correctness, normalization can cancel that coefficient and make token cost the only policy-gradient signal. A small raw coefficient does not establish a small learning effect. Cost is therefore an evaluation metric and an explicit budget constraint, not part of the primary reward. GRPO normalization choices require scrutiny [S19, S20].

Binary rewards can be too sparse to train. Measure mixed-outcome groups and valid candidates in a bounded pilot. If useful signal is absent, improve training-only data, use a matched SFT initialization, or stop the RL branch. Do not claim that an optimizer call establishes useful learning. Constant-reward groups may still produce a KL update; when the current policy equals its reference, the exact KL gradient is zero. Do not equate a present KL term with a guaranteed weight change.

Acceptance is a separate hard gate. Rejection retains the parent and records an unresolved incident. An incident already contained by a previous patch is validated and recorded without an unnecessary generation call. An incomplete replay is indeterminate, not an already-contained success. Track these statuses separately.

### Two execution paths

~~~mermaid
flowchart TD
    A["Training applications and incidents"] --> B["Repair-policy rollouts"]
    B --> C["Isolated candidate execution"]
    C --> D["Protected outcome rewards"]
    D --> E["GRPO update on AI Cloud"]
    E --> B
    E --> F["Development checkpoint selection"]
    F --> G["Frozen repair checkpoint"]
    G --> H["Held-out application repair"]
    H --> I["Hard acceptance gate"]
    I --> J["Frozen code snapshots"]
    J --> K["Sealed outcome evaluation"]
~~~

The sealed evaluator has no feedback connection to training, checkpoint selection, or ongoing repair. Model weight updates run on Nebius AI Cloud with explicit training infrastructure; Token Factory inference calls do not update the model. Training should not occur inside a visitor's demo request.

### Runtime trust and instrumentation

An allowlisted Python source file can still perform arbitrary side effects. Run candidate code in a separate restricted process or stronger isolation, with no shared evaluator interpreter, host mounts, credentials, package installation, or unrestricted network access. Bind fixture and identity capabilities outside candidate arguments. Require tampering tests before any hosted demonstration.

An out-of-process broker owns authoritative simulated state and mutation logs. The evaluator reads that state rather than candidate-reported success messages. Generated adapters cannot alter trusted identity, expected outcomes, the broker, or the runner. Evaluate test-harness tampering as a failure. Pin test semantics, dependencies, and fixture state. A container alone is not proof of isolation.

The retail simulator must also support an explicitly labeled direct-enforcement mode: the broker evaluates tentative transitions and commits only allowed ones. Compare its cost and utility with repair. Observation mode records synthetic effects without policy prevention, including prompt-only policy violations in the unchanged benchmark. Fault injection is an additional, separately labelled setting. Do not confuse these configurations.

The owner supplies complete policy context for all baselines. A manually written reference guard and a one-shot full-contract repair remain essential comparators. If these solve the problem more simply, report that finding and narrow the adaptive-product claim.

### Compute and go/no-go gates

1. Produce real baseline failures and legitimate successes with reliable observation.
2. Collect actual candidate patches and check that rewards vary meaningfully.
3. Profile one rollout-and-update run on the selected checkpoint and hardware.
4. Freeze pilot settings, including group size, token budget, optimizer, LoRA configuration, and resource ceiling.
5. Compare frozen repair, successful-example SFT, and RL under common inference limits.
6. Continue to a larger study only if the pilot supports feasibility. A negative pilot is reportable.

No GPU count, training duration, credit expenditure, or accuracy gain is promised. Existing NeMo RL support is not evidence that the chosen run has succeeded. Keep research training off the MVP critical path.

## 14. Research manuscript and evidence standard

The companion manuscript contains an abstract, related work, threat model, mathematical formulation, specification pseudocode, a controlled experimental protocol, statistical decision rules, limitations, reference audit, architecture figure, worked example, and a short statement of finite-testing limits. It contains no fabricated experiments, dataset sizes presented as collected data, plots, checkpoints, user studies, performance numbers, or publication claims.

The primary learning comparison is SFT-plus-RL versus the identical SFT checkpoint. It requires improvement in a prespecified security-failure-or-incomplete-execution endpoint and a non-inferiority test for clean utility. Observed executed violations are reported separately; fewer missing observations alone cannot establish fewer violations. Fix the utility margin, sample-size justification, confidence procedure, independent sampling unit, training seeds, exclusions, and stopping rules before final evaluation. Compare against SFT so the contribution is not merely access to successful examples. Include complete collection and training costs as well as per-repair inference cost.

Use the same SFT checkpoint as the starting point for both main learning conditions, and disclose the common data. Add continued SFT or rejection-sampling fine-tuning as an extra-compute control. For the primary security contrast, incomplete security observations are conservatively counted as failures; separately report observed violations and completion coverage. This prevents missing execution from creating an apparent gain.

The finite-suite retention argument assumes deterministic replay, immutable requirements, complete checks, trusted observations, pinned environments, and activation of the exact tested artifact. It does not prove universal security or any empirical RL gain. Evaluate unseen historical-family cases to test generalization beyond gate-enforced memory.

The paper can become an empirical submission only after released code, real training logs, checkpoints, raw outcomes, aggregation scripts, and independent reproduction exist. Until then, label it a proposed-method and experimental-protocol manuscript. Refresh the novelty review before submission and report negative or inconclusive results without changing the hypotheses after seeing final data.

## 15. Critical audit: issues corrected and remaining blockers

| Finding | Severity | Required disposition |
|---|---|---|
| The existing oracle may already solve authorization | Critical to product/research value | Implement the direct-enforcement baseline before investing in RL |
| Raw reward weights do not control normalized advantage weights | High | Withdraw token-cost shaping; use a binary primary reward and report cost separately |
| SFT warm-start gains can be mistaken for RL gains | High | Make matched SFT versus SFT-plus-RL the primary learning contrast |
| File edit restrictions do not isolate candidate execution | High | Separate processes, trusted broker identity, restricted capabilities, and tampering checks |
| Already-fixed later incidents can be misclassified as replay failures | High | Add already-contained and indeterminate states; avoid unnecessary repair calls |
| Missing observations are not observed violations | High | Report the composite endpoint, observed violations, and missing-outcome bounds separately |
| Conditional historical subsets differ across methods | Medium | Use a fixed shared panel for primary retention and disclose conditional denominators |
| Passing enforced tests is a circular retention claim | High | Use sealed historical-family companions; treat finite-suite induction as an elementary invariant |
| One-patch training does not learn a long-horizon repair strategy | Scope limitation | State this explicitly and measure feedback-distribution shift |
| Only one narrow frozen-model implementation; no sufficient research corpus or GPU pilot | Blocking broad empirical/RL claims | Treat live ownership repair as engineering evidence; keep broader paper claims proposed until controlled experiments exist |
| Research novelty is unestablished | Blocking novelty claims | Broaden related-work comparison and let controlled evidence determine the contribution |

The architecture is plausible to prototype, but the case for RL remains unproven. A single-benchmark demo does not establish research value. Sections 15–16 supersede any earlier impression that the design is ready for an empirical paper merely because it has a reward formula and proofs.

## 16. Implementation contract after critical review

Current adapter repair receives policy text, native tool schemas, violation/conversation traces and a generic argument-selected read-only view. The broker does not compute an owner or protection flag for this mode. Trusted session/consent metadata and independent evaluators remain outside the candidate. Fixed-rule mode remains the explicit-rule comparator. Failed live adapter attempts are retained and reported rather than accepted by changing tests.

### Pilot scope and exact comparisons

Start with the τ-bench retail copy (Section 0). Implement ownership and authentication first; specify action-bound confirmation separately. The 1,375-call reference archive is a regression source, not an automatically valid or sealed utility suite. Resolve and disclose the `test-64` task/login conflict before freezing authorized utility cases. A separately authored second integration is a P1 item; the τ-bench airline domain shares authors and code style, so it does not establish an independent family.

The four main conditions are unrepaired, frozen independent-sampling repair, frozen feedback repair, and direct enforcement. Keep a handwritten reference guard as a fixture-solvability check and account for its human effort. Both repair arms share initial source, incident, full contract, historical context, fixed model, acceptance gate, and declared candidate/token/test/wall-time ceilings. Feedback alone receives permitted intermediate execution diagnostics. Limit generation to three candidates per incident, select the first gate-passing candidate in a fixed order, and count failures and unused allowance honestly.

The current gate freezes secret-seeded development/sealed identity panels per run, with disjoint fixture users and all nine protected tools. Only aggregate development diagnostics enter feedback; conflict outcome records and sealed diagnostics do not. Sealed checks run once after development selection; failure or incomplete execution stops repair rather than informing another candidate. These panels prevent fixed-ID fitting but remain self-authored checks within one public benchmark, not the proposed independently authored final study.

Use deterministic action replay and repeated end-to-end agent runs, with clean tasks included. Fix one short incident stream per implementation if reporting retention; score all frozen snapshots afterward on the same sealed companions. Defer order sensitivity, adaptive attacks, public benchmark adaptation, and external developer studies to later protocols. Report each implementation separately; one or two clusters cannot establish population-level transfer.

### Evaluator acceptance tests

Before hosting, the finite required suite covers forged success, ownership bypass, duplicate effects, test/import tampering, cross-fixture access, missing observations after timeout, stale-parent activation, and deny-all behavior. Score from broker state and events. Unsafe effects must be rejected or detected; incomplete replay is indeterminate; stale promotion fails compare-and-swap; deny-all fails legitimate-task checks. Passing this suite is an implementation gate, not a universal isolation proof.

The broker binds identity and fixture capability outside candidate arguments. Candidate code has no evaluator interpreter, host mounts, secrets, dependency installation, or unrestricted network access. Separate observation-mode fault injection from direct-enforcement mode in reports. Immutable dependency, contract, checker, fixture, and source versions define the validation scope.

### Contracts, provenance, and data acquisition

Maintain an inventory with implementation author, contract reviewer, shared ancestors, source/license, fault and descendants, case IDs, reference repair, oracle author, and intended partition. Keep descendants of a source defect together. Seek a separate reviewer and independently authored sealed companions; record disagreement and adjudication against the explicit contract before the lock. Shared authorship is a risk to measure, not an asserted defect.

Owner-authored policy and correct broker state do not eliminate semantic mistakes in the checker. Treat disagreement between independently written oracles as an issue to resolve, not a vote whose majority automatically becomes truth.

### Research gate and model identity

The primary learning comparison starts both conditions from the identical SFT checkpoint. Add continued SFT or iterated rejection-sampling fine-tuning with comparable declared collection/training budgets before attributing gains to the algorithm choice. Use several training seeds where feasible; a one-seed study is exploratory.

Nano-30B-A3B-Base-BF16 is a candidate checkpoint to profile, not a committed hardware plan. NVIDIA's published GRPO-LoRA recipe uses 2 nodes x 8 GPUs; that is an example configuration, not a demonstrated minimum [S28]. Pin tokenizer, LoRA targets, inherited configuration, framework commit, rollout engine, GPU type/count, and spending ceiling. Exercise rollout, protected reward, update, save, reload, fresh generation, and serving of the exact artifact before scaling.

Measure empirical mixed-reward group frequency per task and checkpoint. Under conditional independence it is 1 - p^g - (1-p)^g, so both easy and hard tasks can have weak signal. Use training data to select curricula; preserve the declared final population. Keep costs outside the primary binary reward. With a positive stabilizer, a cost-only group's normalized signal is attenuated by eta*s_C/(eta*s_C+epsilon); a small coefficient does not by itself establish a small effect.

Freeze a harm-justified utility margin and calibrated family/sample counts before confirmatory evaluation. The paper specifies one-sided 97.5% bounds for both required learning endpoints; plan joint power. The target model remains fixed, and a result on a smaller repairer supports that tested configuration rather than an assumed training effect on Super.

### Claim and release discipline

The document's ownership example is a hand-written specification, never a claimed generated patch. The demo must show real code changes, trusted state transitions, and valid tasks succeeding. Publish build/test commands with relative paths and pinned dependencies; include the verification scripts themselves. Document compilation checks are separate from project experiments.

Related work now includes ClawGuard, AttriGuard, Tau-bench, Self-Debugging, Reflexion, SWE-bench, Agentless, CodeRL, and RLEF. Maintainer repository descriptions remain product-positioning evidence, not independent research-performance evidence. Confirm real authors and affiliations before submission, with anonymity handled according to the selected venue.

## Sources

Sources checked during 2–4 October 2026. Summaries above distinguish existing work from this proposed design.

- **S1 — Nebius:** [NVIDIA Nemotron 3 Super on Token Factory](https://nebius.com/blog/posts/nemotron3-super-now-available).
- **S2 — USENIX Security 2025:** [PATCHAGENT: A Practical Program Repair Agent Mimicking Human Expertise](https://www.usenix.org/conference/usenixsecurity25/presentation/yu-zheng).
- **S3 — ICSE 2026 / author paper:** [AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](https://arxiv.org/abs/2503.18666).
- **S4 — Author preprint:** [ClawGuard](https://arxiv.org/abs/2604.11790).
- **S5 — Maintainer repository:** [PromptArmor plugin](https://github.com/allsmog/promptarmor-plugin).
- **S6 — Maintainer repository:** [AgentProof](https://github.com/evanl666/agentproof). Capability description retrieved through indexed repository results; full-page retrieval timed out.
- **S7 — Benchmark authors:** [AgentDojo documentation](https://agentdojo.spylab.ai/) and [paper](https://arxiv.org/abs/2406.13352).
- **S8 — ACL Findings 2024:** [InjecAgent](https://aclanthology.org/2024.findings-acl.624/).
- **S9 — USENIX Security 2026:** [AttriGuard](https://www.usenix.org/conference/usenixsecurity26/presentation/he-yu).
- **S10 — Author preprint, 2024:** [Code Security Vulnerability Repair Using Reinforcement Learning with Large Language Models](https://arxiv.org/abs/2401.07031).
- **S11 — Author paper, 2025:** [SWE-RL](https://arxiv.org/abs/2502.18449).
- **S12 — ICML 2026 proceedings:** [Self-play SWE-RL](https://proceedings.mlr.press/v306/wei26x.html).
- **S13 — Author paper:** [PISmith](https://arxiv.org/abs/2603.13026), version 2; author record states to appear in COLM 2026.
- **S14 — Author preprint, 2026:** [RETA](https://arxiv.org/abs/2606.15441).
- **S15 — Author preprint, 29 September 2026:** [Self-Evolving Defense](https://arxiv.org/abs/2609.36603).
- **S16 — GRPO source paper:** [DeepSeekMath](https://arxiv.org/abs/2402.03300).
- **S17 — NVIDIA documentation:** [NeMo RL GRPO guide](https://docs.nvidia.com/nemo/rl/nightly/guides/grpo.html).
- **S18 — NVIDIA documentation:** [NeMo RL LoRA guide](https://docs.nvidia.com/nemo/rl/nightly/guides/lora.html).
- **S19 — Author paper:** [Understanding R1-Zero-Like Training: A Critical Perspective](https://arxiv.org/abs/2503.20783).
- **S20 — NVIDIA technical report/preprint:** [GDPO](https://arxiv.org/abs/2601.05242).

- **S21 — Author paper:** [Tau-bench](https://arxiv.org/abs/2406.12045).
- **S22 — Author paper:** [Self-Debugging](https://arxiv.org/abs/2304.05128).
- **S23 — Author paper:** [Reflexion](https://arxiv.org/abs/2303.11366).
- **S24 — Author paper:** [SWE-bench](https://arxiv.org/abs/2310.06770).
- **S25 — Author paper:** [Agentless](https://arxiv.org/abs/2407.01489).
- **S26 — Author paper:** [CodeRL](https://arxiv.org/abs/2207.01780).
- **S27 — Author paper:** [RLEF](https://arxiv.org/abs/2410.02089).
- **S28 — NVIDIA configuration:** [Nano GRPO-LoRA example](https://github.com/NVIDIA-NeMo/RL/blob/main/examples/configs/recipes/llm/grpo-nanov3-30BA3B-2n8g-fsdp2-lora.yaml).
- **S29 — Sierra repository (MIT):** [τ-bench](https://github.com/sierra-research/tau-bench); retail policy `tau_bench/envs/retail/wiki.md`, tools in `tau_bench/envs/retail/tools/`. Inspected 4 October 2026 at commit `59a200c`.
- **S30 — Sierra repository (MIT):** [τ²-bench](https://github.com/sierra-research/tau2-bench); retail tools in `src/tau2/domains/retail/tools.py`. Inspected 4 October 2026 at commit `5bfa7e3`.
