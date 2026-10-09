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


def test_mcp_client_session_is_checked_before_the_server_sees_the_call(tmp_path):
    pytest.importorskip("fastmcp")
    from fastmcp import Client, FastMCP
    from patchloop.integrations.mcp import protect_session

    ran = []
    server = FastMCP("helpdesk")

    @server.tool
    def get_ticket(ticket_id: str) -> str:
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    async def main():
        async with Client(server) as client:
            session = protect_session(client.session, guard(tmp_path))
            with identify("ada"):
                allowed = await session.call_tool("get_ticket", {"ticket_id": "1"})
                refused = await session.call_tool("get_ticket", {"ticket_id": "2"})
            return allowed, refused, [tool.name for tool in (await session.list_tools()).tools] == ["get_ticket"]

    allowed, refused, passthrough = asyncio.run(main())
    assert (allowed.isError, allowed.content[0].text) == (False, "mine")
    assert (refused.isError, refused.content[0].text) == (True, REFUSAL)
    assert ran == ["1"] and passthrough

    observe = PatchLoop(RULES, facts=lambda resource, identifier: TICKETS.get(identifier),
                        recordings=tmp_path / "observe.jsonl")

    async def server_error():
        async with Client(server) as client:
            with identify("ada"):
                return await protect_session(client.session, observe).call_tool("get_ticket", {"ticket_id": "999"})

    assert asyncio.run(server_error()).isError
    assert '"outcome": "error"' in (tmp_path / "observe.jsonl").read_text()


def test_claude_agent_sdk_hooks_deny_with_refusal_and_record_outcomes(tmp_path):
    pytest.importorskip("claude_agent_sdk")
    from claude_agent_sdk import ClaudeAgentOptions
    from patchloop.integrations.claude_agent_sdk import PatchLoopHooks

    hooks = PatchLoopHooks(guard(tmp_path), name=lambda tool_name: tool_name.removeprefix("mcp__helpdesk__"))
    options = ClaudeAgentOptions(hooks=hooks.hooks())
    assert set(options.hooks) == {"PreToolUse", "PostToolUse", "PostToolUseFailure"}

    def pre(ticket_id, use_id):
        return {"hook_event_name": "PreToolUse", "tool_name": "mcp__helpdesk__get_ticket", "session_id": "s",
                "transcript_path": "", "cwd": "", "tool_input": {"ticket_id": ticket_id}, "tool_use_id": use_id}

    async def main():
        with identify("ada"):
            allowed = await hooks.pre_tool_use(pre("1", "u1"), "u1", {})
            denied = await hooks.pre_tool_use(pre("2", "u2"), "u2", {})
            bash = await hooks.pre_tool_use({**pre("1", "u3"), "tool_name": "Bash"}, "u3", {})
        await hooks.post_tool_use({**pre("1", "u1"), "tool_response": "mine"}, "u1", {})
        return allowed, denied, bash

    allowed, denied, bash = asyncio.run(main())
    assert allowed == {}
    assert denied["hookSpecificOutput"] == {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                            "permissionDecisionReason": REFUSAL}
    assert bash["hookSpecificOutput"]["permissionDecision"] == "deny", "unlisted built-in tools are never allowed"
    outcomes = [line.split('"outcome": "')[1].split('"')[0] for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert outcomes == ["blocked", "blocked", "ok"]


def test_google_adk_agent_gets_refusal_as_tool_result(tmp_path):
    pytest.importorskip("google.adk")
    from google.adk.agents import LlmAgent
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from patchloop.integrations.google_adk import protect

    ran = []

    def get_ticket(ticket_id: str) -> dict:
        """Read a support ticket."""
        ran.append(ticket_id)
        return {"text": TICKETS[ticket_id]["text"]}

    class ScriptedLlm(BaseLlm):
        ticket: str = "1"

        async def generate_content_async(self, llm_request, stream=False):
            responses = [part.function_response.response for content in llm_request.contents
                         for part in content.parts or [] if part.function_response]
            if responses:
                yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=json.dumps(responses[-1]))]))
            else:
                call = types.FunctionCall(name="get_ticket", args={"ticket_id": self.ticket})
                yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=call)]))

    async def ask(ticket):
        agent = protect(LlmAgent(name="support", model=ScriptedLlm(model="scripted", ticket=ticket), tools=[get_ticket]),
                        guard(tmp_path))
        runner = InMemoryRunner(agent=agent, app_name="helpdesk")
        session = await runner.session_service.create_session(app_name="helpdesk", user_id="ada")
        texts = []
        with identify("ada"):
            async for event in runner.run_async(user_id="ada", session_id=session.id,
                                                new_message=types.Content(role="user", parts=[types.Part(text="hi")])):
                texts += [part.text for part in (event.content.parts if event.content else []) if part.text]
        return json.loads(texts[-1])

    import json
    assert asyncio.run(ask("1")) == {"text": "mine"}
    assert asyncio.run(ask("2")) == {"error": REFUSAL}
    assert ran == ["1"]


