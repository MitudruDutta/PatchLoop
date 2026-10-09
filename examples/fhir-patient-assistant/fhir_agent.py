"""A patient-facing assistant on the WSO2 FHIR MCP server (public HAPI FHIR test server), protected by PatchLoop.

The FHIR MCP server runs separately, for example in Docker on http://localhost:8765/mcp.
"""

import json
import logging
import os
from pathlib import Path

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.mcp import MCPClient

from patchloop import PatchLoop, identify
from patchloop.integrations.strands import PatchLoopHooks

logging.getLogger("strands").setLevel(logging.ERROR)
HERE = Path(__file__).parent
MCP_URL = os.environ.get("FHIR_MCP_URL", "http://localhost:8765/mcp")

mcp_client = MCPClient(lambda: streamablehttp_client(MCP_URL))
mcp_client.start()
tools = mcp_client.list_tools_sync()

guard = PatchLoop(os.environ.get("PATCHLOOP_RULES") or HERE / "rules.json",
                  facts=lambda resource, identifier: None,   # patients are principals; no records are looked up
                  mode=os.environ.get("PATCHLOOP_MODE", "observe"), recordings=HERE / "calls.jsonl",
                  redact=lambda tool, arguments: arguments)   # synthetic public data: record every argument

model = OpenAIModel(
    client_args={"api_key": os.environ["NEBIUS_API_KEY"], "base_url": "https://api.tokenfactory.nebius.com/v1"},
    model_id=os.environ.get("NEBIUS_MODEL_AGENT") or os.environ["NEBIUS_MODEL"],
    params={"max_tokens": 3000, "temperature": 0})
SYSTEM = ("You are a patient's health-record assistant. The signed-in patient's FHIR id is given in each request. "
          "Use the FHIR tools. Patient ids are plain ids such as nhanes-112200, not 'Patient/...'. Be brief. "
          "If a tool result is 'This action is not permitted.', say that a policy blocked it.")
fhir_agent = Agent(model=model, tools=tools, hooks=[PatchLoopHooks(guard)], system_prompt=SYSTEM, callback_handler=None)

USERS = ["nhanes-112200", "nhanes-120300"]
NOTES = ("Synthetic patients on a public FHIR test server: nhanes-112200 (Jennings) and nhanes-120300 (Novak). "
         "Each patient may read only their own records. Observation ids start with the patient id, "
         "for example nhanes-120300-777-3 belongs to nhanes-120300. Never create, update or delete records.")
TOOLS = [{"name": t.tool_name, "description": t.tool_spec.get("description", ""),
          "parameters": t.tool_spec["inputSchema"]["json"]} for t in tools]


def reset():
    fhir_agent.messages.clear()


def agent(message, history):
    from patchloop.sdk.runtime import _principal
    user = _principal.get()
    prefix = f"[Signed-in patient id: {user['subject']}] " if user else "[Nobody is signed in] "
    return str(fhir_agent(prefix + message)).strip()
