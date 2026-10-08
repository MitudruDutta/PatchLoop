# PatchLoop specification

The language-neutral contract that every PatchLoop SDK implements. The Python SDK (`src/patchloop/sdk/`) and the TypeScript SDK must give the same decision for the same rule set, call and facts.

| File | Content |
|---|---|
| [rule-semantics.md](rule-semantics.md) | How one tool call is decided: inputs, evaluation order, reason codes, rule set validity, rule set hash |
| [schemas/ruleset.schema.json](schemas/ruleset.schema.json) | JSON Schema of a rule set (structure only; cross-field rules are in rule-semantics.md section 4) |
| [schemas/recording.schema.json](schemas/recording.schema.json) | JSON Schema of one line in a recordings file |
| [conformance/decisions.json](conformance/decisions.json) | Decision cases, invalid rule sets, invalid rule set texts and expected rule set hashes |

## Conformance

An SDK conforms when, for every entry in `conformance/decisions.json`:

- each case gives exactly the expected `decision` and `reason`, and exactly the expected `lookups` when the case lists them;
- each invalid rule set is refused at load time, and so is each text in `invalid_ruleset_texts` (duplicate keys cannot survive JSON parsing, so they are given as raw text);
- each rule set hashes to the listed `ruleset_sha256` value.

A case's facts come from `facts[<rule set>]`: a lookup returns the record from `records`, returns "missing" when there is no record, and fails (unavailable) for each pair in `unavailable`.

## Changing the specification

1. Change `rule-semantics.md` and, when needed, the schemas.
2. Add or change the conformance cases that show the change.
3. Change each SDK until its conformance tests pass.

Never change a vector to match an SDK. A change to evaluation order or reason codes is a new `schema_version`.
