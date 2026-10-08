import { cn } from "@/lib/cn";
import styles from "./InlineDocLink.module.css";

type Props = {
  /** The word inside the heading that carries the link. */
  word: string;
  /** Slides out under the word on hover. */
  label: string;
  href: string;
  className?: string;
};

/** A linked word inside a heading. On hover the word turns dotted and a label slides out. */
export function InlineDocLink({ word, label, href, className }: Props) {
  return (
    <a className={cn(styles.native, className)} href={href} aria-label={`${word}: ${label}`}>
      <span>{word}</span>
      <span className={styles.dots} aria-hidden>
        {word}
      </span>
      <span className={styles.lead} aria-hidden>
        <span className={styles.rule} />
        <span className={styles.tick} />
        <span className={styles.label}>{label} ↗</span>
      </span>
    </a>
  );
}
