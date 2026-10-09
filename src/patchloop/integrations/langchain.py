"""LangChain and LangGraph adapter.

    # LangChain v1 agents
    from patchloop.integrations.langchain import PatchLoopMiddleware
    agent = create_agent(model, tools, middleware=[PatchLoopMiddleware()])

    # LangGraph ToolNode
    from patchloop.integrations.langchain import wrap_tool_call, awrap_tool_call
    node = ToolNode(tools, wrap_tool_call=wrap_tool_call, awrap_tool_call=awrap_tool_call)

A blocked call returns an error ToolMessage with PatchLoop's message, so the agent keeps
running instead of crashing. Put the middleware last, so it checks the final arguments.
"""

from langchain_core.messages import ToolMessage

from patchloop.sdk.runtime import Blocked, client


def _refusal(request, blocked):
    call = request.tool_call
    return ToolMessage(content=str(blocked), tool_call_id=call["id"], name=call["name"], status="error")


def wrap_tool_call(request, handler, patchloop=None):
    call = request.tool_call
    try:
        return (patchloop or client()).run(call["name"], dict(call["args"]), lambda: handler(request))
    except Blocked as blocked:
        return _refusal(request, blocked)


async def awrap_tool_call(request, handler, patchloop=None):
    call = request.tool_call
    try:
        return await (patchloop or client()).arun(call["name"], dict(call["args"]), lambda: handler(request))
    except Blocked as blocked:
        return _refusal(request, blocked)


try:
    from langchain.agents.middleware import AgentMiddleware
except ImportError:  # langchain-core and langgraph without the langchain package
    AgentMiddleware = None

if AgentMiddleware is not None:
    class PatchLoopMiddleware(AgentMiddleware):
        def __init__(self, patchloop=None):
            super().__init__()
            self.patchloop = patchloop

        def wrap_tool_call(self, request, handler):
            return wrap_tool_call(request, handler, self.patchloop)

        async def awrap_tool_call(self, request, handler):
            return await awrap_tool_call(request, handler, self.patchloop)
