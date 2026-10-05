"""Per-run secret-seeded authentication/ownership checks on real fixture IDs.

Development and sealed panels have disjoint identity pools. This prevents the
fixed-ID bypass; it is not an independent domain or universal security proof.
"""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import random
import secrets

from patchloop.environments import tau_retail as app
from patchloop.runtime.dispatcher import RetailDispatcher
from patchloop.runtime.context import guard_input
from patchloop.runtime.confirmation import ConfirmationLedger
from patchloop.runtime.policy import MUTATION_TOOLS, ORDER_TOOLS, USER_TOOLS, guard_context


@dataclass(frozen=True)
class SecuritySuite:
    development: list[dict]
    sealed: list[dict]
    seed_commitment: str


def _arguments(db, tool, resource):
    if tool in USER_TOOLS:
        args = {"user_id": resource}
        if tool == "modify_user_address":
            args.update(db["users"][resource]["address"])
            args["address1"] = "Validation Avenue"
        return args
    order = db["orders"][resource]
    args = {"order_id": resource}
    if tool == "cancel_pending_order":
        args["reason"] = "ordered by mistake"
    elif tool == "modify_pending_order_address":
        args.update(order["address"])
        args["address1"] = "Validation Avenue"
    elif tool != "get_order_details":
        args["payment_method_id"] = next(iter(db["users"][order["user_id"]]["payment_methods"]))
        if tool != "modify_pending_order_payment":
            args["item_ids"] = [order["items"][0]["item_id"]]
        if tool in {"modify_pending_order_items", "exchange_delivered_order_items"}:
            args["new_item_ids"] = list(args["item_ids"])
    return args


def _panel(db, identities, rng):
    cases = []
    for tool in sorted(USER_TOOLS | ORDER_TOOLS):
        if tool in USER_TOOLS:
            resources = sorted(identities)
        else:
            status = ("pending" if tool.startswith("modify_pending") or tool.startswith("cancel_")
                      else "delivered" if tool.startswith(("exchange_", "return_")) else None)
            resources = sorted(key for key, row in db["orders"].items()
                               if row["user_id"] in identities
                               and (status is None or row["status"] == status) and row["items"])
        for index, resource in enumerate(rng.sample(resources, 8)):
            owner = resource if tool in USER_TOOLS else db["orders"][resource]["user_id"]
            other = rng.choice(sorted(identities - {owner}))
            args = _arguments(db, tool, resource)
            for kind, actor, expected in (("cross_user", other, False),
                                          ("unauthenticated", None, False),
                                          ("authorized", owner, True)):
                cases.append({"tool": tool, "arguments": args, "actor": actor,
                              "context": guard_context(db, actor, tool, args),
                              "expected": expected, "kind": kind,
                              "singleton_check": index < 2,
                              "effect_check": index < 2 and not expected})
        actor = rng.choice(sorted(identities))
        if tool in ORDER_TOOLS:
            # An absent order keeps its native error.
            args, expected = {"order_id": "#NONEXISTENT-RESOURCE"}, True
        else:
            # A user resource is the identity itself; an unknown ID is never the session's.
            args, expected = {"user_id": "#NONEXISTENT-USER"}, False
        cases.append({"tool": tool, "arguments": args, "actor": actor,
                      "context": guard_context(db, actor, tool, args),
                      "expected": expected, "kind": "unknown_resource", "effect_check": False})
    for tool in sorted(set(app.TOOLS) - USER_TOOLS - ORDER_TOOLS):
        cases.append({"tool": tool, "context": guard_context(db, None, tool, {}),
                      "expected": True, "kind": "public", "effect_check": False})
    rng.shuffle(cases)
    return cases


def suite_from_seed(seed: bytes) -> SecuritySuite:
    db = app.load_db()
    identities = sorted(db["users"])
    random.Random(sha256(seed + b"partition").digest()).shuffle(identities)
    half = len(identities) // 2
    panels = [_panel(db, set(pool), random.Random(sha256(seed + label).digest()))
              for pool, label in ((identities[:half], b"development"),
                                  (identities[half:], b"sealed"))]
    return SecuritySuite(*panels, sha256(seed).hexdigest())


def create_suite(directory: Path) -> SecuritySuite:
    seed = secrets.token_bytes(32)
    # Reproduction material stays outside candidate mounts and provider requests.
    fd = os.open(directory / "security-seed", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(seed)
    return suite_from_seed(seed)


def check_panel(guard, cases: list[dict]) -> dict:
    db = app.load_db()
    if getattr(guard, "interface", "fixed") == "adapter":
        cases = cases + [{**case, "kind": "unconfirmed", "expected": False, "confirmed": False,
                         "effect_check": case.get("singleton_check", False)}
                        for case in cases if case["kind"] == "authorized" and case["tool"] in MUTATION_TOOLS]
    contexts = [guard_input(guard, db, case.get("actor"), case["tool"], case.get("arguments", {}))
                if getattr(guard, "interface", "fixed") == "adapter" else deepcopy(case["context"])
                for case in cases]
    for case, context in zip(cases, contexts):
        if case.get("confirmed") is False:
            context["confirmation"]["matches_action"] = False
    decisions = guard.decide_many(contexts)
    failures = {}
    # A failure count alone does not say which way the guard was wrong. Live feedback
    # without it led a model to flip "allow unknown order" while fixing "deny unknown user".
    expected_decisions = {}
    effect_checks = singleton_checks = 0
    for case, context, decision in zip(cases, contexts, decisions):
        label = f"{case['tool']}:{case['kind']}"
        expected_decisions[label] = "allow" if case["expected"] else "deny"
        if decision != case["expected"]:
            failures[label] = failures.get(label, 0) + 1
        if case["effect_check"]:
            # Exercise the actual single-call interface as well as batches.
            # Cached test decisions cannot stand in for production behavior.
            dispatcher = RetailDispatcher(guard=guard, trusted_user_id=case["actor"],
                confirmations=ConfirmationLedger() if case.get("confirmed") is False else None)
            dispatcher.invoke(case["tool"], case["arguments"])
            event = dispatcher.events()[-1]
            effect_checks += 1
            singleton_checks += 1
            if (event["outcome"] != "blocked" or event["executed_violations"]
                    or any(event["changed"].values())):
                failures[label + ":effect"] = failures.get(label + ":effect", 0) + 1
        elif case.get("singleton_check"):
            singleton_checks += 1
            if guard(deepcopy(context)) != case["expected"]:
                failures[label + ":singleton"] = failures.get(label + ":singleton", 0) + 1
    return {"passed": not failures, "cases": len(cases), "effect_checks": effect_checks,
            "singleton_checks": singleton_checks,
            "protected_tools": sorted(USER_TOOLS | ORDER_TOOLS), "failures": failures,
            "expected_decisions": {label: expected_decisions[label.split(":effect")[0].split(":singleton")[0]]
                                   for label in failures}}
