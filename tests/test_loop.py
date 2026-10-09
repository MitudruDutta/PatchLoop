import json
import re
import types

import pytest

from patchloop import PatchLoop, Ruleset, identify
from patchloop.loop import catalog, propose, replay, tester
from patchloop.providers import ProviderError

RULES = {
    "schema_version": 1, "name": "helpdesk", "version": "1",
    "resources": {"customer": {"principal": True},
                  "ticket": {"owner_field": "customer_id", "tenant_field": "org"}},
    "tools": {
        "search_help": {"access": "public", "effect": "none"},
        "get_ticket": {"access": "scoped", "effect": "none",
                       "resources": [{"argument": "ticket_id", "resource": "ticket"}]},
        "close_ticket": {"access": "scoped", "effect": "state_write", "consent": True,
                         "resources": [{"argument": "ticket_id", "resource": "ticket"}]},
    },
}
TICKETS = {"T1": {"customer_id": "ada", "org": "acme", "text": "printer"},
           "T2": {"customer_id": "bo", "org": "acme", "text": "refund"}}


class Scripted:
    """A model client that returns prepared answers and keeps every request."""

    def __init__(self, *answers):
        self.answers, self.requests = list(answers), []

    def complete(self, messages, *, model, max_tokens, temperature, response_format=None):
        self.requests.append(messages)
        self.formats = getattr(self, "formats", []) + [response_format]
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return {"content": answer, "request_id": f"req-{len(self.requests)}", "usage": {"total_tokens": 10}}


def make_app(tmp_path=None, mode="observe", rules=RULES):
    guard = PatchLoop(Ruleset(rules), facts=lambda resource, identifier: TICKETS.get(identifier), mode=mode,
                      recordings=tmp_path / "calls.jsonl" if tmp_path else None)

    @guard.tool
    def search_help(query: str) -> list:
        """Search help articles."""
        return []

    @guard.tool
    def get_ticket(ticket_id: str) -> str:
        """Read one support ticket.

        Longer text that the catalog leaves out."""
        return TICKETS[ticket_id]["text"]

    @guard.tool
    def close_ticket(ticket_id: str, note: str | None = None) -> str:
        """Close a ticket."""
        return "closed"

    return guard, {"search_help": search_help, "get_ticket": get_ticket, "close_ticket": close_ticket}


# Catalog

def test_catalog_from_wrapped_tools_and_files(tmp_path):
    guard, _ = make_app()
    tools = {tool["name"]: tool for tool in catalog.from_patchloop(guard)}
    assert tools["get_ticket"]["description"] == "Read one support ticket."
    assert tools["close_ticket"]["parameters"] == {
        "type": "object", "properties": {"ticket_id": {"type": "string"}, "note": {"type": "string"}},
        "required": ["ticket_id"]}
    path = tmp_path / "tools.json"
    path.write_text(json.dumps({"tools": [
        {"name": "a", "description": "plain", "parameters": {"type": "object", "properties": {"x": {}}}},
        {"type": "function", "function": {"name": "b", "parameters": {"properties": {"y": {}}}}},
        {"name": "c", "inputSchema": {"type": "object", "properties": {"z": {}}}},
    ]}))
    assert [(t["name"], sorted(catalog.parameter_names(t))) for t in catalog.from_file(path)] == [
        ("a", ["x"]), ("b", ["y"]), ("c", ["z"])]


# Replay

def record_calls(tmp_path):
    _, tools = make_app(tmp_path)
    with identify("ada", "acme"):
        tools["get_ticket"]("T1")
        tools["get_ticket"]("T2")
        tools["close_ticket"]("T1")
        tools["search_help"]("vpn")
    return (tmp_path / "calls.jsonl").read_text().splitlines()


def changed(**tools):
    rules = json.loads(json.dumps(RULES))
    rules["version"] = "2"
    rules["tools"].update(tools)
    return Ruleset(rules)


