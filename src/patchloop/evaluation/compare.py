"""Exploratory four-condition local pilot, with frozen cases and bounded calls.

Independent draws and feedback repair share generation temperature, candidate
limits, initial incident and private evaluator panels. Evaluation conversations
are frozen separately and never fed back to repair. This is not a final study.
"""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4

from patchloop.evaluation.campaign import BudgetedClient, run_campaign, scenarios
from patchloop.providers import NebiusClient
from patchloop.repair.loop import run_repair, write_json
from patchloop.repair.validation import create_suite
from patchloop.repair.versions import VersionStore


def run_comparison(output, model, *, client=None, count=1, turns=1, attempts=2, requests=80):
    if not 1 <= requests <= 120:
        raise ValueError("Comparison request cap must be 1–120")
    output.mkdir(parents=True, exist_ok=False)
    budget = BudgetedClient(client or NebiusClient(), requests=requests, tokens=400000)
    development = scenarios(secrets.token_bytes(32), count)
    evaluation = scenarios(secrets.token_bytes(32), count)
    write_json(output / "frozen-cases.json", {"development": development, "evaluation": evaluation})
    suite = create_suite(output)
    result = {"scope": "exploratory synthetic-retail pilot; no RL, transfer or statistical superiority claim",
        "evaluation_commitment": sha256(json.dumps(evaluation, sort_keys=True).encode()).hexdigest(),
        "candidate_limit": attempts, "temperature": .7, "turn_limit": turns,
        "request_limit": requests, "conditions": {}, "cost_usd": None,
        "cost_status": "provider prices not supplied; tokens and request IDs retained"}
    discovery = run_campaign(output / "discovery", budget, model, cases=development, turns=turns)
    result["discovery"] = {"status": discovery["status"], "unique_findings": discovery["unique_findings"]}
    incident = discovery["findings"][0] if discovery["status"] == "completed" and discovery["findings"] else None
    for condition in ("unrepaired", "independent", "feedback", "reference"):
        directory = output / condition
        directory.mkdir()
        record = {"repair": None}
        guard, reference = None, condition == "reference"
        if condition in {"independent", "feedback"}:
            if incident is None:
                record.update(status="not_run", reason="No complete discovered incident; no fixed-demo fallback")
                result["conditions"][condition] = record
                write_json(output / "report.json", result)
                continue
            store = directory / "versions"
            repaired = run_repair(directory / "repair", store, model, attempts,
                incident=incident, client=budget, strategy=condition, interface="adapter",
                validation_suite=suite, temperature=.7)
            record["repair"] = repaired
            guard = VersionStore(store).current_guard(default_interface="adapter")
        evaluated = run_campaign(directory / "evaluation", budget, model, cases=evaluation,
                                 guard=guard, reference=reference, turns=turns)
        record.update(status=evaluated["status"], evaluation=evaluated)
        result["conditions"][condition] = record
        write_json(output / "report.json", result)
    result.update(model_requests=budget.calls, total_tokens=budget.tokens, provider_records=budget.records,
                  usage_complete=all("total_tokens" in r.get("usage", {}) for r in budget.records))
    write_json(output / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.getenv("NEBIUS_MODEL", ""))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cases", type=int, default=1)
    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--requests", type=int, default=80)
    args = parser.parse_args()
    output = args.output or Path("artifacts/comparison") / uuid4().hex
    report = run_comparison(output, args.model, count=args.cases, turns=args.turns,
                            attempts=args.attempts, requests=args.requests)
    print(json.dumps({"report": str(output / "report.json"), "model_requests": report["model_requests"],
                      "conditions": {key: value["status"] for key, value in report["conditions"].items()}}))


if __name__ == "__main__":
    main()
