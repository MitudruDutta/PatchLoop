"""The SDK runtime: applies a rule set at the tool boundary of a host application.

    import patchloop

    patchloop.init("rules.json", facts=lookup, mode="enforce")

    @patchloop.tool
    def get_ticket(ticket_id: str): ...

    with patchloop.identify(subject=user.id, tenant=user.org_id):   # once per request
        agent.run(...)
"""

import contextvars
import functools
import hashlib
import inspect
import json
import logging
import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from .rules import Decision, Ruleset, is_identifier, principal_of

log = logging.getLogger("patchloop")
MODES = ("observe", "warn", "enforce")
REFUSAL = "This action is not permitted."

try:
    SDK = f"python/{metadata.version('patchloop')}"
except metadata.PackageNotFoundError:
    SDK = "python/unknown"

_IDENTIFIER_NAME = re.compile(r"(^|_)ids?$|[a-z]Ids?$")
_principal = contextvars.ContextVar("patchloop_principal", default=None)
_client = None


@contextmanager
def identify(subject, tenant=None):
    """Bind the logged-in user for the enclosed block. Use it once per request or task.

    The binding lives in a context variable: asyncio tasks and frameworks that copy the
    context into worker threads (LangChain, LangGraph) see it; a bare threading.Thread does not.
    """
    token = _principal.set(principal_of({"subject": subject, "tenant": tenant}))
    try:
        yield
    finally:
        _principal.reset(token)


class Blocked(PermissionError):
    """Raised in enforce mode when a call is not allowed. The tool did not run.

    str(exc) is the same refusal text for every reason, so it is safe to show the model.
    exc.decision holds the reason and lookups for the host.
    """

    def __init__(self, decision: Decision):
        super().__init__(REFUSAL)
        self.decision = decision


class ConsentLedger:
    """Single-use, expiring consent grants, held in memory by one process.

    For several processes, pass an object with the same grant/has/take methods backed by
    shared storage. take() must be atomic, for example Redis GETDEL.
    """

    def __init__(self, ttl: float = 600):
        self.ttl = ttl
        self._grants = {}
        self._lock = threading.Lock()

    def grant(self, key: str, ttl: float | None = None):
        with self._lock:
            self._grants[key] = time.monotonic() + (self.ttl if ttl is None else ttl)

    def has(self, key: str) -> bool:
        with self._lock:
            return self._grants.get(key, 0) > time.monotonic()

    def take(self, key: str) -> bool:
        with self._lock:
            return self._grants.pop(key, 0) > time.monotonic()


def _arguments(signature, args, kwargs) -> dict:
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    return {name: list(value) if signature.parameters[name].kind is inspect.Parameter.VAR_POSITIONAL else value
            for name, value in bound.arguments.items()}


def _top_key(argument: str) -> str:
    if not argument.startswith("/"):
        return argument
    return argument[1:].split("/")[0].replace("~1", "/").replace("~0", "~")


