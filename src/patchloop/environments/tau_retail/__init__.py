"""tau-bench retail environment, vendored from Sierra (MIT). See NOTICE.md."""

import functools
import json
import pickle
from pathlib import Path

from .tools import ALL_TOOLS

HERE = Path(__file__).parent
TOOLS = {tool.get_info()["function"]["name"]: tool for tool in ALL_TOOLS}
TERMINATE_TOOLS = frozenset({"transfer_to_human_agents"})


@functools.cache
def _db_snapshot() -> bytes:
    db = {name: json.loads((HERE / "data" / f"{name}.json").read_text())
          for name in ("orders", "products", "users")}
    return pickle.dumps(db, protocol=pickle.HIGHEST_PROTOCOL)


def load_db() -> dict:
    """Return a fresh, independent copy of the initial database."""
    return pickle.loads(_db_snapshot())  # about 2x faster than json.loads for each fresh copy


def policy() -> str:
    return (HERE / "wiki.md").read_text()


def reference_calls() -> list[dict]:
    """The 635 tau-bench retail tasks: correct tool calls and expected final-state hashes."""
    return json.loads((HERE / "reference_calls.json").read_text())
