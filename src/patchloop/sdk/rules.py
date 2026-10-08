"""Rule set loading and evaluation, as defined in spec/rule-semantics.md.

Pure: no I/O except the host's facts lookup. Section numbers below refer to that document.
Evaluation is written once, as a generator that yields each lookup; `evaluate` and
`aevaluate` drive it with a sync or an async facts function.
"""

import hashlib
import inspect
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("patchloop")

MAX_SAFE_INTEGER = 2**53 - 1
MAX_PARENT_LINKS = 4

_TOP_KEYS = {"schema_version", "name", "version", "description", "resources", "tools"}
_RESOURCE_KEYS = {"principal", "owner_field", "tenant_field", "parent"}
_TOOL_KEYS = {"access", "effect", "consent", "description", "resources"}
_BINDING_KEYS = {"argument", "resource", "cardinality"}
_POINTER = re.compile(r"(/([^~/]|~[01])*)+")
_INDEX = re.compile(r"0|[1-9][0-9]*")
_UNAVAILABLE = object()


class RulesetError(ValueError):
    """The rule set breaks section 4. Nothing was loaded."""


@dataclass(frozen=True)
class Decision:
    decision: str  # allow, deny or indeterminate
    reason: str
    tool: str
    lookups: list = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"

    def to_dict(self) -> dict:
        return {"decision": self.decision, "reason": self.reason, "lookups": [dict(item) for item in self.lookups]}


def is_identifier(value) -> bool:
    return isinstance(value, str) or (type(value) is int and abs(value) <= MAX_SAFE_INTEGER)


def _same(a, b) -> bool:
    # Python never equates a str with an int, and is_identifier excludes bool and float.
    return is_identifier(a) and is_identifier(b) and a == b


def principal_of(value) -> dict | None:
    """Normalize an identity: None, an identifier, or {subject, tenant}."""
    if value is None:
        return None
    if is_identifier(value):
        value = {"subject": value}
    if not isinstance(value, dict) or set(value) - {"subject", "tenant"}:
        raise TypeError("identity must be None, an identifier, or {'subject': ..., 'tenant': ...}")
    subject, tenant = value.get("subject"), value.get("tenant")
    if not is_identifier(subject) or not (tenant is None or is_identifier(tenant)):
        raise TypeError("principal subject and tenant must be identifiers (string or integer)")
    return {"subject": subject, "tenant": tenant}


