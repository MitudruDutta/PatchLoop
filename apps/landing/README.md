# PatchLoop landing page

The public marketing page. Requirements and design: [docs/prd/landing.md](../../docs/prd/landing.md).

Next.js 16.4 (App Router), React 19, Tailwind 4 for the global stylesheet, CSS Modules for components. The page is fully static.

Before changing code, read [AGENTS.md](AGENTS.md): this Next.js version differs from older releases.

## Run it

From the repository root (Bun 1.4 or later):

```bash
bun install
bun run landing:dev      # http://localhost:3000
```

Or from this directory: `bun run dev`.

| Command | What it does |
|---|---|
| `bun run dev` | Syncs the evidence, then starts the dev server |
| `bun run build` | Syncs the evidence, then builds for production |
| `bun run lint` | ESLint |
| `bun run typecheck` | Generates route types, then runs `tsc` |
| `bun run check:evidence` | Fails if `src/content/evidence.generated.ts` is out of date |
| `bun run test` | Playwright: smoke, evidence and accessibility checks against a production build |

The tests use Playwright's Chromium (`bunx playwright install chromium`). To use an installed browser instead, set `PLAYWRIGHT_CHANNEL=chrome` or `msedge`.

## Configuration

Copy `.env.example` to `.env.local`. Every value is optional.

| Variable | Effect when unset |
|---|---|
| `NEXT_PUBLIC_SITE_URL` | Canonical URLs and social cards use `http://localhost:3000` |
| `NEXT_PUBLIC_DOCS_URL` | Docs links point at the matching file in the GitHub repository |
| `NEXT_PUBLIC_CONTACT_EMAIL` | The footer contact box and "Talk to us" point at GitHub issues |
| `NEXT_PUBLIC_LEAD_ENDPOINT` | "Talk to us" opens a `mailto:` draft instead of posting the form |

## Where things live

```
scripts/sync-evidence.mjs   docs/evidence/*.json → src/content/evidence.generated.ts
src/app/                    layout, the one page, metadata routes
src/components/sections/    one folder per page section, in page order in app/page.tsx
src/components/mocks/       product mocks drawn in HTML and SVG
src/components/art/         illustrations: LoopField, CallField, LoopMark
src/components/ui/          shared pieces: Button, TabPlateau, LeadDialog, Reveal …
src/components/layout/      nav and the page rail
src/content/                all copy and data, typed. Components hold no copy
src/hooks/                  scroll progress, auto-advance, reduced motion
tests/                      Playwright specs
```

Design tokens and the logo come from [`packages/brand`](../../packages/brand).

## Rules worth knowing

- **Numbers come from evidence.** Every figure on the page is read from `docs/evidence/*.json` by `scripts/sync-evidence.mjs`. A missing field, a gate that no longer passes, or a guard file whose hash differs from the validated one fails the build. Do not type a number into a component.
- **Copy lives in `src/content/`.** A change that touches a claim should point to the evidence or status line that supports it. The claim rules are in the PRD, section 5.
- **`src/content/status.ts` mirrors the README status line.** Update both in one change.
- **Motion is optional.** With reduced motion, or without JavaScript, the page is stacked and complete. Component CSS decides this with `prefers-reduced-motion` and `scripting` media queries, so there is no layout jump on load.
- **Mock identities are made up** (`demo_user_a`, `demo_order_b1`) and deliberately unlike the benchmark fixture's IDs.
