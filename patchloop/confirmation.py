"""Trusted, single-use consent bound to exact action, identity and version."""

from copy import deepcopy
from hashlib import sha256
import json
import time

from patchloop.policy import MUTATION_TOOLS


def action_digest(tool, arguments, user_id, source_hash):
    value = {"tool": tool, "arguments": arguments, "user_id": user_id, "source_hash": source_hash}
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class ConfirmationLedger:
    def __init__(self, *, lifetime=600, clock=time.monotonic):
        self._clock, self._lifetime = clock, lifetime
        self._pending = self._confirmed = None

    def propose(self, tool, arguments, user_id, source_hash):
        # Consent binds the current identity, even none. Authentication is enforced when the
        # action runs; a later login changes the digest, so earlier consent cannot carry over.
        if tool not in MUTATION_TOOLS or not isinstance(arguments, dict):
            raise ValueError("Confirmation requires a specific mutation")
        self._confirmed = None
        self._pending = {"tool": tool, "arguments": deepcopy(arguments), "user_id": user_id,
                         "source_hash": source_hash,
                         "digest": action_digest(tool, arguments, user_id, source_hash),
                         "expires": self._clock() + self._lifetime}
        return self.pending()

    def pending(self):
        if self._pending is None or self._pending["expires"] < self._clock():
            return None
        return {key: deepcopy(value) for key, value in self._pending.items() if key != "expires"}

    def user_turn(self, text):
        """Only the session's external user-input path may invoke this method."""
        self._confirmed = None
        acknowledged = text.strip().casefold() == "yes" and self.pending() is not None
        if acknowledged:
            self._confirmed = self._pending
        self._pending = None
        return bool(acknowledged)

    def permits(self, tool, arguments, user_id, source_hash):
        return (self._confirmed is not None and self._confirmed["expires"] >= self._clock()
                and self._confirmed["digest"] == action_digest(tool, arguments, user_id, source_hash))

    def consume(self, tool, arguments, user_id, source_hash):
        permitted = self.permits(tool, arguments, user_id, source_hash)
        if permitted:
            self._confirmed = None
        return permitted
