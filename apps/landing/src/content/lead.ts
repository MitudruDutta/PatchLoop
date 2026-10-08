import { repoUrl } from "./site";

export const lead = {
  title: "Talk to us",
  intro:
    "We are working with a small group of design partners. Tell us about your agent and we will get back to you.",
  fields: {
    name: { label: "Name", placeholder: "Your name" },
    email: { label: "Work email", placeholder: "you@company.com" },
    agent: {
      label: "What does your agent do?",
      placeholder: "The tools it calls and the data it can change",
    },
    stack: {
      label: "How are its tools defined?",
      options: ["Python tools", "OpenAI tool schemas", "MCP", "Other"],
    },
  },
  submit: "Send",
  sending: "Sending…",
  close: "Close",
  errors: {
    name: "Enter your name.",
    email: "Enter a valid work email.",
    agent: "Tell us a little about your agent.",
    send: "That did not send. Please try again, or email us directly.",
  },
  success: {
    title: "Thank you.",
    sent: "We have your note and will reply by email.",
    mailto: "Your email app should now have a draft addressed to us. Send it and we will reply.",
  },
  // Shown when neither a form endpoint nor a contact address is configured.
  unconfigured: {
    text: "Our contact address is being set up. Until then, open an issue on GitHub and we will reply there.",
    action: { label: "Open an issue", href: `${repoUrl}/issues` },
  },
  mailSubject: "PatchLoop design partner",
} as const;
