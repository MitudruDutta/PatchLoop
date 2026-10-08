"use client";

import { useRef, useState, type CSSProperties } from "react";
import { CallField } from "@/components/art/CallField";
import { Container } from "@/components/layout/Container";
import { Button } from "@/components/ui/Button";
import { InlineDocLink } from "@/components/ui/InlineDocLink";
import { stages } from "@/content/stages";
import { usePinnedProgress } from "@/hooks/usePinnedProgress";
import { cn } from "@/lib/cn";
import styles from "./RuleStages.module.css";

const STAGE_IDS = [0, 1, 2] as const;

/**
 * Three stages of where a rule lives. With motion and scripting, the stages
 * share one pinned viewport and cross-fade as the page scrolls. Otherwise they
 * are stacked one after another; the CSS decides, so there is no layout jump.
 */
export function RuleStages() {
  const runwayRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  usePinnedProgress(runwayRef, { steps: stages.panes.length, onStep: setActive });

  const { heading, panes, cta } = stages;
  const last = panes.length - 1;

  return (
    <section className={styles.section} aria-labelledby="stages-heading">
      <div className={styles.headingRow}>
        <Container>
          <h2 id="stages-heading" className={cn("t-h2", styles.heading)}>
            {heading.before}
            <InlineDocLink {...heading.link} />
            {heading.after}
          </h2>
        </Container>
      </div>

      <div ref={runwayRef} className={styles.runway}>
        <div className={styles.pin}>
          <Container className={styles.grid}>
            {panes.map((pane, index) => (
              <div
                key={pane.label}
                className={cn(styles.pane, index === active && styles.paneActive)}
                style={{ "--i": index } as CSSProperties}
              >
                <div className={styles.copy}>
                  <h3 className={styles.label}>{pane.label}</h3>
                  <p className={styles.body}>{pane.body}</p>
                  {index === last && (
                    <div className={styles.cta}>
                      <Button tone="onLight" href={cta.href} data-track="cta_click" data-track-location="stages">
                        {cta.label}
                      </Button>
                    </div>
                  )}
                </div>
                <div className={styles.art} role="img" aria-label={pane.artAlt}>
                  <CallField stage={STAGE_IDS[index]} />
                </div>
              </div>
            ))}
          </Container>
        </div>
      </div>
    </section>
  );
}
