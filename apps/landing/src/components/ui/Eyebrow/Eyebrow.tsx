import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Eyebrow.module.css";

type Props = { children: ReactNode; className?: string; style?: CSSProperties };

/** A small chip above a headline, with a slow sheen. */
export function Eyebrow({ children, className, style }: Props) {
  return (
    <span className={cn(styles.eyebrow, className)} style={style}>
      {children}
    </span>
  );
}
