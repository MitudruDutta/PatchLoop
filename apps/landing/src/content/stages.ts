import { docHref } from "./site";

export const stages = {
  heading: {
    before: "Every agent's rules live somewhere between the prompt and ",
    link: { word: "proof", label: "Read what proof means", href: docHref("proof") },
    after: ".",
  },
  panes: [
    {
      label: "Rules in the prompt",
      body: "The policy says to help one customer at a time and to confirm before changing anything. The tools accept any order ID. One persuasive message, and the agent cancels someone else's order.",
      artAlt:
        "Diagram: calls from the agent reach every record, including two that belong to other customers. Those two records are changed.",
    },
    {
      label: "Rules at the tool boundary",
      body: "A guard checks every call before it runs. Identity comes from the session, never from the model's arguments. The unsafe call is refused before any record changes.",
      artAlt:
        "Diagram: a boundary stands between the agent and the records. Calls to the session user's records pass. Calls to other customers' records stop at the boundary.",
    },
    {
      label: "Rules with evidence",
      body: "Each promoted guard carries its own record: the violation it contains, the private cases it passed, and every legitimate task that still completes.",
      artAlt:
        "Diagram: the same boundary, with a ledger underneath that counts each call as preserved or blocked.",
    },
  ],
  cta: { label: "Get started", href: docHref("quickstart") },
  /** Labels drawn inside the CallField illustration. */
  art: {
    agent: "Agent",
    session: "Session user",
    others: "Other customers",
    boundary: "Guard",
    changed: "changed",
    untouched: "untouched",
    preserved: "preserved",
    blocked: "blocked",
    ledger: "Ledger",
  },
} as const;
