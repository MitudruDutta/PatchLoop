# PatchLoop

PatchLoop puts authorization rules at the tool boundary of an AI agent. The agent's model chooses tool names and arguments. Your application, not the model, says who is logged in, who owns which record, and whether the user confirmed an action. PatchLoop checks every tool call against a declarative rule set, records the decision, and in enforce mode blocks the call before the tool runs.

It works with any agent framework: wrap plain Python tools with a decorator, or call `patchloop.wrap()` on your framework object. Adapters exist for FastMCP, MCP clients, LangChain, LangGraph, Strands, the OpenAI Agents SDK, the Claude Agent SDK, Google ADK, LlamaIndex, Pydantic AI and CrewAI.

**Status (8 October 2026):** version 0.1 in development. The rule engine, the Python SDK runtime, framework adapters, recordings, `patchloop report`, `patchloop doctor`, the language-neutral specification, and the find, fix and prove loop (`patchloop test`, `propose`, `replay`) are implemented and tested. The hosted control plane, the TypeScript SDK and more adapters are next.

## Install

Python 3.10 or later. The core SDK uses only the standard library. Each adapter is an extra: `fastmcp`, `mcp`, `langchain`, `strands`, `openai-agents`, `claude-agent-sdk`, `google-adk`, `llamaindex`, `pydantic-ai`, `crewai`. Some frameworks pin conflicting dependencies, so install only the ones you use.

```bash
python -m pip install -e '.[dev]'               # core and tests
python -m pip install -e '.[dev,langchain]'     # plus one adapter's framework
python -m pytest -q
```

## Quick start

Describe your resources and tools in a rule set (`rules.json`):

```json
{
  "schema_version": 1,
  "name": "notes",
  "version": "1",
  "resources": {
    "user": {"principal": true},
    "note": {"owner_field": "owner_id", "tenant_field": "org_id"}
  },
  "tools": {
    "search_help": {"access": "public", "effect": "none"},
    "read_note": {"access": "scoped", "effect": "none",
                  "resources": [{"argument": "note_id", "resource": "note"}]},
    "delete_note": {"access": "scoped", "effect": "state_write", "consent": true,
                    "resources": [{"argument": "note_id", "resource": "note"}]}
  }
}
```

Initialize once, protect the tools, and bind the logged-in user per request:

```python
import patchloop
from patchloop import Blocked

NOTES = {"n1": {"owner_id": "ada", "org_id": "acme", "text": "mine"},
         "n2": {"owner_id": "bo", "org_id": "acme", "text": "not mine"}}

patchloop.init("rules.json", facts=lambda resource, record_id: NOTES.get(record_id),
               mode="enforce", recordings="calls.jsonl")

@patchloop.tool
def read_note(note_id: str) -> str:
    return NOTES[note_id]["text"]

@patchloop.tool
def delete_note(note_id: str) -> str:
    return NOTES.pop(note_id)["text"]

with patchloop.identify(subject="ada", tenant="acme"):    # from your own login, never from the model
    print(read_note("n1"))                                # allowed: ada owns n1
    try:
        read_note("n2")                                   # blocked: the reason is not_owner
    except Blocked as blocked:
        print(blocked)                                    # "This action is not permitted."
    patchloop.confirm("delete_note", {"note_id": "n1"})  # the user said yes to this exact action
    print(delete_note("n1"))                              # allowed once; the grant is used up
```

Give the wrapped functions to your agent framework as usual. Async tools and async `facts` work too.

## Framework adapters

One adapter protects every tool the framework runs, including tools you forgot to list in the rule set (they are never allowed). A blocked call returns the refusal text to the model as a tool error, so the agent keeps running. The simplest way is `patchloop.wrap()`, which picks the adapter:

```python
mcp = patchloop.wrap(FastMCP("notes"))         # FastMCP server: middleware added
agent = patchloop.wrap(Agent(...))             # Strands, Google ADK or OpenAI Agents SDK agent
tools = patchloop.wrap([tool_a, tool_b])       # functions, LlamaIndex tools
session = patchloop.wrap(client_session)       # MCP ClientSession: calls to servers you do not run
```

