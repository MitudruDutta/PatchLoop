import { contactEmail, docHref, repoUrl, type NavLink } from "./site";

type Column = { title: string; links: NavLink[] };

// A link is listed only when its target exists. Terms, Privacy and a
// community channel are still open items (docs/prd/landing.md, section 17).
const columns: Column[] = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "#how-it-works" },
      { label: "Evidence", href: "#evidence" },
      { label: "Pricing", href: "#pricing" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Docs", href: docHref("welcome") },
      { label: "Changelog", href: docHref("changelog") },
      { label: "Research notes", href: docHref("research") },
      { label: "Security", href: docHref("security") },
    ],
  },
  {
    title: "Community",
    links: [{ label: "GitHub", href: repoUrl }],
  },
  {
    title: "Legal",
    links: [{ label: "MIT License", href: `${repoUrl}/blob/main/LICENSE` }],
  },
];

export const closer = {
  headline: "Test. Repair. Test again.",
  primary: { label: "Get started", href: docHref("quickstart") },
  secondary: { label: "Star on GitHub", href: repoUrl },
  blurb: "Open-source authorization remediation for tool-using agents.",
  contact: {
    title: "Reach out.",
    blurb: "Tell us about the agent you are protecting.",
    email: contactEmail,
    copy: "Copy",
    copied: "Copied",
    copyLabel: (email: string) => `Copy ${email}`,
    // Shown until a contact address is configured.
    fallback: { label: "Open an issue on GitHub", href: `${repoUrl}/issues` },
  },
  footerLabel: "Footer",
  columns,
  foot: "© 2026 PatchLoop. MIT licensed.",
} as const;
