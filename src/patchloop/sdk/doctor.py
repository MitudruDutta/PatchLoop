"""Check a PatchLoop setup: `patchloop doctor myapp.agent` or `patchloop doctor myapp.agent:guard`.

The module either has a `guard` attribute (a PatchLoop) or calls patchloop.init(). When its tools are
protected through an adapter, give the module a TOOLS catalog so that doctor can check them too.
"""

import argparse

from patchloop.loop import catalog
from patchloop.sdk.runtime import PatchLoop


def main():
    parser = argparse.ArgumentParser(prog="patchloop doctor", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="module, or module:attribute naming a PatchLoop")
    options = parser.parse_args()
    target = catalog.load_target(options.target)
    patchloop = target if isinstance(target, PatchLoop) else catalog.guard_of(target)
    rows = getattr(target, "TOOLS", None)
    tools = {tool["name"]: sorted(catalog.parameter_names(tool)) for tool in catalog.normalize(rows)} if rows else None
    problems = patchloop.doctor(tools)
    rules = patchloop.rules
    print(f"rule set {rules.name}@{rules.version} ({rules.sha256[:12]}), "
          f"{len(tools) if tools is not None else len(patchloop.registered)} tools checked")
    for problem in problems:
        print(f"  - {problem}")
    print("no problems found" if not problems else f"{len(problems)} problems")
    return 1 if problems else 0