class PatchLoop:
    """Protect tool calls with a rule set.

    facts(resource, id) -> the record as a dict, None when it does not exist; raise when the
                           lookup cannot answer. May be async for async tools and adapters.
    identity()          -> None, an identifier, or {"subject", "tenant"}. Defaults to the
                           user bound by patchloop.identify().

    Modes: "observe" runs every call and records the decision; "warn" also logs and calls
    on_violation; "enforce" runs only allowed calls and raises Blocked for the rest.
    Recordings keep the arguments the rule set uses, plus identifier values of arguments named like
    identifiers (id, ticket_id, ticket_ids, ticketId), so a later rule set can be replayed; every other
    value is "[redacted]" unless `redact` says otherwise.
    """

    def __init__(self, rules, *, facts, identity=None, mode="observe", modes=None, recordings=None,
                 redact=None, on_violation=None, consents=None):
        self.rules = rules if isinstance(rules, Ruleset) else Ruleset.load(rules)
        self.mode, self.modes = mode, dict(modes or {})
        for value in (mode, *self.modes.values()):
            if value not in MODES:
                raise ValueError(f"mode must be one of {MODES}, not {value!r}")
        self.facts = facts
        self.identity = identity or _principal.get
        self.recordings = Path(recordings) if recordings else None
        self.redact = redact or self._bound_arguments
        self.on_violation = on_violation
        self.consents = consents or ConsentLedger()
        self.registered = {}
        self._signatures = {}
        self._observers = []
        self._lock = threading.Lock()

    # Registration

    def tool(self, fn=None, *, name=None):
        """Wrap a sync or async tool function. The rule set names it by `name`, else its function name."""
        if fn is None:
            return lambda fn: self.tool(fn, name=name)
        tool_name = name or fn.__name__
        signature = inspect.signature(fn)
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
            raise TypeError(f"{tool_name}: cannot protect a tool that takes **kwargs, "
                            "because arguments that are not checked could reach it")
        if tool_name in self.registered:
            raise ValueError(f"a tool named {tool_name!r} is already registered; pass name= to tell them apart")

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                return await self.arun(tool_name, _arguments(signature, args, kwargs), lambda: fn(*args, **kwargs))
        else:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                return self.run(tool_name, _arguments(signature, args, kwargs), lambda: fn(*args, **kwargs))

        self.registered[tool_name] = wrapper
        self._signatures[tool_name] = signature
        return wrapper

    # Decisions

    def check(self, tool: str, arguments: dict) -> Decision:
        """Decide one call without running it, recording it or using up consent."""
        principal, key = self._context(tool, arguments)
        return self.rules.evaluate(tool, arguments, principal, self.facts, self._has_consent(key))

    async def acheck(self, tool: str, arguments: dict) -> Decision:
        principal, key = self._context(tool, arguments)
        return await self.rules.aevaluate(tool, arguments, principal, self.facts, self._has_consent(key))

    def begin(self, tool: str, arguments: dict) -> dict:
        """Decide and admit one call, raising Blocked when it must not run. Pair with end().

        For frameworks whose hooks run before and after the tool separately.
        """
        principal, key = self._context(tool, arguments)
        decision = self.rules.evaluate(tool, arguments, principal, self.facts, self._has_consent(key))
        return self._admit(tool, arguments, decision, principal, key)

    async def abegin(self, tool: str, arguments: dict) -> dict:
        principal, key = self._context(tool, arguments)
        decision = await self.rules.aevaluate(tool, arguments, principal, self.facts, self._has_consent(key))
        return self._admit(tool, arguments, decision, principal, key)

    def end(self, call: dict, outcome: str = "ok", error: BaseException | None = None):
        """Record how an admitted call finished: "ok" or "error"."""
        self._record(call, outcome, error)

    def run(self, tool: str, arguments: dict, call):
        """Decide, then run call() when the mode allows it. Adapters use this for framework tools."""
        admitted = self.begin(tool, arguments)
        try:
            result = call()
        except BaseException as exc:
            self.end(admitted, "error", exc)
            raise
        self.end(admitted)
        return result

    async def arun(self, tool: str, arguments: dict, call):
        """Like run, for an async call() and possibly async facts."""
        admitted = await self.abegin(tool, arguments)
        try:
            result = await call()
        except BaseException as exc:
            self.end(admitted, "error", exc)
            raise
        self.end(admitted)
        return result

    # Consent

    def confirm(self, tool: str, arguments: dict, *, ttl: float | None = None):
        """Record that the logged-in user said yes to this exact call. The grant is used up by one call."""
        principal = principal_of(self.identity())
        if principal is None:
            raise ValueError("confirm() needs a logged-in user; call it inside patchloop.identify()")
        if tool in self._signatures:
            arguments = _arguments(self._signatures[tool], (), arguments)
        self.consents.grant(self._consent_key(tool, arguments, principal), ttl)

    def _consent_key(self, tool, arguments, principal):
        payload = {"tool": tool, "arguments": arguments, "principal": principal, "ruleset": self.rules.sha256}
        text = json.dumps(payload, sort_keys=True, default=repr, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(text.encode()).hexdigest()

    def _context(self, tool, arguments):
        principal = principal_of(self.identity())
        needs_consent = (self.rules.tools.get(tool) or {}).get("consent") and principal is not None
        return principal, self._consent_key(tool, arguments, principal) if needs_consent else None

    def _has_consent(self, key):
        return key is not None and self.consents.has(key)

    def _admit(self, tool, arguments, decision, principal, key):
        mode = self.modes.get(tool, self.mode)
        runs = decision.allowed or mode != "enforce"
        consent = False
        if key is not None and runs:
            consent = self.consents.take(key)
            if decision.allowed and not consent:  # another call used the grant after the check
                decision = Decision("deny", "consent_required", tool, decision.lookups)
                runs = mode != "enforce"
        call = {"tool": tool, "arguments": arguments, "principal": principal, "consent": consent,
                "decision": decision, "mode": mode}
        if not decision.allowed:
            if mode == "warn":
                log.warning("%s would be blocked: %s (%s)", tool, decision.decision, decision.reason)
            if mode != "observe":
                self._notify(decision)
        if not runs:
            self._record(call, "blocked")
            raise Blocked(decision)
        return call

    def subscribe(self, observer):
        """Call observer(line) with every recording line, even without a recordings file.

        Returns a function that removes the observer.
        """
        self._observers.append(observer)
        return lambda: self._observers.remove(observer)

    # Diagnostics

    def unreviewed(self) -> list[str]:
        """Registered tools that the rule set does not name. They are never allowed."""
        return sorted(set(self.registered) - set(self.rules.tools))

    def doctor(self, tools=None) -> list[str]:
        """Problems that weaken protection or break calls silently. An empty list means none found.

        `tools` adds tools that were not wrapped with tool(), as {name: callable or [parameter names]}.
        """
        known = {name: list(signature.parameters) for name, signature in self._signatures.items()}
        for name, item in (tools or {}).items():
            known[name] = list(inspect.signature(item).parameters) if callable(item) else list(item)
        problems = []
        if self.mode == "observe" and "enforce" not in self.modes.values():
            problems.append("mode is observe: calls are recorded but nothing is blocked")
        for name in sorted(set(known) - set(self.rules.tools)):
            problems.append(f"{name}: not in the rule set, so every call is indeterminate")
        if known:
            for name in sorted(set(self.rules.tools) - set(known)):
                problems.append(f"{name}: in the rule set but not registered (check the spelling)")
        for name, parameters in sorted(known.items()):
            for binding in (self.rules.tools.get(name) or {}).get("resources", []):
                if _top_key(binding["argument"]) not in parameters:
                    problems.append(f"{name}: binding argument {binding['argument']!r} is not a parameter, "
                                    "so every call is denied")
        for name, rule in sorted(self.rules.tools.items()):
            if rule["effect"] != "none" and not rule.get("consent"):
                problems.append(f"{name}: effect {rule['effect']} without consent")
        return problems

    # Recording

    def _bound_arguments(self, tool, arguments):
        rule = self.rules.tools.get(tool) or {}
        keep = {_top_key(binding["argument"]) for binding in rule.get("resources", [])}

        def identifiers(value):
            return is_identifier(value) or (isinstance(value, list) and all(map(is_identifier, value)))
        return {key: value if key in keep or (_IDENTIFIER_NAME.search(key) and identifiers(value)) else "[redacted]"
                for key, value in arguments.items()}

    def _notify(self, decision):
        if self.on_violation is None:
            return
        try:
            self.on_violation(decision)
        except Exception:
            log.exception("on_violation hook failed")

    def _record(self, call, outcome, error=None):
        # A recording failure must never change the tool's outcome: the tool may already have run.
        if self.recordings is None and not self._observers:
            return
        try:
            line = {
                "schema_version": 1,
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "sdk": SDK,
                "ruleset": {"name": self.rules.name, "version": self.rules.version, "sha256": self.rules.sha256},
                "tool": call["tool"], "arguments": self.redact(call["tool"], call["arguments"]),
                "principal": call["principal"], "consent": call["consent"], "decision": call["decision"].to_dict(),
                "mode": call["mode"], "executed": outcome != "blocked", "outcome": outcome,
                "error": type(error).__name__ if error is not None else None,
            }
            for observer in list(self._observers):
                try:
                    observer(line)
                except Exception:
                    log.exception("recording observer failed")
            if self.recordings is not None:
                text = json.dumps(line, default=repr, ensure_ascii=False) + "\n"
                with self._lock, self.recordings.open("a", encoding="utf-8") as file:
                    file.write(text)
        except Exception:
            log.exception("could not write recording for %s", call["tool"])


# Module-level API: one process-wide instance, created by init().

def init(rules, **options) -> PatchLoop:
    """Create the process-wide PatchLoop instance. Call it once at startup, before defining tools."""
    global _client
    _client = PatchLoop(rules, **options)
    return _client


def client() -> PatchLoop:
    if _client is None:
        raise RuntimeError("call patchloop.init() first")
    return _client


def tool(fn=None, *, name=None):
    return client().tool(fn, name=name)


def check(tool_name: str, arguments: dict) -> Decision:
    return client().check(tool_name, arguments)


def confirm(tool_name: str, arguments: dict, *, ttl: float | None = None):
    return client().confirm(tool_name, arguments, ttl=ttl)


def doctor(tools=None) -> list[str]:
    return client().doctor(tools)
