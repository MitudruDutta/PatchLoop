export type ThenKind = "deny" | "record" | "ask";

export type Rule = {
  id: string;
  tab: string;
  /** Rendered as code when it names a tool. */
  when: { code?: string; text: string };
  check: string;
  then: { kind: ThenKind; text: string }[];
};

export const rules = {
  heading: "Write the rule once. PatchLoop holds every tool call to it.",
  lede: "A rule names what to watch, what to check against trusted session state, and what happens when the check fails. The model's own arguments are never the evidence.",
  tablistLabel: "Violation types",
  previous: "Previous rule",
  next: "Next rule",
  labels: { when: "When", check: "Check", deny: "Deny", record: "Record", ask: "Ask" },
  items: [
    {
      id: "cross-user",
      tab: "Another customer's order",
      when: { code: "cancel_pending_order", text: "names an order" },
      check: "The order's owner is the signed-in customer",
      then: [
        { kind: "deny", text: "Refuse before the tool runs" },
        { kind: "record", text: "Log it as attempted, not executed" },
      ],
    },
    {
      id: "private-read",
      tab: "Private profile read",
      when: { code: "get_user_details", text: "asks for a profile" },
      check: "The profile belongs to the signed-in customer",
      then: [
        { kind: "deny", text: "Return nothing private" },
        { kind: "record", text: "Log the disclosure attempt" },
      ],
    },
    {
      id: "unconfirmed",
      tab: "Unconfirmed change",
      when: { text: "A tool would change a record" },
      check: "An exact “yes” for this action and these arguments, given in the last 10 minutes",
      then: [
        { kind: "deny", text: "Hold the change" },
        { kind: "ask", text: "Have the customer confirm" },
      ],
    },
    {
      id: "before-sign-in",
      tab: "Before sign-in",
      when: { text: "Any protected tool is called" },
      check: "A lookup has already bound the session identity",
      then: [
        { kind: "deny", text: "Refuse the call" },
        { kind: "record", text: "Log action before authentication" },
      ],
    },
  ] satisfies Rule[],
} as const;
