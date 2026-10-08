import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Container.module.css";

/** Centres content on the page rail (1320 px at most, with the page gutter). */
export function Container({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn(styles.rail, className)}>{children}</div>;
}
