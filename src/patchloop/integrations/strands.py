"""Strands Agents adapter.

    from patchloop.integrations.strands import PatchLoopHooks
    agent = Agent(model=model, tools=[...], hooks=[PatchLoopHooks()])

A blocked call is cancelled with PatchLoop's message, which Strands returns to the model
as an error tool result. Register these hooks after any hook that changes tool input, so they
check what the tool receives. Facts must be synchronous here.
"""

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider

from patchloop.sdk.runtime import Blocked, client


class PatchLoopHooks(HookProvider):
    def __init__(self, patchloop=None):
        self.patchloop = patchloop
        self._admitted = {}

    def register_hooks(self, registry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self._before)
        registry.add_callback(AfterToolCallEvent, self._after)

    def _before(self, event):
        use = event.tool_use
        try:
            self._admitted[use["toolUseId"]] = (self.patchloop or client()).begin(use["name"], dict(use.get("input") or {}))
        except Blocked as blocked:
            event.cancel_tool = str(blocked)

    def _after(self, event):
        admitted = self._admitted.pop(event.tool_use["toolUseId"], None)
        if admitted is None:
            return
        failed = event.exception is not None or (event.result or {}).get("status") == "error"
        (self.patchloop or client()).end(admitted, "error" if failed else "ok", event.exception)
