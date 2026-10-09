import asyncio
import json
import logging
import threading
from pathlib import Path

import jsonschema
import pytest

import patchloop
from patchloop import REFUSAL, Blocked, PatchLoop, Ruleset, identify
from patchloop.sdk import report, runtime

SPEC = Path(__file__).parents[1] / "spec"
RULES = {
    "schema_version": 1, "name": "notes", "version": "1",
    "resources": {"user": {"principal": True}, "note": {"owner_field": "owner"}},
    "tools": {
        "search": {"access": "public", "effect": "none"},
        "read_note": {"access": "scoped", "effect": "none", "resources": [{"argument": "note_id", "resource": "note"}]},
        "delete_note": {"access": "scoped", "effect": "state_write", "consent": True,
                        "resources": [{"argument": "note_id", "resource": "note"}]},
        "refund": {"access": "scoped", "effect": "state_write", "consent": True,
                   "resources": [{"argument": "note_id", "resource": "note"}]},
        "profile": {"access": "scoped", "effect": "none", "resources": [{"argument": "user_id", "resource": "user"}]},
        "send_report": {"access": "authenticated", "effect": "external", "consent": True},
    },
}


class App:
    def __init__(self):
        self.notes = {"n1": {"owner": "ada", "text": "mine"}, "n2": {"owner": "bo", "text": "secret"}}
        self.ran = []

    def facts(self, resource, identifier):
        return self.notes.get(identifier) if resource == "note" else None


def protected(tmp_path, **options):
    app = App()
    guard = PatchLoop(Ruleset(RULES), facts=app.facts, recordings=tmp_path / "calls.jsonl", **options)

    @guard.tool
    def read_note(note_id: str):
        app.ran.append(("read_note", note_id))
        return app.notes[note_id]["text"]

    @guard.tool
    def delete_note(note_id: str):
        app.ran.append(("delete_note", note_id))
        return app.notes.pop(note_id)["text"]

    @guard.tool(name="search")
    def search_notes(query: str, limit: int = 5):
        app.ran.append(("search", query))
        return []

    return app, guard, {"read_note": read_note, "delete_note": delete_note, "search": search_notes}


def recordings(tmp_path):
    return [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]


def test_enforce_blocks_before_the_tool_runs_with_a_uniform_message(tmp_path):
    app, _, tools = protected(tmp_path, mode="enforce")
    with identify("ada"):
        assert tools["read_note"]("n1") == "mine"
        messages = set()
        for note_id in ("n2", "missing"):
            with pytest.raises(Blocked) as blocked:
                tools["read_note"](note_id=note_id)
            messages.add(str(blocked.value))
    assert messages == {REFUSAL}
    assert blocked.value.decision.reason == "resource_missing"
    assert app.ran == [("read_note", "n1")]
    lines = recordings(tmp_path)
    assert [(line["outcome"], line["decision"]["reason"]) for line in lines] == [
        ("ok", "authorized"), ("blocked", "not_owner"), ("blocked", "resource_missing")]


