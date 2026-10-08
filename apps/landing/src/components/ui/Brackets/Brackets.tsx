import { cn } from "@/lib/cn";
import styles from "./Brackets.module.css";

const corners = ["tl", "tr", "bl", "br"] as const;

/**
 * Four corner arms drawn inside a positioned parent. Size and colour come from
 * `--bracket-arm` and `--bracket-color` on that parent.
 */
export function Brackets() {
  return (
    <>
      {corners.map((corner) => (
        <span key={corner} aria-hidden className={cn(styles.arm, styles[corner])} />
      ))}
    </>
  );
}
