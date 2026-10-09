"""OpenAI Agents SDK adapter: wrap each function tool's invocation.

    from patchloop.integrations.openai_agents import protect
    agent = protect(Agent(name="support", tools=[get_ticket, close_ticket]))

A blocked call is not run and the model receives PatchLoop's message as the tool output.
Only function tools run in your process, so only they are covered. Hosted tools (web search,
file search, code interpreter) run at OpenAI. For tools from MCP servers, protect the server
(FastMCP middleware) or the client session (patchloop.integrations.mcp).
"""

import dataclasses
import json

from agents import FunctionTool

from patchloop.sdk.runtime import Blocked, client


def protect_tool(tool: FunctionTool, patchloop=None) -> FunctionTool:
    original = tool.on_invoke_tool

    async def on_invoke_tool(context, input_json):
        try:
            arguments = json.loads(input_json or "{}")
        except ValueError:
            arguments = None
        if not isinstance(arguments, dict):
            arguments = {}  # nothing to check against; scoped tools then deny as missing_argument
        try:
            return await (patchloop or client()).arun(tool.name, arguments, lambda: original(context, input_json))
        except Blocked as blocked:
            return str(blocked)

    return dataclasses.replace(tool, on_invoke_tool=on_invoke_tool)


def protect(agent, patchloop=None):
    """Protect the function tools of an Agent in place and return it."""
    agent.tools = [protect_tool(tool, patchloop) if isinstance(tool, FunctionTool) else tool for tool in agent.tools]
    return agent
