import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./MockCard.module.css";

type Props = {
  title: string;
  /** Sits at the right of the title: a badge or a tag. */
  aside?: ReactNode;
  /** Read out in place of the card, which is decorative. */
  alt: string;
  children: ReactNode;
  className?: string;
};

/**
 * The white card every product mock is drawn on. Mocks are pictures of the
 * product, so the card is one image to assistive technology, described by `alt`.
 */
export function MockCard({ title, aside, alt, children, className }: Props) {
  return (
    <div className={cn(styles.card, className)} role="img" aria-label={alt}>
      <div className={styles.inner} aria-hidden>
        <div className={styles.head}>
          <span className={styles.title}>{title}</span>
          {aside}
        </div>
        {children}
      </div>
    </div>
  );
}
