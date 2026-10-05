"""Prepare a reviewable patch bundle from trusted accepted validation artifacts."""

import argparse
import difflib
import json
from pathlib import Path

from patchloop.sandbox import SandboxGuard


def export_patch(source, validation, output):
    guard = SandboxGuard(source, interface=validation.get("interface", "fixed"))
    if (validation.get("accepted") is not True or validation.get("source_hash") != guard.source_hash
            or validation.get("coverage_complete") is not True
            or validation.get("scheduled_tasks") != 635 or validation.get("scheduled_calls") != 1375
            or validation.get("utility_tasks") != 634 or validation.get("utility_passed") != 634
            or validation.get("observed_violations") != 0 or validation.get("new_execution_errors") != 0
            or validation.get("baseline_fidelity") is not True
            or validation.get("security_development", {}).get("passed") is not True
            or validation.get("sealed_security", {}).get("passed") is not True):
        raise ValueError("Patch export requires matching accepted source and complete trusted validation")
    output.mkdir(parents=True, exist_ok=False)
    relative = f"examples/guards/{guard.source_hash[:16]}.py"
    evidence_relative = f"docs/evidence/guard-{guard.source_hash[:16]}.json"
    summary = {key: validation[key] for key in (
        "source_hash", "interface", "sandbox_backend", "scope", "boundary_cases", "boundary_failures",
        "scheduled_tasks", "scheduled_calls", "utility_tasks", "utility_passed", "coverage_complete",
        "observed_violations", "new_execution_errors", "baseline_fidelity") if key in validation}
    for key in ("security_development", "sealed_security"):
        summary[key] = {field: validation[key][field] for field in
                        ("passed", "cases", "effect_checks", "singleton_checks") if field in validation[key]}
    summary["accepted"] = True
    summary["limitations"] = "Finite fixture checks. Public archive regression; private panels share the same benchmark and oracle. No transfer or RL result."
    evidence = json.dumps(summary, indent=2) + "\n"
    patch = "".join(difflib.unified_diff([], source.splitlines(keepends=True),
                                      fromfile="/dev/null", tofile=f"b/{relative}"))
    patch += "".join(difflib.unified_diff([], evidence.splitlines(keepends=True),
                                        fromfile="/dev/null", tofile=f"b/{evidence_relative}"))
    (output / "guard.py").write_text(source)
    (output / "validation.public.json").write_text(evidence)
    (output / "patch.diff").write_text(patch)
    body = ("Add the exact validated retail guard and its public validation summary. "
            "The guard is checked against unauthorized effects and legitimate-call preservation.\n\n"
            f"Source SHA-256: `{guard.source_hash}`. Interface: `{guard.interface}`.\n\n"
            "Validation recorded all 635 tasks / 1,375 calls, preserved all 634 policy-consistent tasks, "
            "and contained the explicit reference identity conflict. Development and sealed panels passed; "
            "seeds, identity cases and private diagnostics are excluded.\n\n"
            "Recheck from a clean environment:\n\n```bash\n"
            f"python -m patchloop.repair --verify {relative} --interface {guard.interface}\n```\n\n"
            "This bundle does not independently authenticate a model/provider origin or establish general security. "
            "Publication targets this project's repository; vendored benchmark files remain unchanged.\n")
    (output / "PR_DESCRIPTION.md").write_text(body)
    (output / "paths.json").write_text(json.dumps({"guard": relative, "evidence": evidence_relative}, indent=2) + "\n")
    return {"source_hash": guard.source_hash, "patch": str(output / "patch.diff"), "description": str(output / "PR_DESCRIPTION.md")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export_patch(args.guard.read_text(), json.loads(args.validation.read_text()), args.output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
