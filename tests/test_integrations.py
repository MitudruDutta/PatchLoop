"""Each adapter inside its real framework: allowed calls run, blocked calls return the refusal and never run."""

import asyncio
import functools

import pytest

from patchloop import REFUSAL, PatchLoop, Ruleset, identify

RULES = Ruleset({
    "schema_version": 1, "name": "tickets", "version": "1",
    "resources": {"ticket": {"owner_field": "owner"}},
    "tools": {"get_ticket": {"access": "scoped", "effect": "none",
                             "resources": [{"argument": "ticket_id", "resource": "ticket"}]}},
})
TICKETS = {"1": {"owner": "ada", "text": "mine"}, "2": {"owner": "bo", "text": "secret"}}


def guard(tmp_path):
    return PatchLoop(RULES, facts=lambda resource, identifier: TICKETS.get(identifier), mode="enforce",
                     recordings=tmp_path / "calls.jsonl")


def test_fastmcp_middleware_protects_every_tool(tmp_path):
    pytest.importorskip("fastmcp")
    from fastmcp import Client, FastMCP
    from patchloop.integrations.fastmcp import PatchLoopMiddleware

    ran = []
    mcp = FastMCP("helpdesk", middleware=[PatchLoopMiddleware(guard(tmp_path))])

    @mcp.tool
    def get_ticket(ticket_id: str) -> str:
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    @mcp.tool
    def export_all() -> str:
        ran.append("export_all")
        return str(TICKETS)

    async def main():
        with identify("ada"):
            async with Client(mcp) as client:
                return [(await client.call_tool(name, args, raise_on_error=False)).content[0].text
                        for name, args in [("get_ticket", {"ticket_id": "1"}), ("get_ticket", {"ticket_id": "2"}),
                                           ("get_ticket", {"ticket_id": "999"}), ("export_all", {})]]

    assert asyncio.run(main()) == ["mine", REFUSAL, REFUSAL, REFUSAL]
    assert ran == ["1"]


def test_langgraph_tool_node_returns_refusal_instead_of_crashing(tmp_path):
    pytest.importorskip("langgraph")
    from langchain_core.messages import AIMessage
    from langchain_core.tools import tool
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode
    from patchloop.integrations.langchain import awrap_tool_call, wrap_tool_call

    ran = []

    @tool
    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    protect = guard(tmp_path)
    node = ToolNode([get_ticket], wrap_tool_call=functools.partial(wrap_tool_call, patchloop=protect),
                    awrap_tool_call=functools.partial(awrap_tool_call, patchloop=protect))
    graph = StateGraph(MessagesState)
    graph.add_node("tools", node)
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    app = graph.compile()

    def call(ticket_id):
        message = AIMessage(content="", tool_calls=[{"name": "get_ticket", "args": {"ticket_id": ticket_id}, "id": "c" + ticket_id}])
        return app.invoke({"messages": [message]})["messages"][-1]

    with identify("ada"):
        assert call("1").content == "mine"
        refused = call("2")
        assert (refused.content, refused.status) == (REFUSAL, "error")

        async def acall():
            message = AIMessage(content="", tool_calls=[{"name": "get_ticket", "args": {"ticket_id": "2"}, "id": "a2"}])
            return (await app.ainvoke({"messages": [message]}))["messages"][-1].content
        assert asyncio.run(acall()) == REFUSAL
    assert ran == ["1"]


def test_langchain_create_agent_middleware(tmp_path):
    pytest.importorskip("langchain.agents.middleware")
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.tools import tool
    from patchloop.integrations.langchain import PatchLoopMiddleware

    class ScriptedModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    ran = []

    @tool
    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    model = ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_ticket", "args": {"ticket_id": "2"}, "id": "c2"}]),
        AIMessage(content="I cannot open that ticket."),
    ])
    agent = create_agent(model, [get_ticket], middleware=[PatchLoopMiddleware(guard(tmp_path))])
    with identify("ada"):
        messages = agent.invoke({"messages": [HumanMessage("Show me ticket 2")]})["messages"]
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    assert [m.content for m in tool_messages] == [REFUSAL]
    assert messages[-1].content == "I cannot open that ticket."
    assert ran == []


def test_strands_hooks_cancel_blocked_calls_and_record_outcomes(tmp_path):
    pytest.importorskip("strands")
    from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookRegistry
    from patchloop.integrations.strands import PatchLoopHooks

    protect = guard(tmp_path)
    registry = HookRegistry()
    PatchLoopHooks(protect).register_hooks(registry)

    seen = []

    def before(ticket_id):
        seen.append(ticket_id)
        use = {"toolUseId": f"u{ticket_id}-{len(seen)}", "name": "get_ticket", "input": {"ticket_id": ticket_id}}
        event = BeforeToolCallEvent(agent=None, selected_tool=None, tool_use=use, invocation_state={})
        registry.invoke_callbacks(event)
        return event

    with identify("ada"):
        allowed, blocked, failing = before("1"), before("2"), before("1")
    assert allowed.cancel_tool is False and failing.cancel_tool is False
    assert blocked.cancel_tool == REFUSAL
    for event, status in ((allowed, "success"), (failing, "error")):
        registry.invoke_callbacks(AfterToolCallEvent(agent=None, selected_tool=None, tool_use=event.tool_use,
                                                     invocation_state={}, result={"status": status, "content": []}))
    outcomes = [line.split('"outcome": "')[1].split('"')[0] for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert outcomes == ["blocked", "ok", "error"]
