"""Google ADK adapter: tool callbacks check every call before it runs.

    from patchloop.integrations.google_adk import protect
    agent = protect(Agent(name="support", model=..., tools=[...]))

A blocked call is skipped and the model receives {"error": <uniform refusal text>} as the tool
result. protect() appends the callbacks after any callbacks the agent already has, so that the
check sees the final arguments; a callback that returns a result earlier skips the tool anyway.
Facts may be async.
"""

from patchloop.sdk.runtime import REFUSAL, Blocked, client


def _as_list(value):
    return [] if value is None else list(value) if isinstance(value, list) else [value]


class PatchLoopCallbacks:
    def __init__(self, patchloop=None):
        self.patchloop = patchloop
        self._admitted = {}

    async def before_tool(self, tool, args, tool_context):
        try:
            self._admitted[tool_context.function_call_id] = await (self.patchloop or client()).abegin(tool.name, dict(args))
        except Blocked:
            return {"error": REFUSAL}
        return None

    async def after_tool(self, tool, args, tool_context, tool_response):
        self._finish(tool_context, "ok")
        return None

    async def on_tool_error(self, tool, args, tool_context, error):
        self._finish(tool_context, "error", error)
        return None

    def _finish(self, tool_context, outcome, error=None):
        admitted = self._admitted.pop(tool_context.function_call_id, None)
        if admitted is not None:
            (self.patchloop or client()).end(admitted, outcome, error)


def protect(agent, patchloop=None):
    """Add PatchLoop's tool callbacks to an ADK LlmAgent and return it."""
    callbacks = PatchLoopCallbacks(patchloop)
    agent.before_tool_callback = _as_list(agent.before_tool_callback) + [callbacks.before_tool]
    agent.after_tool_callback = _as_list(agent.after_tool_callback) + [callbacks.after_tool]
    agent.on_tool_error_callback = _as_list(agent.on_tool_error_callback) + [callbacks.on_tool_error]
    return agent
