import { Check } from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { evidence } from "@/content/evidence.generated";
import { ledger } from "@/content/ledger";
import { validationMock } from "@/content/steps";
import { MockCard } from "../MockCard";
import styles from "./ValidationCard.module.css";

/** One row per validation gate, with its count from the evidence, ending in the promotion. */
export function ValidationCard({ className }: { className?: string }) {
  const { guard, archive } = evidence;
  return (
    <MockCard
      className={className}
      title={validationMock.title}
      alt={validationMock.alt}
      aside={<StatusBadge kind="allowed">{validationMock.promoted(guard.shortHash)}</StatusBadge>}
    >
      <ul className={styles.rows}>
        {ledger.gates.rows.map((gate) => (
          <li key={gate.label} className={styles.row}>
            <span className={styles.tick}>
              <Check aria-hidden size={12} strokeWidth={2.5} />
            </span>
            <span className={styles.label}>{gate.label}</span>
            <span className={styles.count}>{gate.count}</span>
          </li>
        ))}
      </ul>
      <p className={styles.note}>{validationMock.conflictNote(archive.conflictIds.join(", "))}</p>
    </MockCard>
  );
}
