from pathlib import Path

from patchloop.evaluation import compare


def test_four_conditions_share_cases_budget_and_panels_without_cross_feedback(tmp_path, monkeypatch):
    evaluations, repairs = [], []
    def campaign(output, client, model, **kwargs):
        evaluations.append((output, kwargs))
        return {"status": "completed", "unique_findings": 1, "findings": [{"timeline": []}]}
    def repair(output, store, model, attempts, **kwargs):
        repairs.append(kwargs)
        return {"status": "unresolved", "attempts": []}
    monkeypatch.setattr(compare, "run_campaign", campaign)
    monkeypatch.setattr(compare, "run_repair", repair)
    result = compare.run_comparison(tmp_path / "compare", "nvidia/test-nemotron", client=object())
    assert set(result["conditions"]) == {"unrepaired", "independent", "feedback", "reference"}
    assert repairs[0]["strategy"] == "independent" and repairs[1]["strategy"] == "feedback"
    assert repairs[0]["validation_suite"] is repairs[1]["validation_suite"]
    assert repairs[0]["temperature"] == repairs[1]["temperature"] == .7
    assert repairs[0]["incident"] is repairs[1]["incident"]
    assert all(kwargs["cases"] == evaluations[1][1]["cases"] for _, kwargs in evaluations[1:])
    assert evaluations[-1][1]["reference"] is True


def test_comparison_never_invents_incident_when_discovery_finds_none(tmp_path, monkeypatch):
    monkeypatch.setattr(compare, "run_campaign", lambda *args, **kwargs:
        {"status": "completed", "unique_findings": 0, "findings": []})
    def unexpected(*args, **kwargs):
        raise AssertionError("No discovery must not produce a fabricated repair")
    monkeypatch.setattr(compare, "run_repair", unexpected)
    result = compare.run_comparison(tmp_path / "zero", "nvidia/test-nemotron", client=object())
    assert result["conditions"]["independent"]["status"] == "not_run"
    assert result["conditions"]["feedback"]["status"] == "not_run"
