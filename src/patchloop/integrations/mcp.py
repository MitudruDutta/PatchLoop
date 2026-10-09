"""MCP client adapter: check calls your agent makes to MCP servers, including servers you do not run.

    from patchloop.integrations.mcp import protect_session
    session = protect_session(session)          # an mcp.ClientSession
    tools = await load_mcp_tools(session)       # for example with langchain-mcp-adapters

A blocked call returns an MCP error result with the uniform refusal text and never reaches the
server. Every other attribute of the session is passed through. For servers you run, prefer the
server-side FastMCP middleware.
"""

from mcp.types import CallToolResult, TextContent

from patchloop.sdk.runtime import REFUSAL, Blocked, client


class ProtectedSession:
    def __init__(self, session, patchloop=None):
        self._session, self.patchloop = session, patchloop

    def __getattr__(self, name):
        return getattr(self._session, name)

    async def call_tool(self, name, arguments=None, *args, **kwargs):
        patchloop = self.patchloop or client()
        try:
            admitted = await patchloop.abegin(name, dict(arguments or {}))
        except Blocked:
            return CallToolResult(content=[TextContent(type="text", text=REFUSAL)], isError=True)
        try:
            result = await self._session.call_tool(name, arguments, *args, **kwargs)
        except BaseException as exc:
            patchloop.end(admitted, "error", exc)
            raise
        patchloop.end(admitted, "error" if result.isError else "ok")
        return result


def protect_session(session, patchloop=None) -> ProtectedSession:
    return ProtectedSession(session, patchloop)
