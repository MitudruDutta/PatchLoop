import { cn } from "@/lib/cn";
import styles from "./LoopMark.module.css";

/** A small ring with one call circling it. Decorative. */
export function LoopMark({ className }: { className?: string }) {
  return (
    <svg className={cn(styles.mark, className)} width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden>
      <circle className={styles.ring} cx="22" cy="22" r="16" />
      <circle className={styles.ringInner} cx="22" cy="22" r="9" />
      <g className={styles.orbit}>
        <circle className={styles.dot} cx="22" cy="6" r="2.75" />
      </g>
    </svg>
  );
}
