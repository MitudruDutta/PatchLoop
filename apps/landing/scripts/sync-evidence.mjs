// Reads the credential-free evidence files in docs/evidence and writes
// src/content/evidence.generated.ts. Every number on the landing page comes
// from that file, so a missing or retyped field fails the build here.
//
// Usage: node scripts/sync-evidence.mjs [--check]
//   --check  exit 1 if the generated file is out of date, without writing it

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(appDir, "../..");
const evidenceDir = path.join(repoRoot, "docs", "evidence");
const outFile = path.join(appDir, "src", "content", "evidence.generated.ts");

const FILES = {
  validation: "review-validation-2026-10-05.json",
  repair: "live-repair-2026-10-05.json",
  product: "local-product-2026-10-05.json",
};
const GUARD_FILE = "examples/guards/ownership.py";

function fail(message) {
  console.error(`sync-evidence: ${message}`);
  process.exit(1);
}

function load(name) {
  const file = path.join(evidenceDir, name);
  if (!existsSync(file)) fail(`missing evidence file docs/evidence/${name}`);
  try {
    return JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    fail(`docs/evidence/${name} is not valid JSON: ${error.message}`);
  }
}

const data = Object.fromEntries(Object.entries(FILES).map(([key, name]) => [key, load(name)]));

/** Read a dotted path and check its type. Array indexes are plain numbers. */
function read(source, fieldPath, type) {
  let value = data[source];
  for (const part of fieldPath.split(".")) {
    if (value === null || typeof value !== "object" || !(part in value)) {
      fail(`${FILES[source]}: field "${fieldPath}" is missing`);
    }
    value = value[part];
  }
  const actual = Array.isArray(value) ? "array" : typeof value;
  if (actual !== type) {
    fail(`${FILES[source]}: field "${fieldPath}" is ${actual}, expected ${type}`);
  }
  return value;
}

/** A displayed value with the file and field it came from. */
function sourced(value, source, fieldPath) {
  return { value, file: FILES[source], path: fieldPath };
}

function count(source, fieldPath) {
  return sourced(read(source, fieldPath, "number"), source, fieldPath);
}

function requireTrue(source, fieldPath) {
  if (read(source, fieldPath, "boolean") !== true) {
    fail(`${FILES[source]}: "${fieldPath}" is not true. The page states this gate passed; update the copy before shipping.`);
  }
}

function requireEmpty(source, fieldPath) {
  const list = read(source, fieldPath, "array");
  if (list.length !== 0) {
    fail(`${FILES[source]}: "${fieldPath}" is not empty. The page states there were no failures; update the copy before shipping.`);
  }
}

// --- Gates the page describes as passed -----------------------------------

requireTrue("validation", "accepted");
requireTrue("validation", "security_development.passed");
requireTrue("validation", "sealed_security.passed");
requireTrue("validation", "coverage_complete");
requireTrue("validation", "baseline_fidelity");
requireTrue("validation", "incident.legitimate_call_completed");
requireEmpty("validation", "boundary_failures");
requireEmpty("validation", "utility_failures");

// --- Values ----------------------------------------------------------------

const boundaryCases = count("validation", "boundary_cases");
const developmentCases = count("validation", "security_development.cases");
const sealedCases = count("validation", "sealed_security.cases");

const effectChecks = {
  value:
    read("validation", "security_development.effect_checks", "number") +
    read("validation", "sealed_security.effect_checks", "number"),
  file: FILES.validation,
  path: "security_development.effect_checks + sealed_security.effect_checks",
};
const singletonChecks = {
  value:
    read("validation", "security_development.singleton_checks", "number") +
    read("validation", "sealed_security.singleton_checks", "number"),
  file: FILES.validation,
  path: "security_development.singleton_checks + sealed_security.singleton_checks",
};

const scheduledTasks = count("validation", "scheduled_tasks");
const scheduledCalls = count("validation", "scheduled_calls");
const utilityTasks = count("validation", "utility_tasks");
const utilityPassed = count("validation", "utility_passed");

