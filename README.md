# PatchLoop

Many AI agents keep their security rules only in the prompt. PatchLoop tests a tool-using agent, finds the policy rules that no code enforces, writes guard code with an NVIDIA Nemotron model, and proves with tests that legitimate work still succeeds. Each accepted repair becomes a pull request with the patch, the new tests, and an evidence report.

**Status (4 October 2026):** design complete; implementation has started. No repair results exist yet. This README will describe only behavior that the released code demonstrates.

## How it works

1. **Test:** an adversarial tester (a Nemotron model acting as a dishonest customer) talks to the target agent in a sandboxed copy of the application.
2. **Record:** a trusted dispatcher logs every tool call, the authenticated session, and every data change.
3. **Detect:** a protected evaluator flags policy violations, such as an action on another user's account or a change without explicit confirmation.
4. **Repair:** Nemotron writes a guard patch for the affected tools.
5. **Validate:** the patch runs in an isolated sandbox. The violation must now fail, and every legitimate reference action must still pass.
6. **Publish:** an accepted patch becomes a new version and a pull request.

The first application is a copy of the retail environment from [τ-bench](https://github.com/sierra-research/tau-bench) (MIT license, © Sierra). In τ-bench, rules such as "help only the authenticated user" exist only in the agent's policy text, by design, because the benchmark measures policy-following. The 1,375 correct tool calls from its 635 retail tasks serve as PatchLoop's utility regression suite. PatchLoop changes only its own copy; this is not a report of a τ-bench defect.

## Planned NVIDIA and Nebius usage

| Component | Technology |
|---|---|
| Target agent, repair model | NVIDIA Nemotron 3 Super via Nebius Token Factory |
| Adversarial tester | Fast Nemotron model via Nebius Token Factory |
| Application, sandbox, workers | Nebius AI Cloud |
| Parallel test campaigns (optional) | Nebius Serverless Jobs |
| Repair guidance retrieval | Tavily API |

This table is the plan. It will be replaced with the exact model identifiers and services once they run.

## Repository layout

| Path | Content |
|---|---|
| `docs/PRD.md` | Product requirements, architecture, and plan (Section 0 is the current plan) |
| `docs/paper/` | Research protocol manuscript (Markdown and LaTeX), compiled PDF, and planning calculations |

## Research protocol

`docs/paper/` holds a proposed method and experimental protocol. It reports no experiments. It also describes an optional later study that trains the repair model with reinforcement learning; that study is not part of the current build.

Build the PDF with [Tectonic](https://tectonic-typesetting.github.io/book/latest/installation/) 0.17.0:

```bash
cd docs/paper
tectonic --keep-logs --outdir build PATCHLOOP_RL_Research_Paper.tex
```

Reproduce the illustrative planning arithmetic (Python 3.10+, standard library only):

```bash
python3 docs/paper/statistics_calculations.py
```

## License

[MIT](LICENSE). Third-party code included later keeps its own license notice.