| Framework | Explicit form | How a call is checked |
|---|---|---|
| FastMCP | `FastMCP(..., middleware=[PatchLoopMiddleware()])` | Server middleware, before every tool |
| MCP clients | `protect_session(session)` | Before the request leaves for the server |
| LangChain v1 | `create_agent(..., middleware=[PatchLoopMiddleware()])` | `wrap_tool_call` middleware |
| LangGraph | `ToolNode(tools, wrap_tool_call=wrap_tool_call, awrap_tool_call=awrap_tool_call)` | ToolNode wrapper |
| Strands | `Agent(..., hooks=[PatchLoopHooks()])` | `BeforeToolCallEvent` cancels the call |
| OpenAI Agents SDK | `protect(agent)` | Each function tool's invocation is wrapped. Hosted tools run at OpenAI and are not covered |
| Claude Agent SDK | `ClaudeAgentOptions(hooks=PatchLoopHooks().hooks())` | `PreToolUse` hook denies; it also gates built-in tools such as Bash, so list the ones you allow |
| Google ADK | `protect(agent)` | `before_tool_callback` skips the tool |
| LlamaIndex | `protect_tools([...])` | Wrapped tools with the same name and schema |
| Pydantic AI | `Agent(..., toolsets=[PatchLoopToolset(toolset)])` | Toolset wrapper |
| CrewAI | `patchloop.integrations.crewai.install()` | Global tool hooks. CrewAI ignores errors raised in hooks, so this adapter blocks on any error itself |

Each adapter lives in `patchloop.integrations.<framework>` and is tested inside the real framework. Put the adapter last among middleware or hooks, so it checks the arguments the tool will receive.

## What PatchLoop needs from your application

| Input | How |
|---|---|
| Who is logged in | `with patchloop.identify(subject, tenant):` around each request or task, or pass `identity=` to `init()` |
| Who owns a record | `facts(resource, id)` returns the record as a dict, or `None` when it does not exist. Raise when the lookup cannot answer: the decision is then `indeterminate`. |
| What the user confirmed | `patchloop.confirm(tool, arguments)` when the user says yes to an exact action. A grant is used up by one call, expires after 10 minutes, and is bound to the user, the arguments and the rule set. For several processes, pass `consents=` an object with atomic `grant`, `has` and `take` backed by shared storage. |

`identify()` uses a context variable. asyncio tasks and frameworks that copy the context into worker threads (LangChain, LangGraph) see it. A bare `threading.Thread` does not: call `identify()` inside the thread.

## Modes

| Mode | Behavior |
|---|---|
| `observe` (default) | Runs every call and records the decision. Use it first, in production, to see what enforcement would change. |
| `warn` | Also logs a warning and calls `on_violation(decision)` for each call that is not allowed |
| `enforce` | Runs only allowed calls. Raises `Blocked` (a `PermissionError`) for the rest. |

Override per tool with `modes={"delete_note": "enforce"}`. `patchloop.check(tool, arguments)` returns a decision without running, recording or using up consent.

The model always gets the same text for a blocked call: `This action is not permitted.` The reason (`not_owner`, `resource_missing`, ...) goes only to `Blocked.decision` and the recordings, so the model cannot learn which records exist.

## Doctor

`patchloop doctor` finds setups that weaken protection without failing loudly: tools missing from the rule set, rule set entries that match no tool, bindings that name a parameter the tool does not have, state-changing tools without consent, and observe mode.

```bash
patchloop doctor myapp.agent           # a module that calls patchloop.init()
patchloop doctor myapp.agent:guard     # or a PatchLoop instance
```

Tools behind an adapter are not wrapped by PatchLoop; pass them to `patchloop.doctor(tools={"name": function_or_parameter_list})`.

## Find, fix and prove