def argument_value(arguments: dict, name: str):
    """Section 3 step 4.1: a top-level key, or a JSON Pointer when `name` starts with "/"."""
    if not name.startswith("/"):
        return arguments.get(name)
    node = arguments
    for token in name[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            node = node.get(token)
        elif isinstance(node, list) and _INDEX.fullmatch(token) and int(token) < len(node):
            node = node[int(token)]
        else:
            return None
    return node


def _require(condition, message):
    if not condition:
        raise RulesetError(message)


def _object(value, allowed, where):
    _require(isinstance(value, dict), f"{where} must be an object")
    extra = sorted(set(value) - allowed)
    _require(not extra, f"{where}: unknown keys {extra}")


def _defined(name, resources):
    return isinstance(name, str) and name in resources


def _text(value, where):
    _require(isinstance(value, str) and value, f"{where} must be a non-empty string")


def validate(data) -> None:
    """Raise RulesetError unless `data` follows section 4 (rules 2-10)."""
    _object(data, _TOP_KEYS, "rule set")
    _require(type(data.get("schema_version")) is int and data["schema_version"] == 1, "schema_version must be 1")
    _text(data.get("name"), "name")
    _text(data.get("version"), "version")
    _require(isinstance(data.get("description", ""), str), "description must be a string")
    resources, tools = data.get("resources"), data.get("tools")
    _require(isinstance(resources, dict), "resources must be an object")
    _require(isinstance(tools, dict), "tools must be an object")

    for name, resource in resources.items():
        where = f"resource {name!r}"
        _object(resource, _RESOURCE_KEYS, where)
        forms = ("principal" in resource) + ("parent" in resource) + bool({"owner_field", "tenant_field"} & set(resource))
        _require(forms == 1, f"{where} must have exactly one of principal, parent, or owner_field/tenant_field")
        _require(resource.get("principal", True) is True, f"{where}: principal must be true")
        for key in ("owner_field", "tenant_field"):
            if key in resource:
                _text(resource[key], f"{where}.{key}")
        if "parent" in resource:
            _object(resource["parent"], {"resource", "field"}, f"{where}.parent")
            _text(resource["parent"].get("field"), f"{where}.parent.field")
            _require(_defined(resource["parent"].get("resource"), resources), f"{where}: parent must name a defined resource")

    for name in resources:
        seen, current = {name}, resources[name]
        while "parent" in current:
            parent = current["parent"]["resource"]
            _require(parent not in seen, f"resource {name!r}: parent links form a cycle")
            _require(len(seen) <= MAX_PARENT_LINKS, f"resource {name!r}: more than {MAX_PARENT_LINKS} parent links")
            seen.add(parent)
            current = resources[parent]

    for name, tool in tools.items():
        where = f"tool {name!r}"
        _object(tool, _TOOL_KEYS, where)
        _require(tool.get("access") in ("public", "authenticated", "scoped"), f"{where}: access must be public, authenticated or scoped")
        _require(tool.get("effect") in ("none", "state_write", "external"), f"{where}: effect must be none, state_write or external")
        _require(isinstance(tool.get("consent", False), bool), f"{where}: consent must be a boolean")
        _require(not (tool["access"] == "public" and tool.get("consent")), f"{where}: a public tool cannot require consent")
        _require(isinstance(tool.get("description", ""), str), f"{where}: description must be a string")
        bindings = tool.get("resources", [])
        _require(isinstance(bindings, list), f"{where}: resources must be an array")
        if tool["access"] == "scoped":
            _require(bindings, f"{where}: a scoped tool needs at least one resource binding")
        else:
            _require(not bindings, f"{where}: only scoped tools have resource bindings")
        for binding in bindings:
            _object(binding, _BINDING_KEYS, f"{where} binding")
            argument = binding.get("argument")
            _text(argument, f"{where} binding argument")
            _require(not argument.startswith("/") or _POINTER.fullmatch(argument), f"{where}: invalid JSON Pointer {argument!r}")
            _require(_defined(binding.get("resource"), resources), f"{where}: binding must name a defined resource")
            _require(binding.get("cardinality", "one") in ("one", "many"), f"{where}: cardinality must be one or many")


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    _require(not duplicates, f"duplicate keys {duplicates}")
    return dict(pairs)


def canonical_sha256(data) -> str:
    # Equals RFC 8785 for rule sets (strings, booleans, small integers). Key order differs
    # from RFC 8785 only for keys mixing characters above U+FFFF with U+E000-U+FFFF; use a JCS library then.
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def _lookup(facts, resource, identifier):
    try:
        record = facts(resource, identifier)
    except Exception:
        log.warning("facts lookup failed for %s %r", resource, identifier, exc_info=True)
        return _UNAVAILABLE
    if inspect.iscoroutine(record):
        record.close()
    if inspect.isawaitable(record):
        log.warning("facts returned an awaitable; use an async tool or aevaluate for async facts")
        return _UNAVAILABLE
    return record if record is None or isinstance(record, dict) else _UNAVAILABLE


async def _alookup(facts, resource, identifier):
    try:
        record = facts(resource, identifier)
        if inspect.isawaitable(record):
            record = await record
    except Exception:
        log.warning("facts lookup failed for %s %r", resource, identifier, exc_info=True)
        return _UNAVAILABLE
    return record if record is None or isinstance(record, dict) else _UNAVAILABLE


class Ruleset:
    def __init__(self, data: dict):
        validate(data)
        self.data = json.loads(json.dumps(data))  # private copy; later edits to `data` change nothing
        self.name, self.version = data["name"], data["version"]
        self.sha256 = canonical_sha256(data)
        self.tools, self.resources = self.data["tools"], self.data["resources"]

    @classmethod
    def from_json(cls, text: str) -> "Ruleset":
        """Load JSON text, refusing duplicate keys (section 4 rule 1)."""
        try:
            data = json.loads(text, object_pairs_hook=_no_duplicates)
        except json.JSONDecodeError as exc:
            raise RulesetError(f"not valid JSON: {exc}") from None
        return cls(data)

    @classmethod
    def load(cls, path) -> "Ruleset":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def evaluate(self, tool: str, arguments: dict, principal: dict | None, facts, consent: bool = False) -> Decision:
        """Section 3. `facts(resource, id)` returns a record dict, None when missing, or raises when unavailable."""
        steps = self._steps(tool, arguments, principal, consent)
        try:
            request = next(steps)
            while True:
                request = steps.send(_lookup(facts, *request))
        except StopIteration as done:
            return done.value

    async def aevaluate(self, tool: str, arguments: dict, principal: dict | None, facts, consent: bool = False) -> Decision:
        """Like evaluate, but `facts` may be async."""
        steps = self._steps(tool, arguments, principal, consent)
        try:
            request = next(steps)
            while True:
                request = steps.send(await _alookup(facts, *request))
        except StopIteration as done:
            return done.value

    def _steps(self, tool, arguments, principal, consent):
        lookups = []

        def result(decision, reason):
            return Decision(decision, reason, tool, lookups)

        rule = self.tools.get(tool)
        if rule is None:
            return result("indeterminate", "unreviewed_tool")
        if rule["access"] == "public":
            return result("allow", "public")
        if principal is None:
            return result("deny", "authentication_required")
        for binding in rule.get("resources", []):
            value = argument_value(arguments, binding["argument"])
            if value is None:
                return result("deny", "missing_argument")
            items = value if binding.get("cardinality") == "many" else [value]
            if not isinstance(items, list) or not all(map(is_identifier, items)):
                return result("deny", "malformed_argument")
            for item in items:
                failure = yield from self._check(binding["resource"], item, principal, ("deny", "resource_missing"), lookups)
                if failure:
                    return result(*failure)
        if rule.get("consent") and consent is not True:
            return result("deny", "consent_required")
        return result("allow", "authorized")

    def _check(self, name, item, principal, on_missing, lookups):
        """Section 3.1. Returns None when the item passes, else (decision, reason)."""
        resource = self.resources[name]
        if resource.get("principal"):
            return None if _same(item, principal["subject"]) else ("deny", "not_principal")
        record = yield (name, item)
        if record is _UNAVAILABLE:
            lookups.append({"resource": name, "id": item, "status": "unavailable"})
            return ("indeterminate", "facts_unavailable")
        if record is None:
            lookups.append({"resource": name, "id": item, "status": "missing"})
            return on_missing
        entry = {"resource": name, "id": item, "status": "found"}
        for key, field_key in (("owner", "owner_field"), ("tenant", "tenant_field")):
            if field_key in resource:
                entry[key] = record.get(resource[field_key])
        if "parent" in resource:
            entry["parent"] = record.get(resource["parent"]["field"])
        lookups.append(entry)

        if "parent" in resource:
            if not is_identifier(entry["parent"]):
                return ("indeterminate", "broken_parent")
            return (yield from self._check(resource["parent"]["resource"], entry["parent"], principal,
                                           ("indeterminate", "broken_parent"), lookups))
        if "tenant_field" in resource:
            if principal["tenant"] is None or entry["tenant"] is None:
                return ("indeterminate", "tenant_unknown")
            if not _same(entry["tenant"], principal["tenant"]):
                return ("deny", "wrong_tenant")
        if "owner_field" in resource:
            if entry["owner"] is None:
                return ("indeterminate", "owner_unknown")
            if not _same(entry["owner"], principal["subject"]):
                return ("deny", "not_owner")
        return None
