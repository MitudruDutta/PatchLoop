"""Replay reference tool calls and compare final database states.

Each task starts from a fresh database. The tools are deterministic, so a task
passes exactly when its final state hash equals the hash recorded by running
the upstream tau-bench tools (scripts/vendor_tau_bench.py).
"""

import json
import sys
from hashlib import sha256
from multiprocessing import Pool

from patchloop.apps import tau_retail as app


def db_hash(db: dict) -> str:
    return sha256(json.dumps(db, sort_keys=True).encode()).hexdigest()


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
    # ponytail: one machine, all cores; shard tasks across Serverless Jobs if the suite outgrows it
    with Pool() as pool:
        results = pool.map(_check, [(t, invoke) for t in tasks], chunksize=8)
    return [task_id for task_id, ok in results if not ok]


if __name__ == "__main__":
    tasks = app.reference_calls()
    failed = failures(tasks=tasks)
    print(f"{len(tasks) - len(failed)}/{len(tasks)} tasks reproduce the reference state "
          f"({sum(len(t['actions']) for t in tasks)} calls)")
    sys.exit(1 if failed else 0)
