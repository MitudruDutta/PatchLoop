import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Chip.module.css";

type Props = {
  children: ReactNode;
  /** `card` sits on a light mock surface, `glass` on the dark field, `signal` is the accent on dark. */
  variant?: "card" | "glass" | "signal";
  mono?: boolean;
  className?: string;
};

/** A small rounded label. */
export function Chip({ children, variant = "card", mono = false, className }: Props) {
  return <span className={cn(styles.chip, styles[variant], mono && styles.mono, className)}>{children}</span>;
}
