# PatchLoop

PatchLoop puts authorization rules at the tool boundary of an AI agent. The agent's model chooses tool names and arguments. Your application, not the model, says who is logged in, who owns which record, and whether the user confirmed an action. PatchLoop checks every tool call against a declarative rule set, records the decision, and in enforce mode blocks the call before the tool runs.

It works with any agent framework: wrap plain Python tools with a decorator, or add one adapter to FastMCP, LangChain, LangGraph or Strands.

**Status (8 October 2026):** version 0.1 in development. The rule engine, the Python SDK runtime, framework adapters, recordings, `patchloop report`, `patchloop doctor` and the language-neutral specification are implemented and tested. Rule set proposal from recordings, adversarial testing against a test environment, and the hosted control plane are next.

## Install

Python 3.10 or later. The core SDK uses only the standard library. Adapters are extras.

```bash
python -m pip install -e '.[dev]'          # everything, for development
python -m pip install -e '.[langchain]'    # or: fastmcp, strands
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

One adapter protects every tool the framework runs, including tools you forgot to list in the rule set (they are never allowed). A blocked call returns the refusal text to the model as a tool error, so the agent keeps running.

```python
# FastMCP: every tool on the server
from patchloop.integrations.fastmcp import PatchLoopMiddleware
mcp = FastMCP("notes", middleware=[PatchLoopMiddleware()])

# LangChain v1 agents
from patchloop.integrations.langchain import PatchLoopMiddleware
agent = create_agent(model, tools, middleware=[PatchLoopMiddleware()])

# LangGraph
from patchloop.integrations.langchain import wrap_tool_call, awrap_tool_call
node = ToolNode(tools, wrap_tool_call=wrap_tool_call, awrap_tool_call=awrap_tool_call)

# Strands Agents
from patchloop.integrations.strands import PatchLoopHooks
agent = Agent(model=model, tools=tools, hooks=[PatchLoopHooks()])
```

Put the adapter last among middleware or hooks, so it checks the arguments the tool will receive.

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

## Rule sets

A resource is the principal itself (`"principal": true`), a record with an owner and/or tenant field, or a child of another resource (`"parent": {"resource": "ticket", "field": "ticket_id"}`). A tool is `public`, `authenticated`, or `scoped` to one or more of its arguments. A nested argument is named with a JSON Pointer, for example `"/ticket/id"`. The full rules, including the evaluation order and every reason code, are in [spec/rule-semantics.md](spec/rule-semantics.md).

## Reports

Every call writes one JSON line to the recordings file. By default only the arguments that the rule set uses are kept; the rest are replaced with `[redacted]`. Pass `redact=lambda tool, arguments: ...` to change that. An error is recorded by its exception type only, never its message.

```bash
patchloop report calls.jsonl            # calls, decisions and reasons per tool
patchloop report calls.jsonl --json
patchloop report calls.jsonl --strict   # exit 1 if any call was not allowed (for CI)
```

## Specification and other SDKs

`spec/` is the contract for every SDK: the rule semantics, JSON schemas for rule sets and recordings, and conformance vectors. The TypeScript SDK must pass the same vectors. See [spec/README.md](spec/README.md).

## Model providers

`patchloop providers` checks access to [Nebius Token Factory](https://docs.tokenfactory.nebius.com/) (NVIDIA Nemotron models) and [Tavily Search](https://docs.tavily.com/), which later stages use to propose rule sets and test agents. Keys come from environment variables only; `.env.example` lists their names. Never commit keys.

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
  integrations/       FastMCP, LangChain/LangGraph and Strands adapters
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
