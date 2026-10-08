"use client";

import { useId, useState } from "react";
import { Container } from "@/components/layout/Container";
import { faq } from "@/content/faq";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import styles from "./Faq.module.css";

/** Questions and answers. One row is open at a time; the first starts open. */
export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  const baseId = useId();

  const toggle = (index: number) => {
    const next = open === index ? null : index;
    setOpen(next);
    if (next !== null) track("faq_open", { question: index + 1 });
  };

  return (
    <section id="faq" className={styles.section} aria-labelledby={`${baseId}-title`}>
      <Container className={styles.inner}>
        <div className={styles.heading}>
          <h2 id={`${baseId}-title`} className="t-h2">
            {faq.heading}
          </h2>
        </div>

        <div className={styles.list}>
          {faq.items.map((item, index) => {
            const isOpen = open === index;
            return (
              <div key={item.question} className={cn(styles.row, isOpen && styles.isOpen)}>
                <h3 className={styles.questionHeading}>
                  <button
                    type="button"
                    id={`${baseId}-trigger-${index}`}
                    className={styles.trigger}
                    aria-expanded={isOpen}
                    aria-controls={`${baseId}-panel-${index}`}
                    onClick={() => toggle(index)}
                  >
                    <span className={styles.question}>{item.question}</span>
                    <svg className={styles.mark} width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                      <path d="M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      <path
                        className={styles.markStem}
                        d="M7 1v12"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                </h3>
                <div
                  id={`${baseId}-panel-${index}`}
                  className={styles.body}
                  role="region"
                  aria-labelledby={`${baseId}-trigger-${index}`}
                >
                  <p className={styles.answer}>
                    <span className={styles.answerInner}>{item.answer}</span>
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
