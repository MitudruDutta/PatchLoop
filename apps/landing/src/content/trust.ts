import { evidence } from "./evidence.generated";
import { formatNumber } from "./ledger";

const { guard, incident, adapter } = evidence;

export const trust = {
  heading: "Built so you can check the work.",
  lede: "A repair tool you cannot audit is one more thing to trust. PatchLoop keeps identity, evaluation and promotion outside the model's reach, and writes down what it did.",
  identity: {
    title: "Identity comes from the session",
    text: "Bound at the first successful lookup and then locked. Never read from the model's arguments.",
    rows: [
      { source: "First lookup", value: "demo_user_a", verdict: "Bound", tone: "allow" },
      { source: "Later lookup", value: "demo_user_b", verdict: "Ignored", tone: "muted" },
      { source: "Tool argument", value: "user_id", verdict: "Not evidence", tone: "muted" },
    ],
    chip: "Session locked",
    alt: "Mock: the first successful lookup binds the session. A later lookup and a user ID in a tool argument are both ignored.",
  },
  sandbox: {
    title: "Generated code runs in a box",
    text: "Candidates run in bubblewrap or Docker with no network, no secrets and no project files.",
    core: "allow()",
    chips: ["Network · none", "Root · read-only"],
    alt: "Mock: the guard function sits inside nested boundaries, with no network and a read-only root.",
  },
  trace: {
    title: "Every call leaves a trace",
    text: "Arguments, results, record changes, state hashes and the guard hash, in order.",
    header: "Trace",
    rows: [
      { tool: "find_user_id_by_email", verdict: "Allowed", tone: "allow", start: 0, width: 26 },
      { tool: "get_order_details", verdict: "Allowed", tone: "allow", start: 22, width: 30 },
      { tool: "cancel_pending_order", verdict: "Denied", tone: "deny", start: 48, width: 14 },
      { tool: "cancel_pending_order", verdict: "Allowed", tone: "allow", start: 60, width: 34 },
    ],
    chip: `guard ${guard.shortHash} · ${formatNumber(incident.guardedExecuted.value)} executed violations`,
    alt: "Mock trace of four tool calls in order. One cancel call is denied and the next, legitimate one is allowed.",
  },
  promotion: {
    title: "No guard is promoted unproven",
    text: "A candidate replaces the active version only after it passes every gate. If it fails, the previous version stays.",
    chips: [
      { name: "baseline", state: "Unrepaired", tone: "muted" },
      { name: guard.shortHash, state: "Promoted, fixed-rule guard", tone: "allow" },
      { name: "adapter candidate", state: "Rejected, over-blocked a public tool", tone: "deny" },
      { name: "adapter candidate", state: "Rejected, misread a nested record", tone: "deny" },
    ],
    caption: `${formatNumber(adapter.generated.value)} adapter candidates generated, ${formatNumber(adapter.activated.value)} promoted`,
    alt: "Outcomes so far: the baseline is unrepaired, one fixed-rule guard was promoted, and the adapter candidates were rejected.",
  },
  runner: {
    title: "Runs where your agent runs",
    text: "The runner is open source and stays on your laptop, in CI or in your private cloud. Your tools and data do not have to leave.",
    places: ["Laptop", "CI", "Private cloud"],
    core: "runner",
    alt: "Mock: the runner inside three boundaries labelled laptop, CI and private cloud.",
  },
} as const;

export type Tone = "allow" | "deny" | "muted";