const conflicts = read("validation", "identity_conflict_outcomes", "array");
const conflictIds = conflicts.map((entry, index) => {
  if (typeof entry?.task_id !== "string") {
    fail(`${FILES.validation}: identity_conflict_outcomes.${index}.task_id is missing`);
  }
  return entry.task_id;
});
if (utilityPassed.value + conflictIds.length !== scheduledTasks.value) {
  fail(
    `${FILES.validation}: utility_passed (${utilityPassed.value}) plus identity conflicts (${conflictIds.length}) ` +
      `does not equal scheduled_tasks (${scheduledTasks.value}). The "still passing" readout assumes it does.`,
  );
}

const protectedTools = read("validation", "security_development.protected_tools", "array").map((name) => {
  if (typeof name !== "string") fail(`${FILES.validation}: protected_tools contains a non-string`);
  return { name, kind: name.startsWith("get_") ? "read" : "write" };
});

const sourceHash = read("validation", "source_hash", "string");
const activatedHash = read("repair", "activated_hash", "string");
if (sourceHash !== activatedHash) {
  fail(`validated source_hash (${sourceHash}) differs from the activated_hash in ${FILES.repair} (${activatedHash})`);
}

// The guard shown on the page is the saved file, and it must be the validated one.
const guardPath = path.join(repoRoot, GUARD_FILE);
if (!existsSync(guardPath)) fail(`missing ${GUARD_FILE}`);
const guardSource = readFileSync(guardPath, "utf8").replace(/\r\n/g, "\n");
const guardHash = createHash("sha256").update(guardSource, "utf8").digest("hex");
if (guardHash !== sourceHash) {
  fail(`${GUARD_FILE} hashes to ${guardHash}, but the evidence validated ${sourceHash}`);
}

const adapterAttempts = read("product", "live_adapter_generation.attempts", "array");

const evidence = {
  files: FILES,
  incident: {
    baselineExecuted: count("repair", "before_executed_violations"),
    guardedExecuted: count("validation", "incident.executed_violations"),
    guardedBlocked: count("validation", "incident.unsafe_attempts_blocked"),
  },
  archive: {
    scheduledTasks,
    scheduledCalls,
    utilityTasks,
    utilityPassed,
    conflictCount: sourced(conflictIds.length, "validation", "identity_conflict_outcomes"),
    conflictIds,
  },
  gates: {
    boundary: boundaryCases,
    development: developmentCases,
    sealed: sealedCases,
    effect: effectChecks,
    singleton: singletonChecks,
  },
  protectedTools: sourced(protectedTools, "validation", "security_development.protected_tools"),
  guard: {
    file: GUARD_FILE,
    source: guardSource.replace(/\n+$/, ""),
    hash: sourced(sourceHash, "validation", "source_hash"),
    shortHash: sourceHash.slice(0, 8),
  },
  repair: {
    model: sourced(read("repair", "model", "string"), "repair", "model"),
    totalTokens: count("repair", "attempts.0.usage.total_tokens"),
    attempts: sourced(read("repair", "attempts", "array").length, "repair", "attempts"),
  },
  adapter: {
    generated: sourced(adapterAttempts.length, "product", "live_adapter_generation.attempts"),
    accepted: count("product", "live_adapter_generation.accepted"),
    activated: count("product", "live_adapter_generation.activated"),
  },
};

const banner = `// GENERATED by scripts/sync-evidence.mjs from docs/evidence/*.json.
// Do not edit by hand. Run \`bun run sync:evidence\` after the evidence changes.
`;
const body = `${banner}
export const evidence = ${JSON.stringify(evidence, null, 2)} as const;

export type Evidence = typeof evidence;
`;

const current = existsSync(outFile) ? readFileSync(outFile, "utf8").replace(/\r\n/g, "\n") : null;
if (process.argv.includes("--check")) {
  if (current !== body) fail("src/content/evidence.generated.ts is out of date. Run `bun run sync:evidence`.");
  console.log("sync-evidence: up to date");
} else if (current !== body) {
  writeFileSync(outFile, body, "utf8");
  console.log("sync-evidence: wrote src/content/evidence.generated.ts");
} else {
  console.log("sync-evidence: up to date");
}
