"""Vendor the tau-bench retail environment at a pinned commit.

Usage:
    git clone https://github.com/sierra-research/tau-bench /tmp/tau-bench
    git -C /tmp/tau-bench checkout 59a200c6d575d595120f1cb70fea53cef0632f6b
    python scripts/vendor_tau_bench.py /tmp/tau-bench

Copies the retail tools, data, and policy into src/patchloop/environments/tau_retail/ and
writes reference_calls.json. Expected hashes are computed by running the
*upstream* tool files, so the test suite proves the vendored copy is faithful.
"""

import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

COMMIT = "59a200c6d575d595120f1cb70fea53cef0632f6b"
TERMINATE_TOOLS = {"transfer_to_human_agents"}
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "src" / "patchloop" / "environments" / "tau_retail"
sys.path.insert(0, str(ROOT / "src"))
from patchloop.evaluation.replay import db_hash  # noqa: E402  single definition of the state hash


class _Record:
    def __init__(self, **fields):
        self.__dict__.update(fields)


def _stub_tau_bench(clone: Path):
    """Let upstream task and tool files import without tau_bench's heavy dependencies."""
    pkg = types.ModuleType("tau_bench")
    pkg.__path__ = [str(clone / "tau_bench")]
    sys.modules["tau_bench"] = pkg
    sys.modules["tau_bench.types"] = types.SimpleNamespace(Task=_Record, Action=_Record)
    sys.modules["tau_bench.envs"] = types.ModuleType("tau_bench.envs")
    tool = types.ModuleType("tau_bench.envs.tool")
    exec((clone / "tau_bench/envs/tool.py").read_text(), tool.__dict__)
    sys.modules["tau_bench.envs.tool"] = tool


def _load(path: Path, name: str):
    module = types.ModuleType(name)
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def main(clone: Path):
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != COMMIT:
        sys.exit(f"clone is at {head}, expected {COMMIT}")

    src = clone / "tau_bench" / "envs" / "retail"
    shutil.rmtree(DEST / "tools", ignore_errors=True)
    (DEST / "tools").mkdir(parents=True)
    (DEST / "data").mkdir(exist_ok=True)
    for f in sorted((src / "tools").glob("*.py")):
        text = f.read_text().replace("from tau_bench.envs.tool import Tool", "from ..tool import Tool")
        (DEST / "tools" / f.name).write_text(text)
    shutil.copy(clone / "tau_bench" / "envs" / "tool.py", DEST / "tool.py")
    for name in ("orders", "products", "users"):
        shutil.copy(src / "data" / f"{name}.json", DEST / "data" / f"{name}.json")
    shutil.copy(src / "wiki.md", DEST / "wiki.md")
    shutil.copy(clone / "LICENSE", DEST / "LICENSE.sierra")

    _stub_tau_bench(clone)
    tools = {}
    for f in sorted((src / "tools").glob("*.py")):
        if f.name == "__init__.py":
            continue
        for obj in vars(_load(f, f"upstream_{f.stem}")).values():
            if isinstance(obj, type) and hasattr(obj, "get_info") and obj.__name__ != "Tool":
                tools[obj.get_info()["function"]["name"]] = obj
    base = {n: (src / "data" / f"{n}.json").read_text() for n in ("orders", "products", "users")}

    records = []
    for split in ("train", "dev", "test"):
        tasks = getattr(_load(src / f"tasks_{split}.py", f"tasks_{split}"), f"TASKS_{split.upper()}")
        for i, task in enumerate(tasks):
            db = {n: json.loads(t) for n, t in base.items()}
            actions = [{"name": a.name, "kwargs": a.kwargs} for a in task.actions]
            for a in actions:
                if a["name"] in TERMINATE_TOOLS:
                    continue
                try:  # tau-bench Env.step swallows tool exceptions the same way
                    tools[a["name"]].invoke(data=db, **a["kwargs"])
                except Exception:
                    pass
            records.append({
                "id": f"{split}-{i}",
                "user_id": task.user_id,
                "actions": actions,
                "expected_hash": db_hash(db),
            })
    (DEST / "reference_calls.json").write_text(json.dumps(records, indent=1) + "\n")
    print(f"vendored {len(tools)} tools, {len(records)} tasks, "
          f"{sum(len(r['actions']) for r in records)} calls into {DEST}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
