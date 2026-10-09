"""CrewAI adapter: global tool hooks that check every tool call of every crew in this process.

    from patchloop.integrations import crewai as patchloop_crewai
    uninstall = patchloop_crewai.install()

CrewAI swallows exceptions raised by tool hooks and then runs the tool (it fails open), so the
hook here catches every error itself and blocks the call instead. A blocked call returns the
uniform refusal text to the agent. Call the returned function to remove the hooks.
"""

import logging

from crewai.hooks.tool_hooks import (register_after_tool_call_hook, register_before_tool_call_hook,
                                     unregister_after_tool_call_hook, unregister_before_tool_call_hook)

from patchloop.sdk.runtime import REFUSAL, Blocked, client

log = logging.getLogger("patchloop")
_BLOCKED = object()


class PatchLoopHooks:
    def __init__(self, patchloop=None):
        self.patchloop = patchloop
        self._calls = {}

    def before(self, context):
        # CrewAI passes the same tool_input dict to the before and after hooks of one call.
        try:
            self._calls[id(context.tool_input)] = (self.patchloop or client()).begin(
                context.tool_name, dict(context.tool_input))
            return None
        except Blocked:
            self._calls[id(context.tool_input)] = _BLOCKED
        except Exception:
            log.exception("PatchLoop check failed for %s; blocking the call", context.tool_name)
            self._calls[id(context.tool_input)] = _BLOCKED
        return False

    def after(self, context):
        admitted = self._calls.pop(id(context.tool_input), None)
        if admitted is _BLOCKED:
            return REFUSAL
        if admitted is not None:
            (self.patchloop or client()).end(admitted)
        return None


def install(patchloop=None):
    """Register the hooks for every crew and return a function that removes them."""
    hooks = PatchLoopHooks(patchloop)
    register_before_tool_call_hook(hooks.before)
    register_after_tool_call_hook(hooks.after)

    def uninstall():
        unregister_before_tool_call_hook(hooks.before)
        unregister_after_tool_call_hook(hooks.after)
    return uninstall
