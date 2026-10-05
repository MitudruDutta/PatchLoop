"""Replay reference tool calls and compare final database states.

Each task starts from a fresh database. The tools are deterministic, so a task
passes exactly when its final state hash equals the hash recorded by running
the upstream tau-bench tools (scripts/vendor_tau_bench.py).
"""

import json
import argparse
from multiprocessing import Pool

from patchloop.apps import tau_retail as app
from patchloop.dispatcher import RetailDispatcher, state_hash
from patchloop.context import guard_input
from patchloop.manifest import load_manifest
from patchloop.policy import AUTH_TOOLS, guard_context


class _BatchedGuard:
    """Reuse decisions only when current trusted context matches the batch."""
    def __init__(self, guard, contexts):
        self.guard = guard
        self.contexts = contexts
        self.decisions = guard.decide_many(contexts)
        self.position = 0
        self.source_hash = guard.source_hash
        self.interface = getattr(guard, "interface", "fixed")

    def __call__(self, context):
        index = self.position
        self.position += 1
        if context == self.contexts[index]:
            return self.decisions[index]
        # Earlier denied operations can change later context. Never reuse a
        # decision derived from a different resource or session identity.
        return self.guard(context)


def db_hash(db: dict) -> str:
    return state_hash(db)


def raw_invoke(db: dict, name: str, kwargs: dict):
    return app.TOOLS[name].invoke(data=db, **kwargs)


def replay_task(task: dict, invoke=raw_invoke) -> str:
    db = app.load_db()
    for call in task["actions"]:
        if call["name"] in app.TERMINATE_TOOLS:
            continue
        try:  # same as tau-bench Env.step: a raising tool leaves state as it left it
            invoke(db, call["name"], call["kwargs"])
        except Exception:
            pass
    return db_hash(db)


def _check(job):
    task, invoke = job
    return task["id"], replay_task(task, invoke) == task["expected_hash"]


def failures(invoke=raw_invoke, tasks=None) -> list[str]:
    """IDs of tasks whose final state differs from the reference. `invoke` must be picklable."""
    tasks = app.reference_calls() if tasks is None else tasks
    with Pool(processes=4) as pool:
        results = pool.map(_check, [(t, invoke) for t in tasks], chunksize=8)
    return [task_id for task_id, ok in results if not ok]


def check_guarded_task(task: dict, guard=None) -> dict:
    """Check output and state preservation under trusted reference-task identity.

    These tasks omit login/confirmation turns. They test authenticated utility,
    not whether real conversations authenticate or provide valid consent.
    """
    baseline_db = app.load_db()
    mismatches = []
    identity_conflicts = []
    baseline_errors = 0
    contexts, expected_outputs = [], []
    for index, call in enumerate(task["actions"]):
        contexts.append(guard_input(guard, baseline_db, task["user_id"], call["name"], call["kwargs"]))
        try:
            expected = raw_invoke(baseline_db, call["name"], call["kwargs"])
        except Exception as exc:
            baseline_errors += 1
            expected = f"Error: {type(exc).__name__}"
        if call["name"] in AUTH_TOOLS and expected in baseline_db["users"]:
            if expected != task["user_id"]:
                identity_conflicts.append({"call": index, "task_user": task["user_id"],
                                           "lookup_user": expected})
        expected_outputs.append(expected)
    runner = _BatchedGuard(guard, contexts) if guard is not None else None
    guarded = RetailDispatcher(enforce=guard is None, guard=runner,
                               trusted_user_id=task["user_id"])
    for index, (call, expected) in enumerate(zip(task["actions"], expected_outputs)):
        actual = guarded.invoke(call["name"], call["kwargs"])
        if actual != expected:
            mismatches.append(index)
    return {
        "task_id": task["id"], "output_mismatches": mismatches,
        "baseline_state_matches": db_hash(baseline_db) == task["expected_hash"],
        "guarded_state_matches": db_hash(guarded.snapshot()) == task["expected_hash"],
        "identity_conflicts": identity_conflicts,
        "executed_violations": sum(bool(e["executed_violations"]) for e in guarded.events()),
        "execution_errors": sum(e["outcome"] == "error" for e in guarded.events()),
        "baseline_errors": baseline_errors,
        "calls": len(task["actions"]),
    }


def _check_guarded(job):
    return check_guarded_task(*job)


def guarded_results(tasks=None, guard=None) -> list[dict]:
    tasks = app.reference_calls() if tasks is None else tasks
    with Pool(processes=4) as pool:
        return pool.map(_check_guarded, [(task, guard) for task in tasks], chunksize=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guarded", action="store_true",
                        help="Compare handwritten guard outputs and final states")
    args = parser.parse_args()
    tasks = app.reference_calls()
    if args.guarded:
        results = guarded_results(tasks)
        expected_calls = {task["id"]: len(task["actions"]) for task in tasks}
        coverage_complete = (len(results) == len(tasks)
                             and {row["task_id"] for row in results} == set(expected_calls)
                             and all(row["calls"] == expected_calls[row["task_id"]]
                                     for row in results))
        excluded = set(load_manifest()["excluded_from_preservation"])
        failed = [r["task_id"] for r in results if not r["baseline_state_matches"]
                  or r["executed_violations"] or r["execution_errors"] > r["baseline_errors"]
                  or (r["task_id"] not in excluded
                      and (r["output_mismatches"] or not r["guarded_state_matches"]))]
        if not coverage_complete:
            failed.append("incomplete_archive_coverage")
        matched = sum(not r["output_mismatches"] and r["guarded_state_matches"]
                      and r["baseline_state_matches"] for r in results)
        print(f"{matched}/{len(tasks)} tasks preserve outputs and state "
              f"({sum(r['calls'] for r in results)} reference calls; trusted fixture login)")
        print(f"{len(tasks) - len(excluded)} policy-consistent preservation cases; "
              f"{len(excluded)} explicit conflict case(s) checked for containment")
        conflicts = [r for r in results if r["identity_conflicts"]]
        if conflicts:
            print(json.dumps({"reference_identity_conflicts": conflicts}))
    else:
        failed = failures(tasks=tasks)
        print(f"{len(tasks) - len(failed)}/{len(tasks)} tasks reproduce the reference state "
              f"({sum(len(t['actions']) for t in tasks)} scheduled calls)")
    if failed:
        print(json.dumps({"failed_tasks": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
