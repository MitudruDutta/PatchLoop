# Writing PatchLoop rules for an agent

A rule set says which tool calls an agent may make, for which user, on which records. PatchLoop checks every call against it before the tool runs. Anything the rule set does not allow is blocked, including tools it does not list.

This guide gives the steps, the decisions for each tool, and the mistakes to avoid. The exact semantics are in [spec/rule-semantics.md](../../spec/rule-semantics.md). A complete worked example is the [Coinbase AgentKit wallet agent](../../examples/coinbase-agentkit/).

## The steps

1. **List the tools by their exact names.** Frameworks rename tools: AgentKit uses `<ClassName>_<method>` (for example `WalletActionProvider_native_transfer`), and the Claude Agent SDK names MCP tools `mcp__<server>__<tool>`. Print the names your framework gives the model, or run `patchloop doctor`. A tool that is not in the rule set is never allowed.
2. **Answer four questions for each tool** (next section).
3. **Describe your records as resources**: whose they are, and which field says so.
4. **Write the facts function**: it looks records up in your own database or API.
5. **Connect identity**: who is signed in comes from your authentication, through `patchloop.identify()`.
6. **Check the setup** with `patchloop doctor`.
7. **Observe, then enforce.** Run in `observe` mode, read `patchloop report`, fix the rules, then switch tools to `enforce` one by one with `modes={...}`.
8. **Test and keep testing.** Run `patchloop test` in a test environment. Review every finding, propose fixes with `patchloop propose`, and prove each change with `patchloop replay` before you deploy it.

## Four questions for each tool

| Question | If yes | Rule |
|---|---|---|
| Does it read data that belongs to a user or an organization, or change anything? | It is not public. | `access: "authenticated"` or `"scoped"` |
| Does an argument name a record (an ID, an address, an account)? | Bind that argument to a resource. | `access: "scoped"`, `resources: [{"argument": ..., "resource": ...}]` |
| Does it change, send or pay? | Ask the user first. | `effect: "state_write"` or `"external"`, `consent: true` |
| Does it move an amount, or use something that must be approved (a token, a domain)? | Limit the amount and fix the unit. | `limits` and an `allowlist` resource (rule format version 2) |

Choose the access level like this:

| Access | Use it when | Example |
|---|---|---|
| `public` | The tool exposes nothing about any user and changes nothing. No sign-in needed. | Search public help articles; look up a token's contract address by symbol |
| `authenticated` | Any signed-in user may call it, and it touches no record named in its arguments. The tool itself must scope its results to the user. | "List my tickets", where the tool reads the signed-in user, not an argument |
| `scoped` | An argument names a record. PatchLoop checks that the record belongs to the signed-in user. | Read ticket `T1`; pay recipient `0x1111...` |

## Describing records as resources

| Your record | Resource form | Check |
|---|---|---|
| The user's own ID, passed as an argument (`customer_id`, `user_id`) | `{"principal": true}` | The argument must equal the signed-in user (`not_principal` otherwise). No lookup. |
| A record with an owner and/or an organization | `{"owner_field": "customer_id", "tenant_field": "org"}` | The record's owner must be the user (`not_owner`), and its organization the user's (`wrong_tenant`). |
| A record that belongs to another record (an attachment of a ticket) | `{"parent": {"resource": "ticket", "field": "ticket_id"}}` | Access follows the parent, up to 4 links. |
| An approved item that only has to exist (a token, a domain, an account) | `{"allowlist": true}` (version 2) | An item not in the list is denied (`resource_missing`). |

Use the field names exactly as they appear in the records that your facts function returns.

## The facts function

`facts(resource, id)` returns the record as a dictionary, `None` when it does not exist, or raises an exception when it cannot answer.

- **Use the source of truth**: your database or API. Never let the model supply facts.
- **Normalize identifiers the way your tool does.** If the tool accepts `0xABC` and `0xabc` as the same address, look both up the same way (for example in lower case). Comparison is strict: the integer `7` and the string `"7"` are different identifiers.
- **Return `None` only for "does not exist".** If the lookup fails, raise. A failed lookup is `indeterminate`, which blocks in enforce mode. It never allows.
- **Async is fine** in async frameworks and adapters.

## Things to keep in mind

**Coverage**
- Bind every argument that names a record, including nested ones (`"argument": "/order/id"`, a JSON Pointer) and lists (`"cardinality": "many"`, every item is checked).
- A tool with an ID argument that you leave `authenticated` lets any signed-in user use any record. This is the most common mistake, and `patchloop test` finds it as a possible rule gap.
- New tools are blocked until you add them. When you add an integration or an action provider, update the rule set in the same change.

