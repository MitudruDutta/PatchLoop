import json

import pytest

from patchloop.repair import loop as repair
from patchloop.sandbox import SandboxGuard
from patchloop.repair.versions import BASELINE_SOURCE, StaleVersion, VersionStore, source_hash

CORRECT = '''def allow(context):
    if not context["requires_authentication"]:
        return True
    user = context["authenticated_user_id"]
    if user is None:
        return False
    return context["owner_id"] is None or context["owner_id"] == user
'''


def test_prompt_schema_matches_real_records_without_invented_user_fields():
    schema = repair.data_schema()
    assert "user_id" not in schema["users"]["record_fields"]
    assert "user_id" in schema["orders"]["record_fields"]
    assert "email" in schema["users"]["record_fields"]


def test_deny_all_fails_utility_boundary_without_expensive_replay(tmp_path):
    result = repair.validate_candidate(SandboxGuard("def allow(context):\n    return False\n"), tmp_path)
    assert result["accepted"] is False
    assert result["boundary_failures"]
    assert not (tmp_path / "reference-outcomes.json").exists()


def test_allow_all_fails_security_boundary(tmp_path):
    result = repair.validate_candidate(SandboxGuard(BASELINE_SOURCE), tmp_path)
    assert result["accepted"] is False
    assert result["boundary_failures"]


def test_generated_guard_controls_real_state_effects():
    before = repair.replay_incident(SandboxGuard(BASELINE_SOURCE))
    after = repair.replay_incident(SandboxGuard(CORRECT))
    assert before["executed_violations"] == 2
    assert after["executed_violations"] == 0
    assert after["unsafe_attempts_blocked"] == 2
    assert after["legitimate_call_completed"]


def test_manifest_preserves_archive_and_explicit_conflict():
    manifest = repair.load_manifest()
    assert set(manifest["excluded_from_preservation"]) == {"test-64"}
    assert "independent human review pending" in manifest["review_status"]


def test_version_promotion_rejects_stale_parent(tmp_path):
    store = VersionStore(tmp_path)
    parent = source_hash(store.current())
    store.promote(CORRECT, expected_parent=parent, evidence_hash="test-evidence")
    assert store.current() == CORRECT
    with pytest.raises(StaleVersion):
        store.promote(BASELINE_SOURCE, expected_parent=parent, evidence_hash="stale-test")
    assert store.current() == CORRECT


def test_artifact_tampering_fails_hash_check(tmp_path):
    store = VersionStore(tmp_path)
    store.promote(CORRECT, expected_parent=source_hash(BASELINE_SOURCE), evidence_hash="test")
    (tmp_path / f"{source_hash(CORRECT)}.py").write_text(BASELINE_SOURCE)
    with pytest.raises(ValueError, match="hash"):
        store.current()


def test_known_conflict_cannot_hide_failure_on_other_task(monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "guarded_results", lambda **kwargs: [
        {"task_id": "test-64", "output_mismatches": [1], "baseline_state_matches": True,
         "guarded_state_matches": False, "executed_violations": 0, "calls": 8,
         "execution_errors": 0, "baseline_errors": 0},
        {"task_id": "train-0", "output_mismatches": [0], "baseline_state_matches": True,
         "guarded_state_matches": True, "executed_violations": 0, "calls": 1,
         "execution_errors": 0, "baseline_errors": 0},
    ])
    result = repair.validate_candidate(SandboxGuard(CORRECT), tmp_path)
    assert not result["accepted"]
    assert result["utility_failures"] == ["train-0"]


@pytest.mark.parametrize("fault", ["missing", "duplicate", "call_count", "error"])
def test_incomplete_or_failed_replay_cannot_activate(monkeypatch, tmp_path, fault):
    rows = [{"task_id": task["id"], "output_mismatches": [],
             "baseline_state_matches": True, "guarded_state_matches": True,
             "executed_violations": 0, "execution_errors": 0, "baseline_errors": 0,
             "calls": len(task["actions"])} for task in repair.app.reference_calls()]
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = dict(rows[0])
    elif fault == "call_count":
        rows[0]["calls"] += 1
    else:
        rows[0]["execution_errors"] = 1
    monkeypatch.setattr(repair, "guarded_results", lambda **kwargs: rows)
    result = repair.validate_candidate(SandboxGuard(CORRECT), tmp_path)
    assert not result["accepted"]
    assert result["new_execution_errors"] == (1 if fault == "error" else 0)
    assert result["coverage_complete"] == (fault == "error")


def test_missing_observations_reject_candidate(monkeypatch, tmp_path):
    monkeypatch.setattr(repair, "replay_incident", lambda guard: {
        "guard_source_hash": guard.source_hash, "events": [], "executed_violations": 0,
        "errors": 1, "unsafe_attempts_blocked": 0, "legitimate_call_completed": False,
    })
    assert not repair.validate_candidate(SandboxGuard(CORRECT), tmp_path)["accepted"]


