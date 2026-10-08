import { Ban, Check, CircleDashed, Clock, FlaskConical, Minus, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import styles from "./StatusBadge.module.css";

export type StatusKind = "allowed" | "denied" | "indeterminate" | "neutral" | "planned" | "illustrative";

const icons: Record<StatusKind, LucideIcon> = {
  allowed: Check,
  denied: Ban,
  indeterminate: CircleDashed,
  neutral: Minus,
  planned: Clock,
  illustrative: FlaskConical,
};

type Props = {
  kind: StatusKind;
  /** The word shown beside the icon. A verdict is never colour alone. */
  children: string;
  surface?: "light" | "dark";
  className?: string;
};

/** A verdict or status: always an icon and a word together. */
export function StatusBadge({ kind, children, surface = "light", className }: Props) {
  const Icon = icons[kind];
  return (
    <span className={cn(styles.badge, styles[kind], surface === "dark" && styles.dark, className)}>
      <Icon aria-hidden size={12} strokeWidth={2} />
      {children}
    </span>
  );
}
