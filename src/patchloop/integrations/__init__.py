"""Framework adapters, and wrap(), which picks the right one for an object."""

import inspect

from patchloop.sdk.runtime import client

SUPPORTED = """patchloop.wrap() accepts:
  a function or method       -> wrapped with patchloop.tool
  a FastMCP server           -> middleware added
  a Strands Agent            -> hooks added
  a Google ADK LlmAgent      -> tool callbacks added
  an OpenAI Agents Agent or FunctionTool -> function tools wrapped
  a LlamaIndex tool          -> wrapped tool returned
  a Pydantic AI toolset      -> wrapped toolset returned
  an MCP ClientSession       -> wrapped session returned
  ClaudeAgentOptions         -> hooks added
  a list or tuple of these
For LangChain or LangGraph, pass PatchLoopMiddleware or wrap_tool_call from
patchloop.integrations.langchain to the agent or ToolNode. For CrewAI, call
patchloop.integrations.crewai.install()."""


def _is(obj, module_prefix, *class_names):
    return any(cls.__module__.startswith(module_prefix) and cls.__name__ in class_names for cls in type(obj).__mro__)


def wrap(obj, patchloop=None):
    """Protect a framework object with the matching adapter and return what to use in its place."""
    if isinstance(obj, (list, tuple)):
        return type(obj)(wrap(item, patchloop) for item in obj)
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return (patchloop or client()).tool(obj)
    if _is(obj, "fastmcp", "FastMCP"):
        from patchloop.integrations.fastmcp import PatchLoopMiddleware
        obj.add_middleware(PatchLoopMiddleware(patchloop))
        return obj
    if _is(obj, "strands", "Agent"):
        from patchloop.integrations.strands import PatchLoopHooks
        obj.hooks.add_hook(PatchLoopHooks(patchloop))
        return obj
    if _is(obj, "google.adk", "LlmAgent"):
        from patchloop.integrations.google_adk import protect
        return protect(obj, patchloop)
    if _is(obj, "agents", "Agent"):
        from patchloop.integrations.openai_agents import protect
        return protect(obj, patchloop)
    if _is(obj, "agents", "FunctionTool"):
        from patchloop.integrations.openai_agents import protect_tool
        return protect_tool(obj, patchloop)
    if _is(obj, "llama_index", "BaseTool"):
        from patchloop.integrations.llamaindex import ProtectedTool
        return ProtectedTool(obj, patchloop)
    if _is(obj, "pydantic_ai", "AbstractToolset"):
        from patchloop.integrations.pydantic_ai import PatchLoopToolset
        return PatchLoopToolset(obj, patchloop)
    if _is(obj, "mcp", "ClientSession"):
        from patchloop.integrations.mcp import protect_session
        return protect_session(obj, patchloop)
    if _is(obj, "claude_agent_sdk", "ClaudeAgentOptions"):
        from patchloop.integrations.claude_agent_sdk import PatchLoopHooks
        hooks = dict(obj.hooks or {})
        for event, matchers in PatchLoopHooks(patchloop).hooks().items():
            hooks[event] = list(hooks.get(event, [])) + matchers
        obj.hooks = hooks
        return obj
    raise TypeError(f"patchloop.wrap() does not support {type(obj).__module__}.{type(obj).__name__}\n\n{SUPPORTED}")
