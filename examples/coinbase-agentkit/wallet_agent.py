"""A Coinbase AgentKit wallet agent on Base Sepolia, protected by PatchLoop.

Run it:            python wallet_agent.py            (chat as alice; type /yes to confirm, /quit to leave)
Check it:          patchloop doctor wallet_agent
Test it:           patchloop test wallet_agent
"""

import json
import logging
import os
from pathlib import Path

from coinbase_agentkit import (AgentKit, AgentKitConfig, EthAccountWalletProvider, EthAccountWalletProviderConfig,
                               erc20_action_provider, wallet_action_provider)
from coinbase_agentkit_strands_agents import get_strands_tools
from eth_account import Account
from strands import Agent
from strands.models.openai import OpenAIModel

from patchloop import PatchLoop, identify
from patchloop.integrations.strands import PatchLoopHooks

logging.getLogger("strands").setLevel(logging.ERROR)
HERE = Path(__file__).parent


def load_wallet():
    """A local test key, saved so the wallet address stays the same between runs. Testnet only."""
    key_file = HERE / "wallet.key"
    if not key_file.exists():
        key_file.write_text(Account.create().key.hex())
        key_file.chmod(0o600)
    account = Account.from_key(key_file.read_text().strip())
    return EthAccountWalletProvider(EthAccountWalletProviderConfig(account=account, chain_id="84532"))


agentkit = AgentKit(AgentKitConfig(wallet_provider=load_wallet(),
                                   action_providers=[wallet_action_provider(), erc20_action_provider()]))
tools = get_strands_tools(agentkit)

# Facts: who saved each recipient address, and which tokens are approved. Addresses are compared in lower case.
def _load(name):
    return {address.lower(): record for address, record in json.loads((HERE / name).read_text()).items()}


FACTS = {"recipient": _load("address_book.json"), "token": _load("tokens.json")}


def facts(resource, address):
    return FACTS.get(resource, {}).get(str(address).lower())


# A payment that only lacks the user's confirmation waits here until the user types /yes.
pending = {}


def ask_user(tool, arguments, principal):
    pending.update(tool=tool, arguments=arguments, principal=principal)
    print(f"  [patchloop] Confirm {tool} {json.dumps(arguments)}? Type /yes, then ask again.")


guard = PatchLoop(os.environ.get("PATCHLOOP_RULES") or HERE / "rules.json", facts=facts,
                  mode=os.environ.get("PATCHLOOP_MODE", "observe"), recordings=HERE / "calls.jsonl",
                  on_consent_required=ask_user,
                  # Testnet only: record every argument, so that replay can check rules that bind new
                  # arguments. In production, keep the default, which records only what the rules use.
                  redact=lambda tool, arguments: arguments)

model = OpenAIModel(
    client_args={"api_key": os.environ["NEBIUS_API_KEY"], "base_url": "https://api.tokenfactory.nebius.com/v1"},
    model_id=os.environ.get("NEBIUS_MODEL_AGENT") or os.environ["NEBIUS_MODEL"],
    params={"max_tokens": 2048, "temperature": 0})
SYSTEM = ("You are a wallet assistant on the Base Sepolia testnet. Use the tools. Be brief. "
          "If a tool result is 'This action needs the user's confirmation.', ask the user to confirm. "
          "If a tool result is 'This action is not permitted.', tell the user that a policy blocked the action. "
          "Do not guess another reason.")
wallet_agent = Agent(model=model, tools=tools, hooks=[PatchLoopHooks(guard)], system_prompt=SYSTEM,
                     callback_handler=None)

# What `patchloop test` and `patchloop doctor` read from this module.
USERS = ["alice", "bob"]
NOTES = ("Testnet wallet shared by the test users alice and bob, so both may read its address and balances. "
         "Saved recipients: 0x1111111111111111111111111111111111111111 belongs to alice; "
         "0x2222222222222222222222222222222222222222 belongs to bob. Any other address is unknown. "
         "The only approved token is USDC at 0x036CbD53842c5426634e7929541eC2318f3dCF7e. "
         "A payment needs the signed-in user's own saved recipient, at most 0.01 ETH or 10 USDC, "
         "and their confirmation.")
TOOLS = [{"name": tool.tool_name, "description": tool.tool_spec["description"],
          "parameters": tool.tool_spec["inputSchema"]["json"]} for tool in tools]


def reset():
    wallet_agent.messages.clear()


def agent(message, history):
    """One turn. The Strands agent keeps its own conversation, so `history` is not needed."""
    return str(wallet_agent(message)).strip()


def chat(user):
    def show(line):
        decision = line["decision"]
        print(f"  [patchloop] {line['tool']} {json.dumps(line['arguments'])} -> "
              f"{decision['decision']} ({decision['reason']}), {'ran' if line['executed'] else 'blocked'}")

    guard.subscribe(show)
    print(f"Wallet agent, PatchLoop mode {guard.mode}, signed in as {user}. /yes confirms, /quit leaves.")
    with identify(user):
        while True:
            try:
                text = input("you> ").strip()
            except EOFError:
                break
            if text == "/quit":
                break
            if text == "/yes":
                if pending:
                    guard.confirm(pending["tool"], pending["arguments"], principal=pending["principal"])
                    print(f"Confirmed once: {pending['tool']} {json.dumps(pending['arguments'])}")
                    pending.clear()
                continue
            if text:
                print("agent>", agent(text, []))


if __name__ == "__main__":
    chat(os.environ.get("WALLET_USER", "alice"))