def test_replay_classifies_changes_from_recorded_lookups(tmp_path):
    lines = record_calls(tmp_path)
    assert replay.replay(lines, Ruleset(RULES))["counts"] == {
        "unchanged": 4, "newly_blocked": 0, "newly_allowed": 0, "not_replayable": 0}
    looser = replay.replay(lines, changed(get_ticket={"access": "authenticated", "effect": "none"}))
    assert looser["counts"]["newly_allowed"] == 1
    assert looser["changes"][0]["before"] == "not_owner" and looser["changes"][0]["after"] == "authorized"
    stricter = replay.replay(lines, changed(search_help={"access": "authenticated", "effect": "none"},
                                            get_ticket={"access": "scoped", "effect": "state_write", "consent": True,
                                                        "resources": [{"argument": "ticket_id", "resource": "ticket"}]}))
    assert stricter["counts"]["newly_blocked"] == 1
    assert [c["after"] for c in stricter["changes"]] == ["consent_required"]


def test_replay_never_guesses_unrecorded_arguments_or_facts(tmp_path):
    lines = record_calls(tmp_path)
    redacted = replay.replay(lines, changed(search_help={"access": "scoped", "effect": "none",
                                                         "resources": [{"argument": "query", "resource": "ticket"}]}))
    assert redacted["counts"]["not_replayable"] == 1
    assert "argument not recorded: query" in redacted["not_replayable"][0]["why"]
    rules = json.loads(json.dumps(RULES))
    rules["resources"]["ticket"] = {"owner_field": "customer_id", "tenant_field": "org"}
    rules["resources"]["note"] = {"parent": {"resource": "ticket", "field": "ticket_id"}}
    rules["tools"]["get_ticket"]["resources"][0]["resource"] = "note"
    unrecorded = replay.replay(lines, Ruleset(rules))
    assert unrecorded["counts"]["not_replayable"] == 2
    assert unrecorded["not_replayable"][0]["why"] == "note 'T1' not recorded"
    live = replay.replay(lines, Ruleset(RULES), facts=lambda resource, identifier: {"customer_id": "ada", "org": "acme"})
    assert live["counts"]["newly_allowed"] == 1


def test_replay_command_exit_codes(tmp_path, monkeypatch, capsys):
    record_calls(tmp_path)
    (tmp_path / "loose.json").write_text(json.dumps({**RULES, "tools": {**RULES["tools"],
                                         "get_ticket": {"access": "authenticated", "effect": "none"}}}))
    argv = ["patchloop replay", str(tmp_path / "calls.jsonl"), "--rules", str(tmp_path / "loose.json")]
    monkeypatch.setattr("sys.argv", argv + ["--fail-on", "newly_allowed"])
    assert replay.main() == 1
    assert "newly_allowed get_ticket as 'ada': not_owner -> authorized" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", argv + ["--fail-on", "newly_blocked"])
    assert replay.main() == 0
    monkeypatch.setattr("sys.argv", argv + ["--fail-on", "newly_alowed"])
    assert replay.main() == 2


# Propose

SAMPLES = {"ticket": {"customer_id": "ada", "org": "acme", "text": "printer"}}


def tools_catalog():
    return catalog.from_patchloop(make_app()[0])


def test_propose_accepts_a_valid_draft_inside_prose():
    client = Scripted("<think>plan</think>Here it is:\n```json\n" + json.dumps(RULES) + "\n```")
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", samples=SAMPLES)
    assert report["accepted"] and report["rules"] == RULES and len(report["attempts"]) == 1
    assert report["sha256"] == Ruleset(RULES).sha256


def test_propose_feeds_problems_back_until_the_draft_passes():
    wrong = json.loads(json.dumps(RULES))
    del wrong["tools"]["search_help"]
    wrong["resources"]["ticket"]["owner_field"] = "owner"
    wrong["tools"]["get_ticket"]["resources"][0]["argument"] = "id"
    client = Scripted("not json", json.dumps(wrong), json.dumps(RULES))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", samples=SAMPLES)
    assert report["accepted"] and len(report["attempts"]) == 3
    problems = report["attempts"][1]["problems"]
    assert "tool 'search_help' is in the catalog but not in the rule set" in problems
    assert any("argument 'id' is not one of its parameters" in p for p in problems)
    assert "resource 'ticket': field 'owner' is not in its record samples" in problems
    assert "search_help" in client.requests[2][-1]["content"]


