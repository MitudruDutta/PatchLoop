"""FastMCP adapter: one middleware protects every tool on an MCP server.

    from patchloop.integrations.fastmcp import PatchLoopMiddleware
    mcp = FastMCP("helpdesk", middleware=[PatchLoopMiddleware()])

A blocked call returns an MCP tool error with the uniform refusal text. Put this middleware
last in the list, so that it checks the arguments the tool will receive. Tools missing from
the rule set are unreviewed and never allowed.
"""

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware

from patchloop.sdk.runtime import REFUSAL, Blocked, client


class PatchLoopMiddleware(Middleware):
    def __init__(self, patchloop=None):
        self.patchloop = patchloop

    async def on_call_tool(self, context, call_next):
        patchloop = self.patchloop or client()
        arguments = dict(context.message.arguments or {})
        try:
            return await patchloop.arun(context.message.name, arguments, lambda: call_next(context))
        except Blocked:
            raise ToolError(REFUSAL) from None
