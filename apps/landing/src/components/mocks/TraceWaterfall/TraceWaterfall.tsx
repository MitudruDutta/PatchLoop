import type { CSSProperties } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { trust } from "@/content/trust";
import { cn } from "@/lib/cn";
import styles from "./TraceWaterfall.module.css";

/** Tool calls in order, each with a bar on a shared timeline and its verdict. */
export function TraceWaterfall({ className }: { className?: string }) {
  const { header, rows } = trust.trace;
  return (
    <div className={cn(styles.trace, className)}>
      <span className={cn("t-label", styles.header)}>{header}</span>
      {rows.map((row, index) => (
        <div key={index} className={styles.row}>
          <div className={styles.meta}>
            <code className={styles.tool}>{row.tool}</code>
            <StatusBadge kind={row.tone === "deny" ? "denied" : "allowed"}>{row.verdict}</StatusBadge>
          </div>
          <div className={styles.track}>
            <span
              className={cn("reveal-bar", styles.bar, row.tone === "deny" && styles.deny)}
              style={
                {
                  left: `${row.start}%`,
                  width: `${row.width}%`,
                  transitionDelay: `${index * 110}ms`,
                } as CSSProperties
              }
            />
          </div>
        </div>
      ))}
    </div>
  );
}