Three commands close the loop. `test` and `propose` call an NVIDIA Nemotron model on [Nebius Token Factory](https://docs.tokenfactory.nebius.com/) (set `NEBIUS_API_KEY` and `NEBIUS_MODEL`); `propose` also reads public guidance through [Tavily](https://docs.tavily.com/) (`TAVILY_API_KEY`). These are paid requests. `replay` makes none.

Each role can use its own Nemotron model: `NEBIUS_MODEL_PROPOSER`, `NEBIUS_MODEL_PLANNER`, `NEBIUS_MODEL_CUSTOMER` and `NEBIUS_MODEL_JUDGE`, each falling back to `NEBIUS_MODEL`. A small model such as Nemotron Nano is enough for the customer; keep a larger one for proposing and judging. Plans, verdicts and drafts use Token Factory's JSON output, and every report includes token totals.

**Find: `patchloop test`.** A Nemotron tester plans scenarios (another user's records, another organization's records, no sign-in, changes without confirmation) and plays a customer against your agent, in a test environment. Every tool call is decided by the rule set. A call the rules do not allow is a finding. A Nemotron judge then reads each conversation for access that the rules allowed but should not have: a possible rule gap. Point it at a module that provides:

```python
guard = PatchLoop("rules.json", facts=lookup, mode="observe")   # or patchloop.init(...)
USERS = [{"subject": "ada", "tenant": "acme"}, {"subject": "bo", "tenant": "acme"}]
NOTES = "Ticket T1 belongs to ada, T2 to bo."                     # optional, helps the tester and judge
TOOLS = [...]   # optional tool catalog (OpenAI function format); needed when an adapter protects the tools

def agent(message: str, history: list[dict]) -> str: ...        # one turn of your agent
def reset(): ...                                                  # optional: restore test data
```

```bash
patchloop test myapp.test_target --scenarios 3 --turns 4 --report find.json
```

Use test data only: outside enforce mode, the agent's tools really run.

**Fix: `patchloop propose`.** Nemotron drafts a rule set from the tool catalog, record samples, your policy text, the current rules, the tester's findings and OWASP guidance that Tavily finds for the records your tools touch. Each draft is checked against the specification, the catalog and the samples, and the problems go back to the model. Nothing is activated: you review the draft.

```bash
patchloop propose --target myapp.test_target --samples samples.json --policy policy.md \
    --rules rules.json --findings find.json --recordings calls.jsonl --output rules.proposed.json
```

**Prove: `patchloop replay`.** Replays recorded calls against the draft and lists every call it would newly block or newly allow. It uses the lookups saved in the recordings. When the old rules never looked a record up, pass live facts. A call that cannot be replayed is reported as such, never guessed.

```bash
patchloop replay calls.jsonl --rules rules.proposed.json --facts myapp.test_target:guard.facts --fail-on newly_allowed
```

## Rule sets

A resource is the principal itself (`"principal": true`), a record with an owner and/or tenant field, or a child of another resource (`"parent": {"resource": "ticket", "field": "ticket_id"}`). A tool is `public`, `authenticated`, or `scoped` to one or more of its arguments. A nested argument is named with a JSON Pointer, for example `"/ticket/id"`. The full rules, including the evaluation order and every reason code, are in [spec/rule-semantics.md](spec/rule-semantics.md).

## Reports

Every call writes one JSON line to the recordings file. By default the recording keeps the arguments that the rule set uses, plus identifier values of arguments named like identifiers (`id`, `ticket_id`, `ticket_ids`, `ticketId`), so that a later rule set can be replayed. Every other value is replaced with `[redacted]`. Pass `redact=lambda tool, arguments: ...` to change that. An error is recorded by its exception type only, never its message.

```bash
patchloop report calls.jsonl            # calls, decisions and reasons per tool
patchloop report calls.jsonl --json
patchloop report calls.jsonl --strict   # exit 1 if any call was not allowed (for CI)
```

## Specification and other SDKs

`spec/` is the contract for every SDK: the rule semantics, JSON schemas for rule sets and recordings, and conformance vectors. The TypeScript SDK must pass the same vectors. See [spec/README.md](spec/README.md).

## Model providers

`patchloop providers` checks access to [Nebius Token Factory](https://docs.tokenfactory.nebius.com/) (NVIDIA Nemotron models) and [Tavily Search](https://docs.tavily.com/), which `test` and `propose` use. Keys come from environment variables only; `.env.example` lists their names. Never commit keys.

```bash
patchloop providers models
patchloop providers smoke
```

## Sandbox

`patchloop.sandbox` runs one generated Python function, `allow(context)`, in an isolated bubblewrap namespace or a locked-down Docker container (no network, read-only root, no capabilities, non-root user, resource limits). Production enforcement does not use it: rule sets are data, evaluated in process. It exists for experiments with generated code.

```bash
docker build -f docker/sandbox.Dockerfile -t patchloop-guard:local .
PATCHLOOP_SANDBOX=docker python -m pytest -q tests/test_sandbox.py
```

## Repository layout

```
spec/                 Rule semantics, JSON schemas, conformance vectors (shared by all SDKs)
src/patchloop/
  sdk/rules.py        Rule set validation and evaluation
  sdk/runtime.py      PatchLoop: tool wrapping, modes, hooks, recordings
  sdk/report.py       `patchloop report`
  sdk/doctor.py       `patchloop doctor`
  loop/               `patchloop test`, `propose` and `replay`: the find, fix and prove loop
  integrations/       Framework adapters and patchloop.wrap()
  sandbox/            Isolated execution of generated functions
  providers.py        Nebius Token Factory and Tavily clients
  cli.py              The `patchloop` command
tests/                Test suite (pytest)
docker/               Sandbox worker image
apps/                 Documentation and landing websites
rl/                   RL environment workstream
services/api/         Hosted control plane and API keys workstream
website/              Documentation website workstream
docs/                 Product requirements and research
```

## License

[MIT](LICENSE).