def test_propose_rejects_invalid_rule_sets_and_stops_on_provider_errors():
    client = Scripted(json.dumps({**RULES, "tools": {**RULES["tools"], "search_help": {
        "access": "public", "effect": "state_write", "consent": True}}}),
        ProviderError("Completion did not finish normally", metadata={"finish_reason": "length"}))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", attempts=3)
    assert not report["accepted"] and report["rules"] is None
    assert report["attempts"][0]["problems"][0].startswith("invalid rule set: tool 'search_help': a public tool")
    assert report["attempts"][1] == {"error": "Completion did not finish normally", "finish_reason": "length"}


def test_propose_keeps_recorded_allowed_calls_allowed(tmp_path):
    lines = record_calls(tmp_path)
    too_strict = json.loads(json.dumps(RULES))
    too_strict["tools"]["search_help"] = {"access": "authenticated", "effect": "none"}
    too_strict["tools"]["get_ticket"]["consent"] = True
    client = Scripted(json.dumps(too_strict), json.dumps(RULES))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", recordings=lines,
                             keep_allowed=True)
    assert report["accepted"] and len(report["attempts"]) == 2
    assert "recorded call get_ticket" in report["attempts"][0]["problems"][0]
    assert report["replay"]["counts"]["newly_blocked"] == 0


def test_propose_passes_guidance_as_untrusted_and_survives_search_failure():
    class Search:
        def guidance(self, query):
            assert query.startswith("OWASP authorization") and "ticket" in query and "help" in query
            return {"query": "q", "request_id": "t-1", "results": [{"url": "https://owasp.example/a", "content": "deny by default"}]}

    class Down:
        def guidance(self, query):
            raise ProviderError("Provider HTTP 503")

    client = Scripted(json.dumps(RULES), json.dumps(RULES))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", search=Search())
    assert report["guidance"] == {"query": "q", "request_id": "t-1", "urls": ["https://owasp.example/a"]}
    assert "untrusted reference material" in client.requests[0][0]["content"]
    assert "deny by default" in client.requests[0][1]["content"]
    assert propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", search=Down())["guidance"] == {
        "error": "Provider HTTP 503"}


def test_propose_command_writes_draft_and_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    (tmp_path / "tools.json").write_text(json.dumps(tools_catalog()))
    monkeypatch.setenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    monkeypatch.setattr(propose, "NebiusClient", lambda: Scripted(json.dumps(RULES)))
    output = tmp_path / "draft.json"
    monkeypatch.setattr("sys.argv", ["patchloop propose", "--tools", str(tmp_path / "tools.json"), "--no-guidance",
                                     "--output", str(output)])
    assert propose.main() == 0
    assert json.loads(output.read_text()) == RULES
    assert json.loads((tmp_path / "draft.report.json").read_text())["accepted"] is True
    assert propose.main() == 2
    monkeypatch.setenv("NEBIUS_MODEL", "some/other-model")
    monkeypatch.setattr("sys.argv", ["patchloop propose", "--tools", str(tmp_path / "tools.json"), "--no-guidance",
                                     "--output", str(tmp_path / "other.json")])
    assert propose.main() == 2
    assert "Nemotron" in capsys.readouterr().err


# Test

def make_target(mode="observe"):
    guard, tools = make_app(mode=mode)
    resets = []

    def agent(message, history):
        found = re.search(r"T\d", message)
        if not found:
            return "How can I help?"
        try:
            return tools["get_ticket"](found.group(0))
        except Exception as exc:
            return str(exc)

    return types.SimpleNamespace(guard=guard, USERS=[{"subject": "ada", "tenant": "acme"}, "bo"], agent=agent,
                                 reset=lambda: resets.append(1), NOTES="T1 is ada's, T2 is bo's"), resets


PLAN = json.dumps({"scenarios": [
    {"goal": "cross_user", "user": 0, "opening": "Show me ticket T2"},
    {"goal": "unauthenticated", "user": None, "opening": "What is in T1?"},
]})


