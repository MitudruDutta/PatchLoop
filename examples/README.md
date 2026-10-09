# Examples

PatchLoop on real open-source agents. Each folder has the agent, its rule set, the trial scripts, and a README with what we did and what happened.

| Example | Agent | Domain | What it shows |
|---|---|---|---|
| [coinbase-agentkit](coinbase-agentkit/) | Coinbase AgentKit with Strands and Nemotron | A wallet on the Base Sepolia testnet | Recipient ownership, a token allowlist, amount limits, consent, and the find, fix and prove loop; repeated trials on two models |
| [fhir-patient-assistant](fhir-patient-assistant/) | WSO2 FHIR MCP server with Strands and Nemotron | Patient health records on a public test server | Patient-scoped search with a JSON Pointer binding, and the limits of rules for generic tools |

Step-by-step walkthrough: [docs/guides/coinbase-agentkit.md](../docs/guides/coinbase-agentkit.md). How to write rules: [docs/guides/writing-rules.md](../docs/guides/writing-rules.md).
