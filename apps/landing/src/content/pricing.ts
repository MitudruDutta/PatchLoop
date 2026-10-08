import { docHref, repoUrl } from "./site";

export type Plan = {
  id: string;
  name: string;
  blurb: string;
  price: string;
  priceNote: string;
  action: { label: string; kind: "link"; href: string } | { label: string; kind: "lead" };
  lead?: string;
  /** `planned` features are specified in the platform PRD and not built yet. */
  features: { text: string; planned?: boolean }[];
  footnote?: { text: string; link: { label: string; href: string } };
  solid: boolean;
};

// No dollar amounts: the platform PRD's prices are hypotheses until the
// design-partner interviews are done (docs/prd/landing.md, section 8.8).
export const pricing: { heading: string; lede: string; plans: Plan[] } = {
  heading: "Open source today. Hosted when your team needs it.",
  lede: "The runner, CLI and local dashboard are free and MIT licensed. Hosted run history, guard pull requests and team controls are being built with design partners.",
  plans: [
    {
      id: "open-source",
      name: "Open source",
      blurb: "For developers and researchers testing their own agents.",
      price: "Free",
      priceNote: "MIT licensed. Bring your own model key.",
      action: { label: "Get started", kind: "link", href: docHref("quickstart") },
      features: [
        { text: "Runner, CLI and SDK" },
        { text: "Local dashboard and reproduction bundles" },
        { text: "Sandbox for generated guards" },
        { text: "Reviewable patch export with evidence" },
        { text: "Community support" },
      ],
      footnote: {
        text: "Found a bug or a gap?",
        link: { label: "Open an issue.", href: `${repoUrl}/issues` },
      },
      solid: false,
    },
    {
      id: "team",
      name: "Team and Enterprise",
      blurb: "For teams that review guards together and keep the evidence.",
      price: "Design partners",
      priceNote: "Hosted plans are in development. We are starting with a small group.",
      action: { label: "Talk to us", kind: "lead" },
      lead: "Everything in Open source, plus",
      features: [
        { text: "Hosted run and evidence history", planned: true },
        { text: "Guard pull requests and a GitHub Action", planned: true },
        { text: "Organizations, roles and API keys", planned: true },
        { text: "Single sign-on and audit-log export", planned: true },
        { text: "Self-hosted control plane", planned: true },
      ],
      solid: true,
    },
  ],
};
