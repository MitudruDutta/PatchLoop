import { docHref } from "./site";

export const hero = {
  sectionLabel: "PatchLoop",
  eyebrow: "Authorization remediation for AI agents",
  headline: ["Trust the effects,", "not the prompt."],
  lede: "PatchLoop tests a tool-using agent, flags rule violations by what actually changed, writes a guard for the gap, and shows the evidence that legitimate work still succeeds.",
  primary: { label: "Get started", href: docHref("quickstart") },
  secondary: { label: "See the evidence", href: "#evidence" },
  /** The five stations on the LoopField orbit, in order of travel. */
  stations: ["Test", "Detect", "Repair", "Validate", "Promote"],
} as const;
