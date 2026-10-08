// Site-wide names, URLs and navigation.
//
// The docs site, the public domain and the contact address are not live yet
// (docs/prd/landing.md, section 17). Each comes from an environment variable.
// Until one is set, docs links fall back to the matching place in the
// repository so that no link on the page is broken.

function env(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.replace(/\/+$/, "") : null;
}

export const siteName = "PatchLoop";
export const repoUrl = "https://github.com/MitudruDutta/PatchLoop";

export const siteUrl = env(process.env.NEXT_PUBLIC_SITE_URL) ?? "http://localhost:3000";
export const contactEmail = env(process.env.NEXT_PUBLIC_CONTACT_EMAIL);
export const leadEndpoint = env(process.env.NEXT_PUBLIC_LEAD_ENDPOINT);
const docsUrl = env(process.env.NEXT_PUBLIC_DOCS_URL);

const blob = (file: string) => `${repoUrl}/blob/main/${file}`;

const docs = {
  welcome: { path: "/welcome", fallback: `${repoUrl}#readme` },
  quickstart: { path: "/quickstart", fallback: `${repoUrl}#run-locally` },
  proof: { path: "/proof", fallback: blob("docs/prd/engine.md#10-what-proof-means") },
  validation: { path: "/validation", fallback: blob("docs/status/implementation.md#acceptance-gate-correction") },
  evidence: { path: "/evidence", fallback: `${repoUrl}/tree/main/docs/evidence` },
  utilityReplay: {
    path: "/utility-replay",
    fallback: blob("docs/status/implementation.md#reference-identity-conflict-test-64"),
  },
  changelog: { path: "/changelog", fallback: `${repoUrl}/commits/main` },
  research: { path: "/limitations", fallback: blob("docs/research/weaknesses.md") },
  security: { path: "/security", fallback: `${repoUrl}#trust-and-scope` },
  cli: { path: "/cli", fallback: blob("src/patchloop/cli.py") },
} as const;

export type DocKey = keyof typeof docs;

/** Link to a docs page, or to its source in the repository until the docs site is live. */
export function docHref(key: DocKey, subpath = ""): string {
  const entry = docs[key];
  return docsUrl ? `${docsUrl}${entry.path}${subpath}` : entry.fallback;
}

export const isExternal = (href: string) => /^https?:\/\//.test(href);

export type NavLink = { label: string; href: string };

export const nav = {
  homeLabel: `${siteName}, home`,
  primaryLabel: "Primary",
  links: [
    { label: "How it works", href: "#how-it-works" },
    { label: "Evidence", href: "#evidence" },
    { label: "Pricing", href: "#pricing" },
  ] satisfies NavLink[],
  resources: {
    label: "Resources",
    items: [
      { label: "Docs", href: docHref("welcome") },
      { label: "GitHub", href: repoUrl },
      { label: "Changelog", href: docHref("changelog") },
      { label: "Research notes", href: docHref("research") },
    ] satisfies NavLink[],
  },
  github: { label: "GitHub", href: repoUrl },
  talk: "Talk to us",
  start: { label: "Get started", href: docHref("quickstart") },
  menu: { open: "Open menu", close: "Close menu", title: "Menu" },
  skip: "Skip to main content",
} as const;

export const metadataCopy = {
  title: "PatchLoop · Tested guards for tool-using agents",
  description:
    "PatchLoop tests a tool-using agent, flags rule violations by what actually changed, writes a guard for the gap, and shows the evidence that legitimate work still succeeds.",
  ogAlt: "PatchLoop. Trust the effects, not the prompt.",
} as const;

/** Shown wherever a mock uses made-up people and records. */
export const illustrativeTag = "Illustrative, synthetic data";
export const plannedTag = "Planned";
