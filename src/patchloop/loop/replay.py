"""Replay recorded tool calls against another rule set: what would it block, and what would it allow?

    patchloop replay calls.jsonl --rules rules.proposed.json

Facts come from the lookups saved in each recording, so no database access is needed. A call
whose facts or arguments were not recorded is reported as not replayable, never guessed.
Pass --facts module:attribute (for example myapp.agent:guard.facts) to use live facts instead,
which is needed when the earlier rules did not look the records up.
"""

import argparse
import json
import sys
from collections import Counter

from patchloop.loop.catalog import load_target
from patchloop.sdk.rules import Ruleset, RulesetError, argument_value, principal_of
from patchloop.sdk.runtime import _top_key

REDACTED = "[redacted]"
_GAP = ()  # Not a dict and not None, so evaluation treats it as unavailable without logging.


def _recorded_facts(lookups, rules, gaps):
    known = {(entry["resource"], json.dumps(entry["id"])): entry for entry in lookups}

    def facts(resource, identifier):
        entry = known.get((resource, json.dumps(identifier)))
        if entry is None or entry["status"] == "unavailable":
            gaps.append(f"{resource} {identifier!r} not recorded")
            return _GAP
        if entry["status"] == "missing":
            return None
        definition, record = rules.resources[resource], {}
        for key, field in (("owner", definition.get("owner_field")), ("tenant", definition.get("tenant_field")),
                           ("parent", (definition.get("parent") or {}).get("field"))):
            if field is None:
                continue
            if key not in entry:
                gaps.append(f"{resource} {identifier!r}: {key} not recorded")
                return _GAP
            record[field] = entry[key]
        return record
    return facts


def replay(lines, rules: Ruleset, facts=None) -> dict:
    """Compare each recorded decision with the decision `rules` gives for the same call."""
    counts, changes, skipped = Counter(), [], []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        record = json.loads(line)
        tool, arguments = record["tool"], record["arguments"]
        rule = rules.tools.get(tool) or {}
        redacted = [b["argument"] for b in rule.get("resources", [])
                    if argument_value(arguments, b["argument"]) == REDACTED or arguments.get(_top_key(b["argument"])) == REDACTED]
        if redacted:
            counts["not_replayable"] += 1
            skipped.append({"line": number, "tool": tool, "why": f"argument not recorded: {', '.join(redacted)}"})
            continue
        gaps = []
        lookup = facts or _recorded_facts(record["decision"]["lookups"], rules, gaps)
        new = rules.evaluate(tool, arguments, principal_of(record["principal"]), lookup, consent=record["consent"])
        if gaps:
            counts["not_replayable"] += 1
            skipped.append({"line": number, "tool": tool, "why": "; ".join(gaps)})
            continue
        old_allowed = record["decision"]["decision"] == "allow"
        category = ("unchanged" if old_allowed == new.allowed
                    else "newly_blocked" if old_allowed else "newly_allowed")
        counts[category] += 1
        if category != "unchanged":
            changes.append({"line": number, "tool": tool, "principal": record["principal"], "arguments": arguments,
                            "category": category, "before": record["decision"]["reason"], "after": new.reason})
    return {"rules": {"name": rules.name, "version": rules.version, "sha256": rules.sha256},
            "counts": {key: counts[key] for key in ("unchanged", "newly_blocked", "newly_allowed", "not_replayable")},
            "changes": changes, "not_replayable": skipped}


def render(result: dict) -> str:
    rules, counts = result["rules"], result["counts"]
    lines = [f"rule set {rules['name']}@{rules['version']} ({rules['sha256'][:12]})",
             "  ".join(f"{key}: {value}" for key, value in counts.items())]
    for change in result["changes"]:
        who = (change["principal"] or {}).get("subject")
        lines.append(f"  line {change['line']}: {change['category']} {change['tool']} as {who!r}: "
                     f"{change['before']} -> {change['after']}")
    for item in result["not_replayable"]:
        lines.append(f"  line {item['line']}: not replayable {item['tool']}: {item['why']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(prog="patchloop replay", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recordings", help="JSONL file written by the SDK")
    parser.add_argument("--rules", required=True, help="rule set to compare against")
    parser.add_argument("--facts", help="module:attribute giving live facts, for example myapp.agent:guard.facts")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--fail-on", default="", help="comma-separated categories that make the exit code 1, "
                        "for example newly_allowed,newly_blocked")
    options = parser.parse_args()
    try:
        rules = Ruleset.load(options.rules)
        facts = load_target(options.facts) if options.facts else None
        with open(options.recordings, encoding="utf-8") as file:
            result = replay(file, rules, facts)
    except (OSError, ValueError, KeyError, RulesetError, ImportError, AttributeError) as exc:
        print(f"patchloop replay: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if options.json else render(result))
    categories = list(filter(None, options.fail_on.split(",")))
    unknown = sorted(set(categories) - set(result["counts"]))
    if unknown:
        print(f"patchloop replay: unknown --fail-on categories {unknown}", file=sys.stderr)
        return 2
    failing = [key for key in categories if result["counts"][key]]
    return 1 if failing else 0