**What rules cannot see**
- **Results.** Rules check arguments, not what a tool returns. A search or list tool must scope its own query to the signed-in user (read the user from your session, not from an argument), or it can return other users' data even when the call is allowed.
- **Free-form arguments.** A SQL query, a shell command, a URL or an email body cannot be bound to a record. Split such tools into narrow tools with ID arguments, bind destinations to an allowlist (approved domains or recipients), and require consent.
- **Where data goes.** PatchLoop checks each call on its own. It does not follow data from one tool's output into another tool's input.
- **Roles.** Rule format versions 1 and 2 have no roles or admin overrides. Give staff agents their own rule set and their own PatchLoop instance, and keep staff tools out of customer-facing agents.
- **Tenant-local IDs.** An ID must be unique within its resource type. If two organizations can both have ticket `42`, use globally unique IDs.

**Money and other amounts**
- Limit amounts with `limits`, written as decimal strings (`"0.01"`). They are compared exactly.
- Fix the unit first. "At most 10 tokens" means nothing if the token can be anything: 10 test USDC is not 10 WETH. Bind the token argument to an `allowlist` resource.
- Limits are checked after ownership and before consent, so an over-limit call never asks the user to confirm.
- A limit is per call. There are no totals over time; for wallets on Coinbase CDP, add value caps in the CDP Policy Engine as well.

**Consent**
- Require consent for every tool that changes, sends or pays, unless the effect is trivial. `doctor` reports `state_write` and `external` tools without consent.
- A confirmation covers one exact call: the same tool, the same arguments, the same user and the same rule set, used once, within 10 minutes. The agent must repeat the call unchanged. `"0.0001"` and `0.0001` are different arguments.
- Pass `on_consent_required` to show the user exactly what they confirm, and call `confirm()` when they agree. The model gets "This action needs the user's confirmation.", so it can ask for it.

**Recordings and replay**
- By default, recordings keep only the arguments the rules bind or limit, plus identifier-named arguments. That protects secrets, but replay cannot check a future rule on an argument that was never recorded. In a test environment, record every argument (`redact=lambda tool, arguments: arguments`).

**Change control**
- Keep the rule set in version control and review every change like code. PatchLoop refuses rule sets with duplicate JSON keys, so a reviewer always reads what runs.
- Increase `version` with every change. Recordings name the rule set by its hash.
- Use `"schema_version": 2` only when you need `limits` or `allowlist`. Every SDK accepts versions 1 and 2.
- Before you deploy a change, run `patchloop replay calls.jsonl --rules new.json --fail-on newly_allowed`.
- `patchloop test` reports possible rule gaps from a judge model. They are leads, not verdicts. In the AgentKit trials, the judge flagged reading another address's balance, which is public on a blockchain; that was accepted, and the rule set records why in its `description`.

## Worked example: a wallet agent

From [examples/coinbase-agentkit/rules.json](../../examples/coinbase-agentkit/rules.json):

```json
"resources": {
  "recipient": {"owner_field": "user_id"},
  "token": {"allowlist": true}
},
"tools": {
  "ERC20ActionProvider_transfer": {
    "access": "scoped", "effect": "external", "consent": true,
    "resources": [{"argument": "contract_address", "resource": "token"},
                  {"argument": "destination_address", "resource": "recipient"}],
    "limits": [{"argument": "amount", "max": "10"}]
  }
}
```

A token transfer passes only when the token is approved, the destination is a recipient that the signed-in user saved, the amount is at most 10, and the user confirmed this exact call.

## Common mistakes

| Symptom | Cause | Fix |
|---|---|---|
| Every call of a tool is `unreviewed_tool` | The tool name in the rule set does not match the framework's name | Print the names or run `patchloop doctor` |
| Every call is `missing_argument` | The binding names an argument the tool does not have, or a nested argument without a JSON Pointer | `patchloop doctor` lists bindings that name no parameter |
| Every call is `authentication_required` | The call runs outside `patchloop.identify()`, or in a thread that does not copy the context | Wrap each request in `identify()`, or pass `identity=` to the PatchLoop instance |
| Calls are `facts_unavailable` | The facts function raised, or returned something other than a dictionary or `None` | Fix the lookup; check the logs of the `patchloop` logger |
| Own records are `not_owner` | The owner field holds a different type or format than the user's subject (`7` against `"7"`, or mixed case) | Normalize in the facts function or in your identity |
| The agent says a payment needs confirmation, but `/yes` does not unlock it | The repeated call used different arguments | Compare both calls in the recordings |
| A tester run reports a possible rule gap you consider fine | The judge saw access that your policy allows | Record the decision in the tool's `description`, and keep the rule |
