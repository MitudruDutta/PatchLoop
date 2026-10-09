import asyncio
import json
from pathlib import Path

import pytest

from patchloop.sdk.rules import Ruleset, RulesetError, principal_of

VECTORS = json.loads((Path(__file__).parents[1] / "spec/conformance/decisions.json").read_text())


def facts_for(name):
    data = VECTORS["facts"][name]
    unavailable = {tuple(pair) for pair in data["unavailable"]}

    def facts(resource, identifier):
        if (resource, identifier) in unavailable:
            raise ConnectionError("lookup down")
        return data["records"].get(resource, {}).get(identifier)
    return facts


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["id"])
def test_conformance_decision(case):
    rules = Ruleset(VECTORS["rulesets"][case["ruleset"]])
    decision = rules.evaluate(case["tool"], case["arguments"], case["principal"],
                              facts_for(case["ruleset"]), consent=case["consent"])
    assert (decision.decision, decision.reason) == (case["expect"]["decision"], case["expect"]["reason"])
    if "lookups" in case["expect"]:
        assert decision.to_dict()["lookups"] == case["expect"]["lookups"]


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["id"])
def test_conformance_decision_with_async_facts(case):
    sync_facts = facts_for(case["ruleset"])

    async def facts(resource, identifier):
        return sync_facts(resource, identifier)

    rules = Ruleset(VECTORS["rulesets"][case["ruleset"]])
    decision = asyncio.run(rules.aevaluate(case["tool"], case["arguments"], case["principal"], facts, consent=case["consent"]))
    assert (decision.decision, decision.reason) == (case["expect"]["decision"], case["expect"]["reason"])
    if "lookups" in case["expect"]:
        assert decision.to_dict()["lookups"] == case["expect"]["lookups"]


@pytest.mark.parametrize("case", VECTORS["invalid_ruleset_texts"], ids=lambda case: case["id"])
def test_conformance_invalid_ruleset_text(case):
    with pytest.raises(RulesetError):
        Ruleset.from_json(case["text"])


def test_async_facts_in_sync_evaluate_fail_closed_without_warning_leak(recwarn):
    async def facts(resource, identifier):
        return {"customer_id": "c1", "tenant_id": "t1"}
    decision = Ruleset(VECTORS["rulesets"]["helpdesk"]).evaluate(
        "get_ticket", {"ticket_id": "T1"}, principal_of({"subject": "c1", "tenant": "t1"}), facts)
    assert decision.reason == "facts_unavailable"
    assert not [w for w in recwarn if "never awaited" in str(w.message)]


@pytest.mark.parametrize("case", VECTORS["invalid_rulesets"], ids=lambda case: case["id"])
def test_conformance_invalid_ruleset(case):
    with pytest.raises(RulesetError):
        Ruleset(case["ruleset"])


@pytest.mark.parametrize("name", sorted(VECTORS["rulesets"]))
def test_conformance_ruleset_hash(name):
    assert Ruleset(VECTORS["rulesets"][name]).sha256 == VECTORS["ruleset_sha256"][name]


def test_hash_ignores_key_order_and_loaded_copy_is_private():
    data = VECTORS["rulesets"]["helpdesk"]
    reordered = json.loads(json.dumps(data, sort_keys=True))
    rules = Ruleset(data)
    assert Ruleset(dict(reversed(list(reordered.items())))).sha256 == rules.sha256
    edited = json.loads(json.dumps(data))
    rules = Ruleset(edited)
    edited["tools"]["get_ticket"]["access"] = "public"
    assert rules.evaluate("get_ticket", {"ticket_id": "T2"}, principal_of("c1"), facts_for("helpdesk")).reason != "public"


def test_unhashable_references_are_rejected_not_crashing():
    bad = json.loads(json.dumps(VECTORS["rulesets"]["helpdesk"]))
    bad["resources"]["attachment"]["parent"]["resource"] = ["ticket"]
    with pytest.raises(RulesetError):
        Ruleset(bad)


def test_facts_returning_a_non_object_counts_as_unavailable():
    rules = Ruleset(VECTORS["rulesets"]["helpdesk"])
    decision = rules.evaluate("get_ticket", {"ticket_id": "T1"}, principal_of({"subject": "c1", "tenant": "t1"}),
                              lambda resource, identifier: ["not", "a", "record"])
    assert (decision.decision, decision.reason) == ("indeterminate", "facts_unavailable")


@pytest.mark.parametrize("value, expected", [
    (None, None),
    ("c1", {"subject": "c1", "tenant": None}),
    (7, {"subject": 7, "tenant": None}),
    ({"subject": "c1", "tenant": "t1"}, {"subject": "c1", "tenant": "t1"}),
])
def test_principal_normalization(value, expected):
    assert principal_of(value) == expected


@pytest.mark.parametrize("value", [True, 2.5, {"subject": None}, {"subject": "c1", "role": "admin"}, {"subject": "c1", "tenant": False}])
def test_principal_normalization_rejects_bad_identity(value):
    with pytest.raises(TypeError):
        principal_of(value)


@pytest.mark.parametrize("owner", [7.0, True])
def test_host_record_values_that_are_not_identifiers_match_nothing(owner):
    # JSON cannot carry this case to every SDK (JavaScript reads 7.0 as 7), so it is tested here only.
    subject = 1 if owner is True else 7
    decision = Ruleset(VECTORS["rulesets"]["helpdesk"]).evaluate(
        "get_note", {"note_id": "N"}, principal_of(subject), lambda resource, identifier: {"author_id": owner})
    assert decision.reason == "not_owner"
