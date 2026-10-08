import { docHref } from "./site";

// The nine commands are the entries of COMMANDS in src/patchloop/cli.py.
const commands = [
  "replay",
  "demo",
  "campaign",
  "compare",
  "reproduce",
  "repair",
  "export",
  "dashboard",
  "providers",
] as const;

export const builtOn = {
  sectionLabel: "Built on",
  lede: "Built in the open, on tools you can inspect.",
  // Text chips only. Third-party logos need each owner's brand permission.
  chips: [
    { label: "NVIDIA Nemotron", href: "https://nebius.com/blog/posts/nemotron3-super-now-available" },
    { label: "Nebius Token Factory", href: "https://docs.tokenfactory.nebius.com/" },
    { label: "Tavily Search", href: "https://docs.tavily.com/documentation/api-reference/endpoint/search" },
    { label: "τ-bench retail (Sierra, MIT)", href: "https://github.com/sierra-research/tau-bench" },
  ],
  tickerLabel: "PatchLoop commands",
  commands: commands.map((name) => ({
    name,
    text: `patchloop ${name}`,
    href: docHref("cli", `/${name}`),
  })),
} as const;
