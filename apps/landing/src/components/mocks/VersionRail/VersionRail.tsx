import type { CSSProperties } from "react";
import { StatusBadge, type StatusKind } from "@/components/ui/StatusBadge";
import { trust, type Tone } from "@/content/trust";
import { cn } from "@/lib/cn";
import styles from "./VersionRail.module.css";

const kinds: Record<Tone, StatusKind> = { allow: "allowed", deny: "denied", muted: "neutral" };

/** Outcomes of each guard version and candidate, side by side. No lineage is implied. */
export function VersionRail({ className }: { className?: string }) {
  const { chips, caption } = trust.promotion;
  return (
    <div className={cn(styles.rail, className)}>
      <div className={styles.chips}>
        {chips.map((chip, index) => (
          <div
            key={index}
            className={cn("reveal-chip", styles.chip, chip.tone === "allow" && styles.active)}
            style={{ transitionDelay: `${index * 90}ms` } as CSSProperties}
          >
            <code className={styles.name}>{chip.name}</code>
            <StatusBadge kind={kinds[chip.tone]}>{chip.state}</StatusBadge>
          </div>
        ))}
      </div>
      <p className={cn("t-mono", styles.caption)}>{caption}</p>
    </div>
  );
}
