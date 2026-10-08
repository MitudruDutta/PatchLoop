# PatchLoop rule semantics, version 1

This document defines how an SDK decides whether one tool call may run. Every SDK (Python, TypeScript) must give exactly the decisions in `conformance/decisions.json`. Change this document first, then the vectors, then each SDK.

## 1. Inputs

| Input | Form |
|---|---|
| Rule set | A JSON object that follows `schemas/ruleset.schema.json` and section 4 |
| Tool | The tool name |
| Arguments | A JSON object |
| Principal | `null` (nobody is logged in), or `{"subject": <identifier>, "tenant": <identifier or null>}` from the host application's authentication |
| Facts | A lookup `(resource, id) -> record`, supplied by the host application. A record is a JSON object. "Missing" means the lookup confirmed that no record exists. "Unavailable" means the lookup could not answer, or returned something other than a JSON object. |
| Consent | `true` only when the host application holds trusted user consent for this exact call |

An **identifier** is a string or an integer. Booleans are not integers. An integer identifier must be between −(2^53 − 1) and 2^53 − 1, so that every SDK can represent it exactly.

The model never supplies the principal, the facts or the consent.

## 2. Output

A decision has three fields:

- `decision`: `allow`, `deny`, or `indeterminate`.
- `reason`: one code from section 5.
- `lookups`: the facts used, in the order they were read. Each entry is `{"resource", "id", "status"}`. Status is `found`, `missing` or `unavailable`. A `found` entry also has `owner`, `tenant` and `parent` for each of `owner_field`, `tenant_field` and `parent.field` that the resource defines. The value is the record's value, or `null` when the record does not have the field.

In enforce mode, an SDK runs the tool only when the decision is `allow`. `deny` and `indeterminate` both block.

**What the model sees.** When a call is blocked, an SDK gives the model exactly this text, whatever the reason: `This action is not permitted.` The reason and lookups go only to the host application and the recordings. A different text per reason would let the model learn which records exist (`not_owner` versus `resource_missing`).

## 3. Evaluation order

The first step that returns ends the evaluation.

1. If the tool is not in the rule set, return **indeterminate** `unreviewed_tool`.
2. If the tool's `access` is `public`, return **allow** `public`.
3. If the principal is `null`, return **deny** `authentication_required`.
4. If the tool's `access` is `scoped`, check each resource binding in the order listed:
   1. Read the argument named by `argument`. A name that starts with `/` is a JSON Pointer ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901)) into the arguments object, for nested arguments; a pointer that does not resolve counts as absent. Any other name is a top-level key. If the argument is absent or `null`, return **deny** `missing_argument`.
   2. If `cardinality` is `many`, the value must be an array, otherwise return **deny** `malformed_argument`. An empty array passes. If `cardinality` is `one`, treat the value as an array of one item.
   3. Every item must be an identifier, otherwise return **deny** `malformed_argument`.
   4. Check each item with section 3.1. The first failure returns.
5. If the tool has `consent: true` and consent is not `true`, return **deny** `consent_required`.
6. Return **allow** `authorized`.

### 3.1 Checking one resource identifier

Let `R` be the resource definition named by the binding, and `id` the item.

1. If `R` has `principal: true`: the item must equal the principal's subject. Otherwise return **deny** `not_principal`. No lookup happens.
2. Look up `(R's name, id)`:
   - **Unavailable** (the lookup raised an error): return **indeterminate** `facts_unavailable`.
   - **Missing:** return **deny** `resource_missing`.
3. If `R` has a `parent`, read the record's field named `parent.field`:
   - If the field is absent, `null` or not an identifier, return **indeterminate** `broken_parent`.
   - Otherwise check `(parent.resource, that value)` with this same section, starting at step 1. A parent lookup that is **missing** returns **indeterminate** `broken_parent`.
   - The parent's decision is the item's decision.
4. If `R` has a `tenant_field`:
   - If the principal's tenant is `null`, return **indeterminate** `tenant_unknown`.
   - If the record's tenant field is absent or `null`, return **indeterminate** `tenant_unknown`.
   - If it differs from the principal's tenant, return **deny** `wrong_tenant`.
5. If `R` has an `owner_field`:
   - If the record's owner field is absent or `null`, return **indeterminate** `owner_unknown`.
   - If it differs from the principal's subject, return **deny** `not_owner`.
6. The item passes.

**Equality is strict:** two values are equal only when both are strings, or both are integers, with the same value. The integer `7` and the string `"7"` are different. A value that is not an identifier is equal to nothing.

## 4. Rule set validity

An SDK must refuse to load a rule set that breaks any of these rules:

1. The JSON text has no duplicate keys in any object. (A reviewer reads the first value; most parsers keep the last.)
2. `schema_version` is `1`. `name` and `version` are non-empty strings.
3. Only the keys in the schema appear, at every level.
4. Each resource has exactly one of these forms:
   - `principal: true`;
   - a `parent` object with `resource` and `field`;
   - at least one of `owner_field` and `tenant_field`.
5. Every `parent.resource` and every binding's `resource` names a defined resource.
6. Following `parent` links from any resource never revisits a resource, and takes at most **4** links.
7. Each tool's `access` is `public`, `authenticated` or `scoped`. Its `effect` is `none`, `state_write` or `external`.
8. A `scoped` tool has at least one resource binding. Other tools have none.
9. `consent` is a boolean. It defaults to `false`. A `public` tool must not have `consent: true`, because a public tool is allowed before consent is checked.
10. A binding's `cardinality` is `one` or `many`. It defaults to `one`. A binding's `argument` that starts with `/` must be a valid JSON Pointer.

## 5. Reason codes

| Code | Decision | Meaning |
|---|---|---|
| `public` | allow | Public tool |
| `authorized` | allow | All checks passed |
| `unreviewed_tool` | indeterminate | The tool is not in the rule set |
| `authentication_required` | deny | Nobody is logged in |
| `missing_argument` | deny | A bound argument is absent or null |
| `malformed_argument` | deny | A bound argument has the wrong shape |
| `not_principal` | deny | A principal-type argument names someone else |
| `resource_missing` | deny | The resource does not exist |
| `facts_unavailable` | indeterminate | A lookup could not answer |
| `broken_parent` | indeterminate | A parent link is absent or points to nothing |
| `tenant_unknown` | indeterminate | The tenant of the principal or the record is unknown |
| `wrong_tenant` | deny | The record belongs to another tenant |
| `owner_unknown` | indeterminate | The record has no owner value |
| `not_owner` | deny | The record belongs to another subject |
| `consent_required` | deny | The tool needs consent, and consent is absent |

## 6. Limits of version 1

- Identifiers must be unique within one resource type. Tenant-local identifiers come in a later version.
- No roles, amount limits, time windows or data-flow rules.
- `effect` is recorded and reported. It does not change the decision in version 1.

## 7. Rule set hash

Recordings and evidence name a rule set by the SHA-256 of its canonical JSON form ([RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)), as loaded and before defaults are applied, in lowercase hexadecimal. `conformance/decisions.json` lists the expected hash of each rule set.
