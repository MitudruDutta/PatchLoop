import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Reveal } from "../Reveal";
import styles from "./SectionHeader.module.css";

type Props = {
  /** The id of the h2, for the section's `aria-labelledby`. */
  id: string;
  heading: ReactNode;
  lede: ReactNode;
  tone?: "light" | "dark";
  className?: string;
};

/** A section heading on the left with its lede on the right, bottom aligned. */
export function SectionHeader({ id, heading, lede, tone = "light", className }: Props) {
  return (
    <Reveal className={cn(styles.header, tone === "dark" && styles.dark, className)}>
      <h2 id={id} className={cn("t-h2 reveal-rise", styles.heading)}>
        {heading}
      </h2>
      <p className={cn("t-lede reveal-rise", styles.stand)} style={{ transitionDelay: "90ms" }}>
        {lede}
      </p>
    </Reveal>
  );
}
