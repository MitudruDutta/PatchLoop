# Hosted API workstream

**Owner:** platform partner. **Requirements:** [docs/prd/platform.md](../../docs/prd/platform.md).

This directory will hold the hosted control plane: organizations, projects, members, API keys, run and evidence storage, webhooks, usage metering and billing integration.

## Boundaries

- The control plane never executes customer tools or customer guard code. The open-source runner (the `patchloop` package) does that in the customer's environment and uploads evidence.
- Store API keys only as hashes. Keep provider keys on the runner side unless the customer chooses managed credits.
- Depend on the `patchloop` package through its public SDK API, not on internal modules.
- Deploy separately from the SDK. Keep service dependencies out of `pyproject.toml` at the repository root.
