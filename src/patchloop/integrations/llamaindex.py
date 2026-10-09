"""LlamaIndex adapter: wrap the tools you give to an agent.

    from patchloop.integrations.llamaindex import protect_tools
    agent = FunctionAgent(tools=protect_tools([get_ticket_tool, search_tool]), llm=llm)

A blocked call returns an error ToolOutput with PatchLoop's message. The wrapped tool keeps
the original name, description and schema, so the model sees the same tool.
"""

from llama_index.core.tools import ToolOutput
from llama_index.core.tools.types import AsyncBaseTool

from patchloop.sdk.runtime import Blocked, client


class ProtectedTool(AsyncBaseTool):
    def __init__(self, tool, patchloop=None):
        self._tool, self.patchloop = tool, patchloop

    @property
    def metadata(self):
        return self._tool.metadata

    def _arguments(self, args, kwargs):
        if kwargs:
            return dict(kwargs)
        if len(args) == 1:
            return dict(args[0]) if isinstance(args[0], dict) else {"input": args[0]}
        return {}

    def _refusal(self, arguments, blocked):
        return ToolOutput(content=str(blocked), tool_name=self.metadata.name, raw_input=arguments,
                          raw_output=str(blocked), is_error=True)

    def call(self, *args, **kwargs):
        arguments = self._arguments(args, kwargs)
        try:
            return (self.patchloop or client()).run(self.metadata.name, arguments,
                                                    lambda: self._tool.call(*args, **kwargs))
        except Blocked as blocked:
            return self._refusal(arguments, blocked)

    async def acall(self, *args, **kwargs):
        arguments = self._arguments(args, kwargs)
        inner = self._tool.acall if hasattr(self._tool, "acall") else None

        async def run():
            return await inner(*args, **kwargs) if inner else self._tool.call(*args, **kwargs)
        try:
            return await (self.patchloop or client()).arun(self.metadata.name, arguments, run)
        except Blocked as blocked:
            return self._refusal(arguments, blocked)


def protect_tools(tools, patchloop=None):
    return [ProtectedTool(tool, patchloop) for tool in tools]
