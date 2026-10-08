// Cookieless event tracking (docs/prd/landing.md, section 14).
//
// No provider is chosen yet. `track` forwards to a provider's global function
// when one is loaded and does nothing otherwise, so call sites stay stable.

export type AnalyticsEvent =
  | "cta_click"
  | "copy_command"
  | "step_select"
  | "ledger_toggle"
  | "rule_tab"
  | "faq_open"
  | "lead_open"
  | "lead_submit"
  | "outbound";

type Props = Record<string, string | number | boolean>;

declare global {
  interface Window {
    plausible?: (event: string, options?: { props?: Props }) => void;
  }
}

export function track(event: AnalyticsEvent, props?: Props): void {
  if (typeof window === "undefined") return;
  window.plausible?.(event, props ? { props } : undefined);
}
