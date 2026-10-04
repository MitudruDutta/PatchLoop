from patchloop import replay
from patchloop.apps import tau_retail as app


def deny_all(db, name, kwargs):
    return "Error: denied"


def test_reference_calls_reproduce_upstream_state():
    tasks = app.reference_calls()
    assert len(tasks) == 635
    assert sum(len(t["actions"]) for t in tasks) == 1375
    assert replay.failures(tasks=tasks) == []


def test_suite_detects_over_blocking():
    # A guard that blocks everything must fail exactly the tasks that change state.
    base = replay.db_hash(app.load_db())
    tasks = app.reference_calls()
    changing = {t["id"] for t in tasks if t["expected_hash"] != base}
    assert changing
    assert set(replay.failures(deny_all, tasks)) == changing


def test_fresh_databases_are_independent():
    a, b = app.load_db(), app.load_db()
    next(iter(a["users"].values()))["email"] = "changed@example.com"
    assert replay.db_hash(b) == replay.db_hash(app.load_db())
