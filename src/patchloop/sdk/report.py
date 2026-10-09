"""Summarize an SDK recordings file by tool and decision."""

import argparse
import json
from collections import Counter, defaultdict

COLUMNS = ("calls", "allow", "deny", "indeterminate", "blocked", "would_block", "errors")


def summarize(lines) -> dict:
    tools = defaultdict(Counter)
    reasons = defaultdict(Counter)
    rulesets = set()
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        tool, decision = record["tool"], record["decision"]
        counts = tools[tool]
        counts["calls"] += 1
        counts[decision["decision"]] += 1
        if record["outcome"] == "blocked":
            counts["blocked"] += 1
        elif decision["decision"] != "allow":
            counts["would_block"] += 1
        counts["errors"] += record["outcome"] == "error"
        if decision["decision"] != "allow":
            reasons[tool][decision["reason"]] += 1
        ruleset = record["ruleset"]
        rulesets.add(f"{ruleset['name']}@{ruleset['version']} ({ruleset['sha256'][:12]})")
    return {
        "rulesets": sorted(rulesets),
        "tools": {tool: {**{column: tools[tool][column] for column in COLUMNS}, "reasons": dict(reasons[tool])}
                  for tool in sorted(tools)},
        "unreviewed_tools": sorted(tool for tool in reasons if "unreviewed_tool" in reasons[tool]),
    }


def render(summary: dict) -> str:
    lines = [f"rule set: {name}" for name in summary["rulesets"]]
    width = max([len("tool"), *map(len, summary["tools"])])
    lines.append(f"{'tool':<{width}}  " + "  ".join(f"{column:>{len(column)}}" for column in COLUMNS))
    for tool, counts in summary["tools"].items():
        lines.append(f"{tool:<{width}}  " + "  ".join(f"{counts[column]:>{len(column)}}" for column in COLUMNS))
    not_allowed = [f"  {tool}: {reason} x{count}" for tool, counts in summary["tools"].items()
                   for reason, count in sorted(counts["reasons"].items())]
    if not_allowed:
        lines += ["not allowed:", *not_allowed]
    if summary["unreviewed_tools"]:
        lines.append("unreviewed tools (add them to the rule set): " + ", ".join(summary["unreviewed_tools"]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(prog="patchloop report", description=__doc__)
    parser.add_argument("recordings", help="JSONL file written by the SDK")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument("--strict", action="store_true", help="exit 1 when any call was not allowed (for CI)")
    options = parser.parse_args()
    try:
        with open(options.recordings, encoding="utf-8") as file:
            summary = summarize(file)
    except (OSError, ValueError, KeyError) as exc:
        print(f"patchloop report: cannot read {options.recordings}: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(summary, indent=2) if options.json else render(summary))
    not_allowed = any(counts["allow"] != counts["calls"] for counts in summary["tools"].values())
    return 1 if options.strict and not_allowed else 0