def test_rejected_candidates_consume_budget_and_keep_evidence(monkeypatch, tmp_path):
    class TestModel:
        def complete(self, messages, **kwargs):
            return {"content": "def allow(context):\n    return 1\n",
                    "request_id": "test-request", "usage": {"total_tokens": 7}}

    class TestSearch:
        def guidance(self):
            return {"results": [{"content": "untrusted guidance"}], "request_id": "test-search"}

    monkeypatch.setattr(repair, "NebiusClient", TestModel)
    monkeypatch.setattr(repair, "TavilyClient", TestSearch)
    output, versions = tmp_path / "run", tmp_path / "versions"
    result = repair.run_repair(output, versions, "nvidia/test-nemotron", attempts=3)
    assert result["status"] == "unresolved"
    assert len(result["attempts"]) == 3
    assert all(a["status"] == "rejected" and a["usage"]["total_tokens"] == 7
               for a in result["attempts"])
    assert VersionStore(versions).current() == BASELINE_SOURCE
    for i in range(1, 4):
        candidate = output / f"candidate-{i}"
        assert (candidate / "request.json").exists()
        assert (candidate / "generation.json").exists()
        assert (candidate / "guard.patch").exists()


@pytest.mark.parametrize("strategy", ["feedback", "independent"])
def test_only_feedback_mode_receives_its_rejected_candidate_source(monkeypatch, tmp_path, strategy):
    calls = []
    bad = "def allow(context):\n    return 1\n"
    class Model:
        def complete(self, messages, **kwargs):
            calls.append(json.loads(messages[1]["content"]))
            return {"content": bad, "request_id": "scripted", "usage": {}}
    class Search:
        def guidance(self):
            return {"results": []}
    monkeypatch.setattr(repair, "TavilyClient", Search)
    repair.run_repair(tmp_path / "run", tmp_path / "versions", "nvidia/test-nemotron",
                      attempts=2, client=Model(), strategy=strategy)
    diagnostics = calls[1]["previous_development_diagnostics"]
    if strategy == "feedback":
        assert diagnostics[0]["candidate_source"] == bad
    else:
        assert diagnostics == [] and calls[0] == calls[1]


def test_already_contained_does_not_spend_generation_or_search(monkeypatch, tmp_path):
    versions = tmp_path / "versions"
    VersionStore(versions).promote(CORRECT, expected_parent=source_hash(BASELINE_SOURCE),
                                 evidence_hash="test")
    def unexpected_provider():
        pytest.fail("Already contained incident must not request a provider")
    monkeypatch.setattr(repair, "NebiusClient", unexpected_provider)
    monkeypatch.setattr(repair, "TavilyClient", unexpected_provider)
    monkeypatch.setattr(repair, "validate_candidate", lambda *args, **kwargs: {"accepted": True})
    result = repair.run_repair(tmp_path / "run", versions, "nvidia/test-nemotron")
    assert result["status"] == "already_contained"
    assert not result["attempts"]


def test_feedback_excludes_conflict_identities_and_sealed_results():
    result = repair.development_feedback({
        "boundary_failures": [], "utility_passed": 634,
        "identity_conflict_outcomes": [{"lookup_user": "private-id"}],
        "sealed_security": {"failures": {"private-case": 1}},
        "security_seed_commitment": "private-seed-commitment",
    })
    assert result == {"boundary_failures": [], "utility_passed": 634}


@pytest.mark.parametrize("indeterminate", [False, True])
def test_sealed_rejection_stops_generation_without_promotion(monkeypatch, tmp_path, indeterminate):
    calls = []
    class TestModel:
        def complete(self, messages, **kwargs):
            calls.append(messages)
            return {"content": BASELINE_SOURCE, "request_id": "test", "usage": {}}
    class TestSearch:
        def guidance(self):
            return {"results": [], "request_id": "test"}
    monkeypatch.setattr(repair, "NebiusClient", TestModel)
    monkeypatch.setattr(repair, "TavilyClient", TestSearch)
    monkeypatch.setattr(repair, "validate_candidate", lambda *args, **kwargs: {
        "accepted": True, "identity_conflict_outcomes": [{"lookup_user": "private-id"}],
    })
    if indeterminate:
        def sealed_timeout(*args):
            raise repair.SandboxError("sealed execution timed out")
        monkeypatch.setattr(repair, "check_panel", sealed_timeout)
    output, versions = tmp_path / "run", tmp_path / "versions"
    result = repair.run_repair(output, versions, "nvidia/test-nemotron", attempts=3)
    assert result["status"] == ("sealed_indeterminate" if indeterminate else "sealed_rejected")
    assert len(calls) == len(result["attempts"]) == 1
    assert "private-id" not in json.dumps(calls)
    assert not result["attempts"][0]["validation"]["accepted"]
    assert VersionStore(versions).current() == BASELINE_SOURCE
