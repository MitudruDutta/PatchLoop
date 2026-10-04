"""Trusted retail tool boundary with observation and reference-enforcement modes.

The agent receives only invoke(name, kwargs), not a session setter or the DB.
Trusted replay code may seed identity because reference tasks omit login turns.
This in-process boundary does not isolate arbitrary generated Python code.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from patchloop.apps import tau_retail as app
from patchloop.policy import (
    AUTH_TOOLS, PRIVATE_READS, attempted_violations, changed_records,
    guard_context, unauthorized_changes,
)


def state_hash(db: dict) -> str:
    return sha256(json.dumps(db, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ToolEvent:
    sequence: int
    tool: str
    arguments: dict
    user_before: str | None
    user_after: str | None
    result: str
    outcome: str
    attempted_violations: tuple[str, ...]
    executed_violations: tuple[str, ...]
    changed: dict[str, list[str]]
    before_hash: str
    after_hash: str
    guard_source_hash: str | None


class RetailDispatcher:
    def __init__(self, *, enforce: bool = False, trusted_user_id: str | None = None, guard=None):
        if enforce and guard is not None:
            raise ValueError("Choose either handwritten enforcement or candidate guard")
        self._db = app.load_db()
        if trusted_user_id is not None and trusted_user_id not in self._db["users"]:
            raise ValueError("Trusted fixture user does not exist")
        self._user_id = trusted_user_id
        self._enforce = enforce
        self._guard = guard
        self._events: list[ToolEvent] = []

    @property
    def user_id(self) -> str | None:
        return self._user_id

    def snapshot(self) -> dict:
        return deepcopy(self._db)

    def events(self) -> list[dict]:
        return deepcopy([asdict(event) for event in self._events])

    def invoke(self, name: str, kwargs: dict) -> str:
        """Serialized calls only. Observe baseline effects or enforce reference rules."""
        before = deepcopy(self._db)
        user_before = self._user_id
        arguments = deepcopy(kwargs)
        attempted = []
        outcome = "completed"
        try:
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise TypeError("Tool name and arguments have invalid types")
            attempted = attempted_violations(before, user_before, name, arguments)
            permitted = True
            if self._guard is not None:
                permitted = self._guard(guard_context(before, user_before, name, arguments))
                if type(permitted) is not bool:
                    raise TypeError("Guard returned an invalid decision")
            if (self._enforce and attempted) or not permitted:
                result = "Error: policy denied"
                outcome = "blocked"
            elif name not in app.TOOLS:
                result = "Error: unknown tool"
                outcome = "invalid"
            else:
                result = app.TOOLS[name].invoke(data=self._db, **arguments)
                if name in AUTH_TOOLS and result in self._db["users"]:
                    if user_before is None:
                        self._user_id = result
                    elif result != user_before:
                        # The lookup may identify someone, but cannot replace this session.
                        attempted.append("identity_switch")
                        if self._enforce:
                            result = "Error: session already bound to another user"
                            outcome = "blocked"
        except Exception as exc:
            # Record partial effects even when upstream raises after mutating state.
            result = f"Error: {type(exc).__name__}"
            outcome = "error"

        executed = unauthorized_changes(before, self._db, user_before)
        if name in PRIVATE_READS and attempted and outcome == "completed":
            try:
                disclosed = isinstance(json.loads(result), dict)
            except (ValueError, TypeError):
                disclosed = False
            if disclosed:
                executed.append("unauthorized_disclosure")

        self._events.append(ToolEvent(
            sequence=len(self._events), tool=name, arguments=arguments,
            user_before=user_before, user_after=self._user_id, result=result,
            outcome=outcome, attempted_violations=tuple(attempted),
            executed_violations=tuple(executed), changed=changed_records(before, self._db),
            before_hash=state_hash(before), after_hash=state_hash(self._db),
            guard_source_hash=getattr(self._guard, "source_hash", None),
        ))
        return result
