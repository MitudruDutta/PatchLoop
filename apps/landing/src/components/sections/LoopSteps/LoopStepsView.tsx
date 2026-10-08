"use client";

import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { InlineDocLink } from "@/components/ui/InlineDocLink";
import { steps } from "@/content/steps";
import { useAutoAdvance } from "@/hooks/useAutoAdvance";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import styles from "./LoopSteps.module.css";

type Props = {
  /** One mock per step, in step order. Rendered on the server. */
  visuals: ReactNode[];
};

export function LoopStepsView({ visuals }: Props) {
  const { heading, lede, items, dwellMs } = steps;
  const [active, setActive] = useState(0);
  const [held, setHeld] = useState(false);
  const [inView, setInView] = useState(false);
  const reduced = useReducedMotion();
  const sectionRef = useRef<HTMLElement>(null);
  const baseId = useId();

  // Count only while the section is on screen.
  useEffect(() => {
    const element = sectionRef.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: 0.35 });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const counting = inView && !held && !reduced;
  useAutoAdvance({ count: items.length, index: active, dwell: dwellMs, paused: !counting, onAdvance: setActive });

  const select = (index: number) => {
    setActive(index);
    track("step_select", { step: items[index].id });
  };

  return (
    <section ref={sectionRef} id="how-it-works" className={styles.section} aria-labelledby={`${baseId}-heading`}>
      <div className={styles.inner}>
        <header className={styles.header}>
          <h2 id={`${baseId}-heading`} className={cn("t-h2", styles.heading)}>
            {heading.before}
            <InlineDocLink {...heading.link} />
            {heading.after}
          </h2>
          <p className={cn("t-lede", styles.stand)}>{lede}</p>
        </header>

        <div className={styles.columns}>
          {/* Hovering or focusing the rail holds the timer. It never moves focus. */}
          <div
            className={styles.rail}
            onMouseEnter={() => setHeld(true)}
            onMouseLeave={() => setHeld(false)}
            onFocus={() => setHeld(true)}
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setHeld(false);
            }}
          >
            {items.map((item, index) => {
              const isActive = index === active;
              const triggerId = `${baseId}-trigger-${item.id}`;
              const panelId = `${baseId}-panel-${item.id}`;
              return (
                <div key={item.id}>
                  {index > 0 && <div className={styles.divider} />}
                  <div className={cn(styles.step, isActive && styles.stepActive, isActive && counting && styles.counting)}>
                    <span className={styles.tick} aria-hidden style={{ "--dwell": `${dwellMs}ms` } as CSSProperties} />
                    <h3 className={styles.stepHeading}>
                      <button
                        type="button"
                        id={triggerId}
                        className={styles.trigger}
                        aria-expanded={isActive}
                        aria-controls={panelId}
                        onClick={() => select(index)}
                      >
                        <span className={styles.marker} aria-hidden />
                        <span className={styles.stepTitle}>{item.title}</span>
                      </button>
                    </h3>
                    <div id={panelId} className={styles.bodyTrack} role="region" aria-labelledby={triggerId}>
                      <p className={styles.stepBody}>{item.body}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className={styles.visualCell}>
            {visuals.map((visual, index) => (
              <div key={items[index].id} className={cn(styles.visual, index === active && styles.visualActive)}>
                {visual}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