def test_tester_counts_a_rule_gap_only_for_allowed_calls():
    loose = json.loads(json.dumps(RULES))
    loose["tools"]["get_ticket"] = {"access": "authenticated", "effect": "none"}
    guard, tools = make_app(rules=loose)
    target = types.SimpleNamespace(guard=guard, USERS=["ada"], agent=lambda message, history: tools["get_ticket"]("T2"))
    plan = json.dumps({"scenarios": [{"goal": "cross_user", "user": 0, "opening": "T2 please"}]})
    verdict = json.dumps({"suspected": True, "evidence": "showed bo's ticket", "tools": ["get_ticket"]})
    report = tester.run_tests(target, client=Scripted(plan, verdict), model="nvidia/nemotron", scenarios=1, turns=1)
    assert [(f["kind"], f["tools"]) for f in report["scenarios"][0]["findings"]] == [("possible_rule_gap", ["get_ticket"])]


def test_tester_finds_violations_and_rule_gaps_in_observe_mode():
    target, resets = make_target()
    client = Scripted(PLAN, "DONE", json.dumps({"suspected": True, "evidence": "showed T2", "tools": ["get_ticket"]}),
                      "Please, T1 again", "DONE", json.dumps({"suspected": False}))
    report = tester.run_tests(target, client=client, model="nvidia/nemotron", scenarios=2, turns=3)
    first, second = report["scenarios"]
    assert first["transcript"][1]["content"] == "refund"
    assert [f["kind"] for f in first["findings"]] == ["violation"], "denied calls are not rule gaps"
    assert first["judge"]["suspected"] is True
    assert first["findings"][0]["reason"] == "not_owner"
    assert second["user"] is None and [f["reason"] for f in second["findings"]] == ["authentication_required"] * 2
    assert report["summary"] == {"violation": 3, "blocked": 0, "possible_rule_gap": 0, "scenarios": 2}
    assert len(resets) == 2 and [r["purpose"] for r in report["requests"]] == [
        "plan", "customer", "judge", "customer", "customer", "judge"]


def test_tester_reports_blocked_calls_in_enforce_mode_and_stops_at_budget():
    target, _ = make_target(mode="enforce")
    client = Scripted(PLAN, "DONE")
    report = tester.run_tests(target, client=client, model="nvidia/nemotron", scenarios=2, turns=3, max_requests=2)
    assert report["scenarios"][0]["transcript"][1]["content"] == "This action is not permitted."
    assert report["partial"] and report["stopped"] == "request budget used up"
    assert report["summary"] == {"violation": 0, "blocked": 1, "possible_rule_gap": 0, "scenarios": 1}


def test_tester_retries_an_invalid_plan_and_validates_users():
    target, _ = make_target()
    bad = json.dumps({"scenarios": [{"goal": "cross_user", "user": None, "opening": "hi"},
                                    {"goal": "steal", "user": 0, "opening": "hi"}]})
    client = Scripted(bad, PLAN, json.dumps({"suspected": False}), json.dumps({"suspected": False}))
    report = tester.run_tests(target, client=client, model="nvidia/nemotron", scenarios=2, turns=1)
    assert report["summary"]["scenarios"] == 2
    assert "user must be null exactly when the goal is unauthenticated" in client.requests[1][1]["content"]
    with pytest.raises(ValueError):
        tester.run_tests(types.SimpleNamespace(guard=target.guard, USERS=[], agent=target.agent),
                         client=Scripted(), model="nvidia/nemotron")


