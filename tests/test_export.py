import json

import pytest

from patchloop.export import export_patch
from patchloop.versions import source_hash


def record(source):
    return {"accepted": True, "source_hash": source_hash(source), "interface": "fixed",
            "coverage_complete": True, "scheduled_tasks": 635, "scheduled_calls": 1375,
            "utility_tasks": 634, "utility_passed": 634, "observed_violations": 0,
            "new_execution_errors": 0, "baseline_fidelity": True,
            "security_development": {"passed": True, "cases": 230, "secret_id": "fixture-only-secret-772"},
            "sealed_security": {"passed": True, "cases": 230, "secret_id": "fixture-only-secret-772"},
            "security_seed_commitment": "private-seed", "identity_conflict_outcomes": ["fixture-only-secret-772"]}


def test_export_requires_exact_complete_accepted_evidence(tmp_path):
    source = "def allow(context):\n    return True\n"
    for field, invalid in [("source_hash", "wrong"), ("accepted", False),
                           ("scheduled_tasks", 634), ("utility_passed", 633), ("observed_violations", 1)]:
        with pytest.raises(ValueError, match="complete trusted"):
            export_patch(source, {**record(source), field: invalid}, tmp_path / field)


def test_public_bundle_excludes_private_material_and_preserves_source(tmp_path):
    source = "def allow(context):\n    return True\n"
    output = tmp_path / "bundle"
    result = export_patch(source, record(source), output)
    assert (output / "guard.py").read_text() == source
    public = (output / "validation.public.json").read_text()
    assert "fixture-only-secret-772" not in public and "security_seed_commitment" not in public
    assert json.loads(public)["sealed_security"] == {"passed": True, "cases": 230}
    assert result["source_hash"] == source_hash(source)
