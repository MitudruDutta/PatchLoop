from patchloop import replay
from patchloop.apps import tau_retail as app
from patchloop.sandbox import SandboxGuard
from patchloop.versions import source_hash


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


def test_reference_guard_preserves_consistent_tasks_and_reports_identity_conflict():
    results = replay.guarded_results()
    assert len(results) == 635
    assert sum(r["calls"] for r in results) == 1375
    assert all(r["baseline_state_matches"] for r in results)
    failures = {r["task_id"] for r in results
                if not r["guarded_state_matches"] or r["output_mismatches"]}
    conflicts = {r["task_id"] for r in results if r["identity_conflicts"]}
    assert failures == conflicts == {"test-64"}
    conflict = next(r for r in results if r["task_id"] == "test-64")
    assert conflict["identity_conflicts"] == [{
        "call": 0, "task_user": "harper_moore_6183", "lookup_user": "james_sanchez_3954",
    }]
    assert conflict["output_mismatches"]


def test_guarded_cli_known_conflict_is_success_but_security_failure_is_not(monkeypatch, capsys):
    rows = [{"task_id": t["id"], "output_mismatches": [], "guarded_state_matches": True,
             "baseline_state_matches": True, "executed_violations": 0,
             "execution_errors": 0, "baseline_errors": 0, "identity_conflicts": [],
             "calls": len(t["actions"])} for t in app.reference_calls()]
    conflict = next(r for r in rows if r["task_id"] == "test-64")
    conflict.update(output_mismatches=[1], guarded_state_matches=False,
                    identity_conflicts=[{"task_user": "archived", "lookup_user": "different"}])
    monkeypatch.setattr("sys.argv", ["replay", "--guarded"])
    monkeypatch.setattr(replay, "guarded_results", lambda tasks: rows)
    assert replay.main() == 0
    assert "test-64" in capsys.readouterr().out
    conflict["executed_violations"] = 1
    assert replay.main() == 1
    conflict["executed_violations"] = 0
    rows[0]["output_mismatches"] = [0]
    assert replay.main() == 1
    rows[0]["output_mismatches"] = []
    rows.pop()
    assert replay.main() == 1


def test_task_batches_decisions_and_preserves_result():
    source = '''def allow(context):
    return not context["requires_authentication"] or (context["authenticated_user_id"] is not None
        and (context["owner_id"] is None or context["owner_id"] == context["authenticated_user_id"]))
'''
    class RecordingGuard:
        source_hash = source_hash(source)
        batches = []
        def decide_many(self, contexts):
            self.batches.append(len(contexts))
            return SandboxGuard(source).decide_many(contexts)
        def __call__(self, context):
            raise AssertionError("Matching contexts should use the batch")
    task = next(t for t in app.reference_calls() if len(t["actions"]) > 2 and t["id"] != "test-64")
    guard = RecordingGuard()
    result = replay.check_guarded_task(task, guard)
    assert guard.batches == [len(task["actions"])]
    assert not result["output_mismatches"] and result["guarded_state_matches"]


def test_batch_falls_back_when_trusted_context_changes():
    class RecordingGuard:
        source_hash = "test"
        def decide_many(self, contexts):
            return [True]
        def __call__(self, context):
            return False
    runner = replay._BatchedGuard(RecordingGuard(), [{"owner_id": "before"}])
    assert runner({"owner_id": "changed"}) is False
