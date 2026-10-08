import { evidence } from "./evidence.generated";
import { docHref } from "./site";

const { incident, archive, gates } = evidence;

type Sourced<T> = { readonly value: T; readonly file: string; readonly path: string };

const formatter = new Intl.NumberFormat("en-US");
export const formatNumber = (value: number) => formatter.format(value);

const provenance = (...items: Sourced<unknown>[]) =>
  items.map((item) => `${item.file} · ${item.path}`).join("\n");

export type LedgerMode = "baseline" | "guarded";

export const ledger = {
  heading: "See what was attempted, what executed, and what still works.",
  lede: "An unsafe call the model proposes and an unsafe call that changes a record are different outcomes. PatchLoop reports both, next to the legitimate work that has to keep passing.",
  toggle: {
    label: "Guard version",
    options: [
      { id: "baseline", label: "Baseline" },
      { id: "guarded", label: "Guarded" },
    ] satisfies { id: LedgerMode; label: string }[],
    initial: "guarded" as LedgerMode,
  },
  readouts: [
    {
      label: "Unsafe calls executed",
      baseline: formatNumber(incident.baselineExecuted.value),
      guarded: formatNumber(incident.guardedExecuted.value),
      source: provenance(incident.baselineExecuted, incident.guardedExecuted),
    },
    {
      label: "Unsafe attempts blocked",
      // The baseline has no guard, so nothing is blocked.
      baseline: formatNumber(0),
      guarded: formatNumber(incident.guardedBlocked.value),
      source: provenance(incident.guardedBlocked),
    },
    {
      label: "Reference tasks still passing",
      baseline: `${formatNumber(archive.scheduledTasks.value)} of ${formatNumber(archive.scheduledTasks.value)}`,
      guarded: `${formatNumber(archive.utilityPassed.value)} of ${formatNumber(archive.scheduledTasks.value)}`,
      source: provenance(archive.utilityPassed, archive.scheduledTasks),
    },
  ],
  conflictChip: {
    text:
      archive.conflictCount.value === 1
        ? "1 known identity conflict, contained"
        : `${formatNumber(archive.conflictCount.value)} known identity conflicts, contained`,
    href: docHref("utilityReplay"),
    title: `Read about ${archive.conflictIds.join(", ")}`,
  },
  tools: {
    title: "Protected tools",
    columns: { tool: "Protected tool", kind: "Kind" },
    kinds: { write: "Changes data", read: "Reads private data" },
    rows: evidence.protectedTools.value,
    source: provenance(evidence.protectedTools),
  },
  gates: {
    title: "Validation gates",
    passedLabel: "passed",
    rows: [
      {
        label: "Boundary checks",
        count: `${formatNumber(gates.boundary.value)} / ${formatNumber(gates.boundary.value)}`,
        source: provenance(gates.boundary),
      },
      {
        label: "Development panel",
        count: `${formatNumber(gates.development.value)} / ${formatNumber(gates.development.value)}`,
        source: provenance(gates.development),
      },
      {
        label: "Sealed panel",
        count: `${formatNumber(gates.sealed.value)} / ${formatNumber(gates.sealed.value)}`,
        source: provenance(gates.sealed),
      },
      {
        label: "Actual-effect checks",
        count: `${formatNumber(gates.effect.value)} / ${formatNumber(gates.effect.value)}`,
        source: provenance(gates.effect),
      },
      {
        label: "Singleton checks",
        count: `${formatNumber(gates.singleton.value)} / ${formatNumber(gates.singleton.value)}`,
        source: provenance(gates.singleton),
      },
      {
        label: "Archive replay",
        count: `${formatNumber(archive.scheduledTasks.value)} tasks · ${formatNumber(archive.scheduledCalls.value)} calls`,
        source: provenance(archive.scheduledTasks, archive.scheduledCalls),
      },
      {
        label: "Policy-consistent tasks preserved",
        count: `${formatNumber(archive.utilityPassed.value)} / ${formatNumber(archive.utilityTasks.value)}`,
        source: provenance(archive.utilityPassed, archive.utilityTasks),
      },
    ],
  },
  sourceLabel: "Source",
  note: "Every number on this page is read at build time from the credential-free evidence files in the repository.",
  noteLink: { label: "Open the evidence", href: docHref("evidence") },
  scope: "One synthetic retail benchmark. Finite checks. Not a claim of general security.",
} as const;
