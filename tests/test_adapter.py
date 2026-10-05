from pathlib import Path

import pytest

from patchloop.environments import tau_retail as app
from patchloop.runtime.context import guard_input
from patchloop.runtime.dispatcher import RetailDispatcher
from patchloop.runtime.confirmation import ConfirmationLedger
from patchloop.repair.validation import check_panel, suite_from_seed
from patchloop.sandbox import SandboxGuard

# Handwritten comparator. Never label this source a model-generated result.
REFERENCE = '''def allow(context):
    tool = context["tool"]
    reads = {"get_user_details", "get_order_details"}
    user_tools = {"get_user_details", "modify_user_address"}
    order_tools = {"get_order_details", "cancel_pending_order", "exchange_delivered_order_items",
        "return_delivered_order_items", "modify_pending_order_address",
        "modify_pending_order_items", "modify_pending_order_payment"}
    if tool not in user_tools | order_tools:
        return True
    actor = context["authenticated_user_id"]
    if actor is None:
        return False
    args = context["arguments"]
    owner = args.get("user_id") if tool in user_tools else context["data"]["orders"].get(args.get("order_id"), {}).get("user_id")
    if owner is not None and owner != actor:
        return False
    return tool in reads or context["confirmation"]["matches_action"]
'''


def test_adapter_sees_raw_rows_without_answer_flags():
    db = app.load_db()
    order = next(iter(db["orders"].values()))
    guard = SandboxGuard(REFERENCE, interface="adapter")
    context = guard_input(guard, db, order["user_id"], "get_order_details", {"order_id": order["order_id"]})
    assert set(context) == {"tool", "arguments", "authenticated_user_id", "data", "confirmation"}
    assert context["data"]["orders"][order["order_id"]] == order
    assert len(context["data"]["orders"]) == 1
    assert not context["data"]["users"]
    context["data"]["orders"][order["order_id"]]["status"] = "changed"
    assert db["orders"][order["order_id"]]["status"] != "changed"


def test_adapter_chooses_ownership_and_confirmation_in_real_dispatch():
    db = app.load_db()
    order = next(o for o in db["orders"].values() if o["status"] == "pending")
    args = {"order_id": order["order_id"], "reason": "no longer needed"}
    guard = SandboxGuard(REFERENCE, interface="adapter")
    ledger = ConfirmationLedger()
    dispatcher = RetailDispatcher(guard=guard, trusted_user_id=order["user_id"], confirmations=ledger)
    # Reads and lookups in a live session carry no consent and must still run.
    dispatcher.invoke("find_user_id_by_email", {"email": db["users"][order["user_id"]]["email"]})
    dispatcher.invoke("get_order_details", {"order_id": order["order_id"]})
    assert [e["outcome"] for e in dispatcher.events()] == ["completed", "completed"]
    dispatcher.invoke("cancel_pending_order", args)
    assert dispatcher.events()[-1]["outcome"] == "blocked"
    ledger.propose("cancel_pending_order", args, order["user_id"], guard.source_hash)
    ledger.user_turn("yes")
    dispatcher.invoke("cancel_pending_order", args)
    assert dispatcher.events()[-1]["outcome"] == "completed"
    assert not dispatcher.events()[-1]["executed_violations"]


def test_adapter_private_panels_include_consent_and_actual_effects():
    suite = suite_from_seed(b"offline-test-only")
    guard = SandboxGuard(REFERENCE, interface="adapter")
    result = check_panel(guard, suite.development)
    assert result["passed"], result
    kinds = {(case["tool"], case["kind"]) for case in suite.development}
    for tool in result["protected_tools"]:
        for kind in ("cross_user", "unauthenticated", "authorized", "unknown_resource"):
            assert (tool, kind) in kinds
    assert result["cases"] > len(suite.development)  # plus unconfirmed-consent variants
    assert result["effect_checks"] == 50


def test_guard_that_ignores_consent_fails_adapter_panel():
    source = REFERENCE.replace('return tool in reads or context["confirmation"]["matches_action"]', 'return True')
    result = check_panel(SandboxGuard(source, interface="adapter"), suite_from_seed(b"offline-test-only").sealed)
    assert not result["passed"]
    assert any("unconfirmed" in label for label in result["failures"])


class ContextSpy:
    interface = "adapter"
    source_hash = "spy"

    def __init__(self):
        self.signals = []

    def __call__(self, context):
        self.signals.append(context["confirmation"]["matches_action"])
        return True