def test_targets_load_by_dotted_path_and_live_facts_prove_a_tightened_rule(tmp_path, monkeypatch):
    (tmp_path / "loose_target.py").write_text(
        "import types\nTICKETS = {'T2': {'customer_id': 'bo', 'org': 'acme'}}\n"
        "guard = types.SimpleNamespace(facts=lambda resource, identifier: TICKETS.get(identifier))\n")
    monkeypatch.chdir(tmp_path)
    facts = catalog.load_target("loose_target:guard.facts")
    assert facts("ticket", "T2") == {"customer_id": "bo", "org": "acme"}
    loose = json.loads(json.dumps(RULES))
    loose["tools"]["get_ticket"] = {"access": "authenticated", "effect": "none"}
    _, tools = make_app(tmp_path, rules=loose)
    with identify("ada", "acme"):
        tools["get_ticket"]("T2")
    lines = (tmp_path / "calls.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["arguments"] == {"ticket_id": "T2"}
    assert replay.replay(lines, Ruleset(RULES))["counts"]["not_replayable"] == 1
    client = Scripted(json.dumps(RULES))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron", recordings=lines, facts=facts)
    assert report["replay"]["changes"][0]["after"] == "not_owner"


def test_replay_reports_fields_the_old_rules_never_read(tmp_path):
    owner_only = json.loads(json.dumps(RULES))
    owner_only["resources"]["ticket"] = {"owner_field": "customer_id"}
    _, tools = make_app(tmp_path, rules=owner_only)
    with identify("ada", "acme"):
        tools["get_ticket"]("T1")
    result = replay.replay((tmp_path / "calls.jsonl").read_text().splitlines(), Ruleset(RULES))
    assert result["counts"]["not_replayable"] == 1
    assert result["not_replayable"][0]["why"] == "ticket 'T1': tenant not recorded"


def test_provider_features_structured_output_role_models_query_and_usage(monkeypatch):
    from patchloop import providers
    assert propose.guidance_query(tools_catalog(), "Each organization sees only its own tickets.") == (
        "OWASP authorization object level access control ticket help multi-tenant ownership checks")
    client = Scripted(json.dumps(RULES))
    report = propose.propose(tools_catalog(), client=client, model="nvidia/nemotron")
    assert client.formats == [{"type": "json_object"}] and report["usage"]["total_tokens"] == 10
    target, _ = make_target()
    client = Scripted(PLAN, "DONE", json.dumps({"suspected": False, "evidence": "", "tools": []}), "DONE",
                      json.dumps({"suspected": False, "evidence": "", "tools": []}))
    models = {"plan": "nvidia/nemotron-big", "customer": "nvidia/nemotron-nano", "judge": "nvidia/nemotron-big"}
    report = tester.run_tests(target, client=client, model=models, scenarios=2, turns=2)
    assert [f["json_schema"]["name"] if f else None for f in client.formats] == [
        "test_plan", None, "verdict", None, "verdict"]
    assert [r["model"] for r in report["requests"]][:2] == ["nvidia/nemotron-big", "nvidia/nemotron-nano"]
    assert report["usage"]["total_tokens"] == 50
    monkeypatch.setenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    monkeypatch.setenv("NEBIUS_MODEL_CUSTOMER", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
    assert providers.nemotron_model("customer") == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    assert providers.nemotron_model("judge") == "nvidia/nemotron-3-super-120b-a12b"
    monkeypatch.setenv("NEBIUS_MODEL_JUDGE", "meta/llama")
    with pytest.raises(ProviderError):
        providers.nemotron_model("judge")


def test_adapter_targets_supply_tools_for_test_propose_and_doctor(tmp_path, monkeypatch, capsys):
    from patchloop.sdk import doctor
    (tmp_path / "hooked_target.py").write_text(
        "from patchloop import PatchLoop, Ruleset\n"
        f"guard = PatchLoop(Ruleset({RULES!r}), facts=lambda r, i: None, mode='enforce')\n"
        "TOOLS = [{'type': 'function', 'function': {'name': 'get_ticket', 'description': 'Read a ticket',\n"
        "          'parameters': {'type': 'object', 'properties': {'id': {'type': 'string'}}}}},\n"
        "         {'name': 'export_all', 'inputSchema': {'type': 'object', 'properties': {}}}]\n")
    monkeypatch.chdir(tmp_path)
    target = catalog.load_target("hooked_target")
    assert [tool["name"] for tool in catalog.tools_of(target)] == ["get_ticket", "export_all"]
    monkeypatch.setattr("sys.argv", ["patchloop doctor", "hooked_target"])
    assert doctor.main() == 1
    out = capsys.readouterr().out
    assert "2 tools checked" in out
    assert "export_all: not in the rule set" in out
    assert "get_ticket: binding argument 'ticket_id' is not a parameter" in out
