# Third-party notice

The files in this directory, except `__init__.py`, `NOTICE.md`, and `reference_calls.json`, are copied from [τ-bench](https://github.com/sierra-research/tau-bench) by Sierra, commit `59a200c6d575d595120f1cb70fea53cef0632f6b`, path `tau_bench/envs/retail/`. They are licensed under the MIT license in `LICENSE.sierra`.

The only modification is the import line in each `tools/*.py` file: `from tau_bench.envs.tool import Tool` became `from ..tool import Tool`.

`reference_calls.json` is derived from the upstream `tasks_train.py`, `tasks_dev.py`, and `tasks_test.py`. Each expected hash comes from running the upstream tool files. Regenerate everything with `scripts/vendor_tau_bench.py`.

PatchLoop uses this environment as a test application. In τ-bench, some policy rules exist only in the agent's policy text by design, because the benchmark measures policy-following. This is not a report of a τ-bench defect.