def test_identity_is_per_context_and_absent_outside_identify(tmp_path):
    app, guard, tools = protected(tmp_path, mode="enforce")
    with pytest.raises(Blocked) as blocked:
        tools["read_note"]("n1")
    assert blocked.value.decision.reason == "authentication_required"
    with identify("bo", tenant="acme"):
        with identify("ada"):
            assert guard.check("read_note", {"note_id": "n1"}).allowed
        assert guard.check("read_note", {"note_id": "n2"}).allowed
    results = {}

    def worker(user):
        with identify(user):
            results[user] = guard.check("read_note", {"note_id": "n1"}).allowed
    threads = [threading.Thread(target=worker, args=(user,)) for user in ("ada", "bo")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == {"ada": True, "bo": False}


def test_observe_runs_everything_and_records_what_enforce_would_block(tmp_path):
    _, _, tools = protected(tmp_path)
    assert tools["read_note"]("n2") == "secret"
    line = recordings(tmp_path)[0]
    assert (line["decision"]["reason"], line["mode"], line["executed"], line["outcome"]) == (
        "authentication_required", "observe", True, "ok")


def test_warn_runs_logs_and_notifies(tmp_path, caplog):
    seen = []
    _, _, tools = protected(tmp_path, mode="warn", on_violation=seen.append)
    with identify("ada"), caplog.at_level(logging.WARNING, logger="patchloop"):
        assert tools["read_note"]("n2") == "secret"
    assert [decision.reason for decision in seen] == ["not_owner"]
    assert "read_note would be blocked" in caplog.text


def test_failing_violation_hook_does_not_change_the_call(tmp_path):
    def broken(decision):
        raise RuntimeError("alerting is down")
    _, _, tools = protected(tmp_path, mode="enforce", on_violation=broken)
    with identify("ada"), pytest.raises(Blocked):
        tools["read_note"]("n2")


def test_per_tool_mode_overrides_default(tmp_path):
    app, _, tools = protected(tmp_path, mode="observe", modes={"delete_note": "enforce"})
    with identify("ada"):
        assert tools["read_note"]("n2") == "secret"
        with pytest.raises(Blocked):
            tools["delete_note"]("n2")
    assert "n2" in app.notes


def test_consent_is_single_use_bound_to_user_arguments_and_expiry(tmp_path):
    app, guard, _ = protected(tmp_path, mode="enforce")
    refunds = []
    refund = guard.tool(lambda note_id: refunds.append(note_id) or "refunded", name="refund")
    with identify("ada"):
        with pytest.raises(Blocked) as blocked:
            refund("n1")
        assert blocked.value.decision.reason == "consent_required"
        guard.confirm("refund", {"note_id": "n1"})
        assert guard.check("refund", {"note_id": "n1"}).allowed
        assert guard.check("refund", {"note_id": "n1"}).allowed, "check() must not use up consent"
        assert refund("n1") == "refunded"
        with pytest.raises(Blocked):
            refund("n1")
        guard.confirm("refund", {"note_id": "n1"}, ttl=-1)
        with pytest.raises(Blocked):
            refund("n1")
        guard.confirm("refund", {"note_id": "n1"})
    app.notes["n3"] = {"owner": "bo"}
    with identify("bo"):
        assert guard.check("refund", {"note_id": "n1"}).reason == "not_owner"
    assert refunds == ["n1"]
    assert recordings(tmp_path)[1]["consent"] is True


def test_consent_is_bound_to_the_user_who_gave_it_and_check_sees_expiry(tmp_path):
    _, guard, _ = protected(tmp_path)
    with identify("ada"):
        guard.confirm("send_report", {"to": "team"})
        guard.confirm("delete_note", {"note_id": "n1"}, ttl=-1)
        assert guard.check("delete_note", {"note_id": "n1"}).reason == "consent_required"
    with identify("bo"):
        assert guard.check("send_report", {"to": "team"}).reason == "consent_required"
    with identify("ada"):
        assert guard.check("send_report", {"to": "team"}).allowed


def test_consent_used_up_between_check_and_run_blocks(tmp_path):
    class RacedStore:
        def grant(self, key, ttl=None): ...
        def has(self, key): return True
        def take(self, key): return False

    ran = []
    guard = PatchLoop(Ruleset(RULES), facts=App().facts, mode="enforce", consents=RacedStore())
    send = guard.tool(lambda to: ran.append(to), name="send_report")
    with identify("ada"):
        assert guard.check("send_report", {"to": "team"}).allowed
        with pytest.raises(Blocked) as blocked:
            send("team")
    assert blocked.value.decision.reason == "consent_required" and ran == []


def test_consent_matches_arguments_after_defaults(tmp_path):
    _, guard, _ = protected(tmp_path, mode="enforce")
    sent = []

    @guard.tool(name="refund")
    def refund(note_id: str, notify: bool = True):
        sent.append((note_id, notify))
        return "refunded"

    with identify("ada"):
        guard.confirm("refund", {"note_id": "n1"})
        with pytest.raises(Blocked):
            refund("n1", notify=False)
        assert refund("n1") == "refunded"
    assert sent == [("n1", True)]


def test_confirm_needs_a_logged_in_user(tmp_path):
    _, guard, _ = protected(tmp_path)
    with pytest.raises(ValueError):
        guard.confirm("refund", {"note_id": "n1"})


def test_tools_taking_kwargs_and_duplicate_names_are_refused(tmp_path):
    _, guard, _ = protected(tmp_path)
    with pytest.raises(TypeError):
        guard.tool(lambda **kwargs: None, name="profile")

    class Tickets:
        def delete_note(self, note_id): ...
    with pytest.raises(ValueError):
        guard.tool(Tickets().delete_note)


def test_tool_errors_are_recorded_by_type_only_and_re_raised(tmp_path):
    app, _, tools = protected(tmp_path, mode="enforce")
    app.notes["n3"] = {"owner": "ada"}
    with identify("ada"), pytest.raises(KeyError):
        tools["read_note"]("n3")
    line = recordings(tmp_path)[0]
    assert (line["outcome"], line["error"]) == ("error", "KeyError")


def test_recordings_keep_bound_and_identifier_arguments_by_default(tmp_path):
    _, guard, tools = protected(tmp_path)
    tools["search"]("private words")
    with identify("ada"):
        tools["read_note"]("n1")
    lines = recordings(tmp_path)
    assert lines[0]["arguments"] == {"query": "[redacted]", "limit": "[redacted]"}
    assert lines[1]["arguments"] == {"note_id": "n1"}
    log = guard.tool(lambda password, order_id, item_ids, customerId, valid, user_id: 1, name="log_in")
    log("hunter2", "o1", ["i1", 2], 7, "x", {"nested": "secret"})
    assert recordings(tmp_path)[2]["arguments"] == {"password": "[redacted]", "order_id": "o1", "item_ids": ["i1", 2],
                                                    "customerId": 7, "valid": "[redacted]", "user_id": "[redacted]"}
    assert tools["search"].__name__ == "search_notes"


def test_custom_redaction_and_recording_failure_never_change_the_result(tmp_path):
    app = App()
    everything = PatchLoop(Ruleset(RULES), facts=app.facts, recordings=tmp_path / "calls.jsonl",
                           redact=lambda tool, arguments: arguments)
    everything.tool(lambda query: "found", name="search")("words")
    assert recordings(tmp_path)[0]["arguments"] == {"query": "words"}
    unwritable = PatchLoop(Ruleset(RULES), facts=app.facts, recordings=tmp_path)
    assert unwritable.tool(lambda query: "found", name="search")("x") == "found"


def test_unreviewed_tool_is_blocked_in_enforce(tmp_path):
    _, guard, _ = protected(tmp_path, mode="enforce")

    @guard.tool
    def export_everything():
        raise AssertionError("must not run")

    assert guard.unreviewed() == ["export_everything"]
    with pytest.raises(Blocked) as blocked:
        export_everything()
    assert blocked.value.decision.reason == "unreviewed_tool"


def test_async_tools_use_async_facts(tmp_path):
    app = App()

    async def facts(resource, identifier):
        await asyncio.sleep(0)
        return app.notes.get(identifier)

    guard = PatchLoop(Ruleset(RULES), facts=facts, mode="enforce")

    @guard.tool
    async def read_note(note_id):
        return app.notes[note_id]["text"]

    async def main():
        with identify("ada"):
            assert await read_note("n1") == "mine"
            assert (await guard.acheck("read_note", {"note_id": "n2"})).reason == "not_owner"
            with pytest.raises(Blocked):
                await read_note("n2")
    asyncio.run(main())


def test_bad_mode_and_bad_identity_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        PatchLoop(Ruleset(RULES), facts=lambda *_: None, mode="block")
    app, _, tools = protected(tmp_path, mode="enforce", identity=lambda: True)
    with pytest.raises(TypeError):
        tools["read_note"]("n1")
    assert app.ran == []


def test_doctor_reports_gaps(tmp_path):
    app = App()
    guard = PatchLoop(Ruleset(RULES), facts=app.facts)
    guard.tool(lambda id: None, name="read_note")
    guard.tool(lambda: None, name="export_everything")
    problems = guard.doctor(tools={"search": ["query"]})
    assert "mode is observe: calls are recorded but nothing is blocked" in problems
    assert "export_everything: not in the rule set, so every call is indeterminate" in problems
    assert any(p.startswith("read_note: binding argument 'note_id' is not a parameter") for p in problems)
    assert "profile: in the rule set but not registered (check the spelling)" in problems
    assert not any(p.startswith("delete_note: effect") for p in problems)
    assert not any(p.startswith("send_report: effect") for p in problems)


def test_module_level_api(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "_client", None)
    with pytest.raises(RuntimeError):
        patchloop.tool(lambda note_id: None, name="read_note")
    app = App()
    patchloop.init(Ruleset(RULES), facts=app.facts, mode="enforce")

    @patchloop.tool
    def read_note(note_id: str):
        return app.notes[note_id]["text"]

    with identify("ada"):
        assert read_note("n1") == "mine"
        assert patchloop.check("read_note", {"note_id": "n2"}).reason == "not_owner"
        patchloop.confirm("delete_note", {"note_id": "n1"})
        assert patchloop.check("delete_note", {"note_id": "n1"}).allowed
    assert "profile: in the rule set but not registered (check the spelling)" in patchloop.doctor()


def test_recording_lines_and_rule_sets_follow_the_published_schemas(tmp_path):
    _, guard, tools = protected(tmp_path, mode="enforce")
    with identify("ada", tenant="t1"):
        tools["read_note"]("n1")
        with pytest.raises(Blocked):
            tools["delete_note"]("n2")
    recording_schema = json.loads((SPEC / "schemas/recording.schema.json").read_text())
    for line in recordings(tmp_path):
        jsonschema.validate(line, recording_schema)
    ruleset_schema = json.loads((SPEC / "schemas/ruleset.schema.json").read_text())
    vectors = json.loads((SPEC / "conformance/decisions.json").read_text())
    for ruleset in [RULES, *vectors["rulesets"].values()]:
        jsonschema.validate(ruleset, ruleset_schema)


def test_report_counts_decisions_per_tool(tmp_path, capsys, monkeypatch):
    _, _, tools = protected(tmp_path)
    with identify("ada"):
        tools["read_note"]("n1")
        tools["read_note"]("n2")
    _, guard, _ = protected(tmp_path)
    guard.tool(lambda: None, name="export_everything")()
    with open(tmp_path / "calls.jsonl") as file:
        summary = report.summarize(file)
    assert summary["tools"]["read_note"] == {"calls": 2, "allow": 1, "deny": 1, "indeterminate": 0, "blocked": 0,
                                             "would_block": 1, "errors": 0, "reasons": {"not_owner": 1}}
    assert summary["unreviewed_tools"] == ["export_everything"]
    monkeypatch.setattr("sys.argv", ["patchloop report", str(tmp_path / "calls.jsonl"), "--strict"])
    assert report.main() == 1
    assert "not_owner x1" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["patchloop report", str(tmp_path / "missing.jsonl")])
    assert report.main() == 2


def test_observers_see_every_call_without_a_file_and_cannot_break_it():
    app = App()
    guard = PatchLoop(Ruleset(RULES), facts=app.facts)
    seen = []
    unsubscribe = guard.subscribe(seen.append)
    guard.subscribe(lambda line: 1 / 0)
    search = guard.tool(lambda query: "found", name="search")
    assert search("x") == "found"
    unsubscribe()
    search("y")
    assert [(line["tool"], line["outcome"]) for line in seen] == [("search", "ok")]