def test_llamaindex_protected_tool_keeps_metadata_and_refuses(tmp_path):
    pytest.importorskip("llama_index.core")
    from llama_index.core.tools import FunctionTool
    from patchloop.integrations.llamaindex import protect_tools

    ran = []

    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    (tool,) = protect_tools([FunctionTool.from_defaults(fn=get_ticket)], guard(tmp_path))
    assert tool.metadata.name == "get_ticket" and "ticket_id" in tool.metadata.get_parameters_dict()["properties"]
    with identify("ada"):
        assert tool.call(ticket_id="1").content == "mine"
        refused = tool.call(ticket_id="2")
        arefused = asyncio.run(tool.acall(ticket_id="2"))
    assert (refused.content, refused.is_error, arefused.content) == (REFUSAL, True, REFUSAL)
    assert ran == ["1"]


def test_openai_agents_runner_gets_refusal_as_tool_output(tmp_path):
    pytest.importorskip("agents")
    from agents import Agent, Runner, function_tool
    from agents.items import ModelResponse
    from agents.models.interface import Model
    from agents.usage import Usage
    from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
    from patchloop.integrations.openai_agents import protect

    ran = []

    @function_tool
    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    class ScriptedModel(Model):
        def __init__(self, ticket):
            self.ticket = ticket

        async def get_response(self, system_instructions, input, *args, **kwargs):
            outputs = [item["output"] for item in input if isinstance(item, dict) and item.get("type") == "function_call_output"]
            if outputs:
                text = ResponseOutputText(type="output_text", text=str(outputs[-1]), annotations=[])
                item = ResponseOutputMessage(id="m", type="message", role="assistant", status="completed", content=[text])
            else:
                item = ResponseFunctionToolCall(id="f", call_id="call-1", type="function_call", name="get_ticket",
                                                arguments=json.dumps({"ticket_id": self.ticket}))
            return ModelResponse(output=[item], usage=Usage(), response_id=None)

        def stream_response(self, *args, **kwargs):
            raise NotImplementedError

    import json
    protect_with = guard(tmp_path)

    def run(ticket):
        agent = protect(Agent(name="support", tools=[get_ticket], model=ScriptedModel(ticket)), protect_with)
        with identify("ada"):
            return asyncio.run(Runner.run(agent, "hi")).final_output

    assert run("1") == "mine"
    assert run("2") == REFUSAL
    assert ran == ["1"]


def test_pydantic_ai_toolset_refuses_inside_a_real_agent_run(tmp_path):
    pytest.importorskip("pydantic_ai")
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.toolsets import FunctionToolset
    from patchloop.integrations.pydantic_ai import PatchLoopToolset

    ran = []

    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        ran.append(ticket_id)
        return TICKETS[ticket_id]["text"]

    def scripted(ticket):
        def model(messages, info):
            returns = [part.content for message in messages for part in getattr(message, "parts", [])
                       if isinstance(part, ToolReturnPart)]
            if returns:
                return ModelResponse(parts=[TextPart(str(returns[-1]))])
            return ModelResponse(parts=[ToolCallPart("get_ticket", {"ticket_id": ticket})])
        return FunctionModel(model)

    toolset = PatchLoopToolset(FunctionToolset([get_ticket]), guard(tmp_path))
    with identify("ada"):
        assert Agent(scripted("1"), toolsets=[toolset]).run_sync("hi").output == "mine"
        assert Agent(scripted("2"), toolsets=[toolset]).run_sync("hi").output == REFUSAL
    assert ran == ["1"]


