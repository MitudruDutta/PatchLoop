"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { closer } from "@/content/closer";
import { usePinnedProgress } from "@/hooks/usePinnedProgress";
import styles from "./Closer.module.css";

/** The closing headline. It fades and rises in as the band scrolls into view. */
export function CloserBand() {
  const bandRef = useRef<HTMLDivElement>(null);
  usePinnedProgress(bandRef, { mode: "enter" });

  return (
    <div ref={bandRef} className={styles.band}>
      <div className={styles.say}>
        <h2 className={styles.headline}>{closer.headline}</h2>
        <div className={styles.actions}>
          <Button href={closer.primary.href} data-track="cta_click" data-track-location="closer">
            {closer.primary.label}
          </Button>
          <Button variant="ghost" href={closer.secondary.href} data-track="outbound" data-track-location="closer">
            {closer.secondary.label}
          </Button>
        </div>
      </div>
    </div>
  );
}
