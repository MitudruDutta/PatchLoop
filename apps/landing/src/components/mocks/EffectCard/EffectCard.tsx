import { StatusBadge } from "@/components/ui/StatusBadge";
import { effectMock } from "@/content/steps";
import { cn } from "@/lib/cn";
import { MockCard } from "../MockCard";
import styles from "./EffectCard.module.css";

/** What actually changed in the data after a tool call, and why it is a violation. */
export function EffectCard({ className }: { className?: string }) {
  const { title, record, rows, session, badge, note, columns, alt } = effectMock;
  return (
    <MockCard
      className={className}
      title={title}
      alt={alt}
      aside={<StatusBadge kind="denied">{badge}</StatusBadge>}
    >
      <code className={styles.record}>{record}</code>
      <div className={styles.table}>
        <span className={cn("t-label", styles.th)}>{columns.field}</span>
        <span className={cn("t-label", styles.th)}>{columns.before}</span>
        <span className={cn("t-label", styles.th)}>{columns.after}</span>
        {rows.map((row) => {
          const changed = row.before !== row.after;
          return (
            <div key={row.field} className={styles.row}>
              <code className={styles.field}>{row.field}</code>
              <code className={styles.value}>{row.before}</code>
              <code className={cn(styles.value, changed && styles.changed)}>{row.after}</code>
            </div>
          );
        })}
      </div>
      <p className={styles.note}>
        <span>
          {session.label} <code className={styles.session}>{session.value}</code>
        </span>
        <span>{note}</span>
      </p>
    </MockCard>
  );
}
