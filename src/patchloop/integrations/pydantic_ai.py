"""Pydantic AI adapter: a toolset wrapper that checks every call.

    from patchloop.integrations.pydantic_ai import PatchLoopToolset
    agent = Agent(model, toolsets=[PatchLoopToolset(FunctionToolset([get_ticket, close_ticket]))])

A blocked call is not run and the model receives the uniform refusal text as the tool result.
Facts may be async. Wrap MCP server toolsets the same way.
"""

from dataclasses import dataclass
from typing import Any

from pydantic_ai.toolsets import WrapperToolset

from patchloop.sdk.runtime import REFUSAL, Blocked, client


@dataclass
class PatchLoopToolset(WrapperToolset):
    patchloop: Any = None

    async def call_tool(self, name, tool_args, ctx, tool):
        try:
            return await (self.patchloop or client()).arun(
                name, dict(tool_args), lambda: self.wrapped.call_tool(name, tool_args, ctx, tool))
        except Blocked:
            return REFUSAL