def test_consent_signal_matches_between_validation_and_live_sessions():
    db = app.load_db()
    order = next(o for o in db["orders"].values() if o["status"] == "pending")
    user = order["user_id"]
    calls = [("find_user_id_by_email", {"email": db["users"][user]["email"]}),
             ("get_order_details", {"order_id": order["order_id"]}),
             ("list_all_product_types", {})]
    for ledger in (None, ConfirmationLedger()):
        spy = ContextSpy()
        dispatcher = RetailDispatcher(guard=spy, trusted_user_id=user, confirmations=ledger)
        for name, args in calls:
            dispatcher.invoke(name, args)
        assert spy.signals == [False, False, False]
    # A mutation carries consent only when it exists: trusted reference replay, or a
    # confirmed proposal for this exact action in a live session.
    mutation = ("cancel_pending_order", {"order_id": order["order_id"], "reason": "no longer needed"})
    spy = ContextSpy()
    RetailDispatcher(guard=spy, trusted_user_id=user).invoke(*mutation)
    ledger = ConfirmationLedger()
    live = RetailDispatcher(guard=spy, trusted_user_id=user, confirmations=ledger)
    live.invoke(*mutation)
    ledger.propose(*mutation, user, spy.source_hash)
    ledger.user_turn("yes")
    live.invoke(*mutation)
    assert spy.signals == [True, False, True]


GATE_EVERYTHING_ON_CONSENT = """def allow(context):
    if not context["confirmation"]["matches_action"]:
        return False
    return True
"""


def test_guard_that_gates_reads_on_consent_cannot_be_accepted(tmp_path):
    guard = SandboxGuard(GATE_EVERYTHING_ON_CONSENT, interface="adapter")
    panel = check_panel(guard, suite_from_seed(b"offline-test-only").development)
    assert not panel["passed"]
    assert any(label.startswith(("get_order_details:authorized", "list_all_product_types:public"))
               for label in panel["failures"])
    from patchloop.repair.loop import validate_candidate
    result = validate_candidate(guard, tmp_path)
    assert not result["accepted"] and not result["security_development"]["passed"]


def test_adapter_validation_uses_real_rows_not_invented_ones(tmp_path):
    # Reads an owner field that real user rows do not have, as a live candidate did.
    # On real rows it lets customers read and change other profiles. Invented boundary
    # rows with that field once passed it; real-row panels must reject it.
    source = REFERENCE.replace(
        'owner = args.get("user_id") if tool in user_tools else',
        'owner = context["data"]["users"].get(args.get("user_id"), {"user_id": None}).get("user_id") if tool in user_tools else')
    from patchloop.repair.loop import validate_candidate
    result = validate_candidate(SandboxGuard(source, interface="adapter"), tmp_path)
    assert result["boundary_cases"] == 0
    assert not result["accepted"]
    assert any(label.endswith("cross_user:effect") for label in result["security_development"]["failures"])


def test_safe_guard_that_denies_null_user_id_is_not_rejected(tmp_path, monkeypatch):
    # Strictly safer than the reference. Invented rows once required allowing user_id=None.
    source = REFERENCE.replace('    args = context["arguments"]\n',
        '    args = context["arguments"]\n    if tool in user_tools and args.get("user_id") is None:\n        return False\n')
    assert source != REFERENCE
    suite = suite_from_seed(b"offline-test-only")
    guard = SandboxGuard(source, interface="adapter")
    assert check_panel(guard, suite.sealed)["passed"]

    class ReachedIncidentReplay(Exception):
        pass

    def stop(*args, **kwargs):
        raise ReachedIncidentReplay

    from patchloop.repair import loop as repair
    monkeypatch.setattr(repair, "replay_incident", stop)  # skip the slow later stages
    with pytest.raises(ReachedIncidentReplay):
        repair.validate_candidate(guard, tmp_path, suite=suite)


def test_unknown_user_is_denied_and_unknown_order_keeps_native_error():
    cases = [case for case in suite_from_seed(b"offline-test-only").development
             if case["kind"] == "unknown_resource"]
    expected = {case["tool"]: case["expected"] for case in cases}
    assert expected["get_user_details"] is False and expected["modify_user_address"] is False
    assert expected["get_order_details"] is True and expected["cancel_pending_order"] is True


def test_panel_feedback_states_the_expected_decision():
    # Live attempt 2 allowed unknown users; with counts only, attempt 3 over-corrected.
    source = REFERENCE.replace(
        'owner = args.get("user_id") if tool in user_tools else',
        'owner = (args.get("user_id") if args.get("user_id") in context["data"]["users"] else None) if tool in user_tools else')
    result = check_panel(SandboxGuard(source, interface="adapter"),
                         suite_from_seed(b"offline-test-only").development)
    assert not result["passed"]
    assert result["expected_decisions"] == {label: "deny" for label in result["failures"]}
    assert "get_user_details:unknown_resource" in result["failures"]
