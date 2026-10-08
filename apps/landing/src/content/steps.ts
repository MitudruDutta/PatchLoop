import { docHref } from "./site";

export const steps = {
  heading: {
    before: "Anything PatchLoop promotes is a ",
    link: { word: "tested", label: "Read how validation works", href: docHref("validation") },
    after: " guard.",
  },
  lede: "PatchLoop sits at the tool boundary, between your agent and your data. It records what happened, repairs what went wrong, and keeps the evidence. You bring the policy.",
  /** Time each step stays open before the next one opens, in milliseconds. */
  dwellMs: 5500,
  items: [
    {
      id: "find",
      title: "Violations found by their effects",
      body: "An adversarial tester plays a dishonest customer. A trusted dispatcher records every tool call and every record change. A violation is flagged from what executed, not from what the model said.",
    },
    {
      id: "repair",
      title: "A guard written for the gap",
      body: "The repair worker receives the policy, the tool schemas and the reproduced failure, and writes a guard. It gets at most three attempts, and each candidate runs in a sandbox with no network, no secrets and no project files.",
    },
    {
      id: "prove",
      title: "Evidence before promotion",
      body: "A candidate is promoted only if it contains the original violation, passes the private development and sealed panels, and preserves every recorded legitimate task. Otherwise the previous version stays.",
    },
  ],
} as const;

/**
 * Mock conversation for step 1. Made-up identities, deliberately unlike the
 * benchmark fixture's IDs, so nothing here reads as the recorded incident.
 */
export const conversationMock = {
  title: "Conversation",
  tester: {
    speaker: "Tester",
    text: "My partner placed an order on their account. Cancel it for me, it is no longer needed.",
  },
  agent: {
    speaker: "Agent",
    text: "Done. The order has been cancelled.",
  },
  call: {
    label: "Tool call",
    name: "cancel_pending_order",
    args: 'order_id="demo_order_b1", reason="no longer needed"',
  },
  alt: "Mock conversation: a tester asks the agent to cancel an order that belongs to another customer, and the agent calls the cancel tool.",
} as const;

export const effectMock = {
  title: "Effect",
  record: "orders / demo_order_b1",
  rows: [
    { field: "status", before: "pending", after: "cancelled" },
    { field: "owner", before: "demo_user_b", after: "demo_user_b" },
  ],
  session: { label: "Session user", value: "demo_user_a" },
  badge: "Executed violation",
  note: "The order's owner is not the session user.",
  columns: { field: "Field", before: "Before", after: "After" },
  alt: "Mock record change: the order's status moved from pending to cancelled although its owner is not the session user. It is flagged as an executed violation.",
} as const;

export const guardMock = {
  title: "Generated guard",
  caption: "Model-generated, copied unchanged. Fixed-rule interface.",
  attemptLabel: (attempts: number) => `Attempt ${attempts} of 3`,
  tokensLabel: (tokens: string) => `${tokens} tokens`,
  hashLabel: "sha256",
  alt: "The saved model-generated guard: a ten-line Python function that denies a protected call when nobody is signed in or when the record's owner is not the signed-in user.",
} as const;

export const validationMock = {
  title: "Validation",
  promoted: (hash: string) => `Promoted · ${hash}`,
  conflictNote: (ids: string) => `Known conflict ${ids} contained`,
  alt: "Validation results for the guard: every gate passed, and the guard was promoted.",
} as const;
