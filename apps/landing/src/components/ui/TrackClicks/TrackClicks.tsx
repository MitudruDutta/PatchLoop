"use client";

import { useEffect } from "react";
import { track, type AnalyticsEvent } from "@/lib/analytics";

/**
 * One click listener for the whole page. Any element with `data-track` sends
 * that event, with `data-track-location` and its link target as properties.
 * Server components can be tracked without becoming client components.
 */
export function TrackClicks() {
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLElement>("[data-track]") : null;
      if (!target) return;
      const props: Record<string, string> = {};
      if (target.dataset.trackLocation) props.location = target.dataset.trackLocation;
      const href = target.getAttribute("href");
      if (href) props.target = href;
      track(target.dataset.track as AnalyticsEvent, props);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return null;
}
