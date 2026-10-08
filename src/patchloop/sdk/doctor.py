"""Check a PatchLoop setup: `patchloop doctor myapp.agent` or `patchloop doctor myapp.agent:guard`."""

import argparse
import importlib
import sys

from patchloop.sdk import runtime


def main():
    parser = argparse.ArgumentParser(prog="patchloop doctor", description=__doc__)
    parser.add_argument("target", help="module that calls patchloop.init(), or module:attribute naming a PatchLoop")
    options = parser.parse_args()
    module_name, _, attribute = options.target.partition(":")
    sys.path.insert(0, "")
    module = importlib.import_module(module_name)
    patchloop = getattr(module, attribute) if attribute else runtime.client()
    problems = patchloop.doctor()
    rules = patchloop.rules
    print(f"rule set {rules.name}@{rules.version} ({rules.sha256[:12]}), {len(patchloop.registered)} registered tools")
    for problem in problems:
        print(f"  - {problem}")
    print("no problems found" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0
