"""Claude Agent SDK adapter: PreToolUse hooks check every tool call before it runs.

    from patchloop.integrations.claude_agent_sdk import PatchLoopHooks
    options = ClaudeAgentOptions(hooks=PatchLoopHooks().hooks(), ...)

A blocked call is denied with PatchLoop's message for the model. Hooks are used rather than
can_use_tool because the SDK skips can_use_tool for tools in allowed_tools and under
bypassPermissions. Every tool reaches the rule set, including built-in tools such as Bash
and Read, and MCP tools under their full names (mcp__<server>__<tool>); list the ones the
agent may use. Pass name= to map tool names. Call patchloop.identify() around the code that
creates the client or calls query(), so the hooks see the user.
"""

from claude_agent_sdk import HookMatcher

from patchloop.sdk.runtime import Blocked, client


class PatchLoopHooks:
    def __init__(self, patchloop=None, name=None):
        self.patchloop, self.name = patchloop, name or (lambda tool_name: tool_name)
        self._admitted = {}

    def hooks(self) -> dict:
        return {"PreToolUse": [HookMatcher(hooks=[self.pre_tool_use])],
                "PostToolUse": [HookMatcher(hooks=[self.post_tool_use])],
                "PostToolUseFailure": [HookMatcher(hooks=[self.post_tool_use_failure])]}

    async def pre_tool_use(self, hook_input, tool_use_id, context):
        try:
            self._admitted[hook_input["tool_use_id"]] = await (self.patchloop or client()).abegin(
                self.name(hook_input["tool_name"]), dict(hook_input.get("tool_input") or {}))
        except Blocked as blocked:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": str(blocked)}}
        return {}

    async def post_tool_use(self, hook_input, tool_use_id, context):
        self._finish(hook_input, "ok")
        return {}

    async def post_tool_use_failure(self, hook_input, tool_use_id, context):
        self._finish(hook_input, "error")
        return {}

    def _finish(self, hook_input, outcome):
        admitted = self._admitted.pop(hook_input["tool_use_id"], None)
        if admitted is not None:
            (self.patchloop or client()).end(admitted, outcome)
