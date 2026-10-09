"""Tool catalogs and target modules shared by `propose`, `replay` and `test`."""

import functools
import importlib
import inspect
import json
import sys
import types
import typing
from pathlib import Path

from patchloop.sdk import runtime

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


def schema_of(annotation) -> dict:
    """A small JSON Schema for a parameter annotation; {} when unknown."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        options = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        return schema_of(options[0]) if len(options) == 1 else {}
    base = origin or annotation
    return {"type": _JSON_TYPES[base]} if base in _JSON_TYPES else {}


def from_patchloop(guard) -> list[dict]:
    """The catalog of tools wrapped with guard.tool()."""
    tools = []
    for name, wrapper in sorted(guard.registered.items()):
        parameters = inspect.signature(wrapper).parameters
        tools.append({
            "name": name,
            "description": (inspect.getdoc(wrapper) or "").split("\n\n")[0],
            "parameters": {
                "type": "object",
                "properties": {key: schema_of(p.annotation) for key, p in parameters.items()},
                "required": [key for key, p in parameters.items() if p.default is inspect.Parameter.empty
                             and p.kind is not inspect.Parameter.VAR_POSITIONAL],
            },
        })
    return tools


def from_file(path) -> list[dict]:
    """Read tools as plain {name, description, parameters}, OpenAI function tools, or MCP tools/list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("tools", []) if isinstance(data, dict) else data
    tools = []
    for row in rows:
        row = row.get("function", row) if row.get("type") == "function" else row
        tools.append({"name": row["name"], "description": row.get("description", ""),
                      "parameters": row.get("parameters") or row.get("inputSchema") or {"type": "object", "properties": {}}})
    return tools


def load_target(spec: str):
    """Import `module` or `module:attribute.path`. The current directory is importable, as for `python -m`."""
    module_name, _, attribute = spec.partition(":")
    if "" not in sys.path:
        sys.path.insert(0, "")
    module = importlib.import_module(module_name)
    return functools.reduce(getattr, attribute.split("."), module) if attribute else module


def guard_of(target):
    """The PatchLoop instance of a target module: its `guard` attribute, else the one from patchloop.init()."""
    guard = getattr(target, "guard", None)
    return guard if guard is not None else runtime.client()


def parameter_names(tool: dict) -> set:
    return set((tool.get("parameters") or {}).get("properties", {}))