def test_crewai_hooks_block_through_crewai_dispatch_and_fail_closed(tmp_path):
    pytest.importorskip("crewai")
    from crewai.hooks.tool_hooks import ToolCallHookContext, run_after_tool_call_hooks, run_before_tool_call_hooks
    from crewai.tools import tool as crewai_tool
    from patchloop.integrations import crewai as adapter

    @crewai_tool("get_ticket")
    def get_ticket(ticket_id: str) -> str:
        """Read a support ticket."""
        return TICKETS[ticket_id]["text"]

    def call(ticket_id, patchloop):
        tool_input = {"ticket_id": ticket_id}
        before = ToolCallHookContext(tool_name="get_ticket", tool_input=tool_input, tool=get_ticket)
        blocked = run_before_tool_call_hooks(before)
        result = "Tool execution blocked by hook. Tool: get_ticket" if blocked else TICKETS[ticket_id]["text"]
        after = ToolCallHookContext(tool_name="get_ticket", tool_input=tool_input, tool=get_ticket,
                                    tool_result=result, raw_tool_result=result)
        return blocked, run_after_tool_call_hooks(after) or result

    uninstall = adapter.install(guard(tmp_path))
    try:
        with identify("ada"):
            assert call("1", None) == (False, "mine")
            assert call("2", None) == (True, REFUSAL)
        broken = PatchLoop(RULES, facts=TICKETS.get, mode="enforce", identity=lambda: True)  # identity raises TypeError
        uninstall()
        uninstall = adapter.install(broken)
        assert call("1", None) == (True, REFUSAL), "an error in the check must block, not fail open"
    finally:
        uninstall()


def test_wrap_picks_the_adapter_and_rejects_unknown_objects(tmp_path):
    import patchloop
    protect = guard(tmp_path)
    wrapped = patchloop.wrap(lambda ticket_id: TICKETS[ticket_id]["text"], protect)
    with pytest.raises(ValueError):
        patchloop.wrap([lambda ticket_id: None], protect)  # second lambda has the same name
    with identify("ada"):
        with pytest.raises(patchloop.Blocked):
            wrapped("2")
    with pytest.raises(TypeError) as rejected:
        patchloop.wrap(object(), protect)
    assert "For CrewAI, call" in str(rejected.value)
    fastmcp = pytest.importorskip("fastmcp")
    server = patchloop.wrap(fastmcp.FastMCP("x"), protect)
    assert any(type(m).__name__ == "PatchLoopMiddleware" for m in server.middleware)


def test_adapters_tell_the_model_when_only_confirmation_is_missing(tmp_path):
    pytest.importorskip("fastmcp")
    from fastmcp import Client, FastMCP
    from patchloop import CONSENT_NEEDED
    from patchloop.integrations.fastmcp import PatchLoopMiddleware

    rules = Ruleset({"schema_version": 1, "name": "t", "version": "1",
                     "resources": {"ticket": {"owner_field": "owner"}},
                     "tools": {"close_ticket": {"access": "scoped", "effect": "state_write", "consent": True,
                                                "resources": [{"argument": "ticket_id", "resource": "ticket"}]}}})
    guard = PatchLoop(rules, facts=lambda resource, identifier: TICKETS.get(identifier), mode="enforce")
    server = FastMCP("helpdesk", middleware=[PatchLoopMiddleware(guard)])

    @server.tool
    def close_ticket(ticket_id: str) -> str:
        return "closed"

    async def main():
        with identify("ada"):
            async with Client(server) as client:
                own = await client.call_tool("close_ticket", {"ticket_id": "1"}, raise_on_error=False)
                other = await client.call_tool("close_ticket", {"ticket_id": "2"}, raise_on_error=False)
                return own.content[0].text, other.content[0].text

    assert asyncio.run(main()) == (CONSENT_NEEDED, REFUSAL)
