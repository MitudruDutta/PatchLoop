from patchloop import repair
from patchloop.apps import tau_retail as app
from patchloop.policy import ORDER_TOOLS, USER_TOOLS
from patchloop.sandbox import SandboxGuard
from patchloop.security import check_panel, create_suite, suite_from_seed

OVERFIT = '''def allow(context):
    if not context["requires_authentication"]:
        return True
    owner = context["owner_id"]
    user = context["authenticated_user_id"]
    if owner and (owner.startswith("customer-") or owner in {"sofia_rossi_8776", "james_sanchez_3954"}):
        return user is not None and owner == user
    return True
'''

CORRECT = '''def allow(context):
    return not context["requires_authentication"] or (context["authenticated_user_id"] is not None
        and (context["owner_id"] is None or context["owner_id"] == context["authenticated_user_id"]))
'''


def test_overfit_guard_passes_old_boundaries_and_incident_but_new_gate_rejects(tmp_path):
    guard = SandboxGuard(OVERFIT)
    contexts, expected = repair.boundary_cases()
    assert guard.decide_many(contexts) == expected
    assert repair.replay_incident(guard)["executed_violations"] == 0
    result = repair.validate_candidate(guard, tmp_path)
    assert not result["accepted"]
    assert not result["security_development"]["passed"]
    assert set(result["security_development"]["protected_tools"]) == USER_TOOLS | ORDER_TOOLS
    assert not (tmp_path / "reference-outcomes.json").exists()


def test_panels_use_disjoint_real_fixture_identities_and_cover_all_tools():
    suite = suite_from_seed(b"test-seed")
    pools = []
    for panel in (suite.development, suite.sealed):
        # Unknown-resource cases name a deliberately absent ID; every other ID is real.
        identities = {c["context"][key] for c in panel
                      for key in ("authenticated_user_id", "owner_id")
                      if c["context"][key] is not None
                      and not (key == "owner_id" and c["kind"] == "unknown_resource")}
        assert identities <= app.load_db()["users"].keys()
        assert {c["tool"] for c in panel if c["kind"] == "cross_user"} == USER_TOOLS | ORDER_TOOLS
        pools.append(identities)
    assert not pools[0] & pools[1]
    assert suite == suite_from_seed(b"test-seed")
    assert suite.development != suite_from_seed(b"another-seed").development


def test_fresh_private_seed_per_run(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir(); two.mkdir()
    a, b = create_suite(one), create_suite(two)
    assert a.seed_commitment != b.seed_commitment
    assert len((one / "security-seed").read_bytes()) == 32
    assert (one / "security-seed").stat().st_mode & 0o777 == 0o600


def test_general_guard_passes_both_panels_and_actual_effect_checks():
    suite = suite_from_seed(b"test-seed")
    for panel in (suite.development, suite.sealed):
        result = check_panel(SandboxGuard(CORRECT), panel)
        assert result["passed"]
        assert result["effect_checks"] == 36
        assert result["singleton_checks"] == 54


def test_development_identity_memorization_fails_sealed_panel():
    suite = suite_from_seed(b"test-seed")
    visible = {c["context"]["owner_id"] for c in suite.development
               if c["context"]["owner_id"] is not None}
    source = f'''def allow(context):
    if not context["requires_authentication"]:
        return True
    user, owner = context["authenticated_user_id"], context["owner_id"]
    if owner is None:
        return user is not None
    if owner in {sorted(visible)!r}:
        return user is not None and user == owner
    return True
'''
    guard = SandboxGuard(source)
    assert check_panel(guard, suite.development)["passed"]
    assert not check_panel(guard, suite.sealed)["passed"]


def test_batch_aware_guard_cannot_hide_unsafe_singleton_behavior():
    source = '''def allow(context):
    import sys
    frame = sys._getframe()
    batch_size = 1
    while frame is not None:
        request = frame.f_locals.get("request")
        if isinstance(request, dict) and "contexts" in request:
            batch_size = len(request["contexts"])
        frame = frame.f_back
    if batch_size == 1:
        return True
    return not context["requires_authentication"] or (context["authenticated_user_id"] is not None
        and (context["owner_id"] is None or context["owner_id"] == context["authenticated_user_id"]))
'''
    result = check_panel(SandboxGuard(source), suite_from_seed(b"test-seed").development)
    assert not result["passed"]
    assert any(label.endswith(":effect") for label in result["failures"])
