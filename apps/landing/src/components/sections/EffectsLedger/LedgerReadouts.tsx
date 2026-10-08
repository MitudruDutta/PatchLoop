"use client";

import { useState, type CSSProperties } from "react";
import { Chip } from "@/components/ui/Chip";
import { ledger, type LedgerMode } from "@/content/ledger";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import styles from "./EffectsLedger.module.css";

/** The three readouts and the Baseline / Guarded switch that changes them. */
export function LedgerReadouts() {
  const { toggle, readouts, conflictChip, sourceLabel } = ledger;
  const [mode, setMode] = useState<LedgerMode>(toggle.initial);
  const activeIndex = toggle.options.findIndex((option) => option.id === mode);

  const choose = (next: LedgerMode) => {
    if (next === mode) return;
    setMode(next);
    track("ledger_toggle", { mode: next });
  };

  return (
    <div className={cn("reveal-rise", styles.readoutRow)}>
      <dl className={styles.readouts}>
        {readouts.map((readout, index) => {
          const last = index === readouts.length - 1;
          return (
            <div key={readout.label} className={styles.readout} tabIndex={0}>
              <dt className={styles.readoutLabel}>{readout.label}</dt>
              <dd className={styles.readoutValueRow}>
                {/* Keyed by mode so the value re-enters with a short fade. */}
                <span key={mode} className={cn("t-value", styles.readoutValue)}>
                  {readout[mode]}
                </span>
                {last && mode === "guarded" && (
                  <a className={styles.conflict} href={conflictChip.href} title={conflictChip.title}>
                    <Chip variant="signal">{conflictChip.text}</Chip>
                  </a>
                )}
                <span className={styles.provenance}>
                  <span className="t-label">{sourceLabel}</span>
                  {readout.source}
                </span>
              </dd>
            </div>
          );
        })}
      </dl>

      <div className={styles.pill} role="group" aria-label={toggle.label}>
        <span
          className={styles.pillThumb}
          aria-hidden
          style={{ transform: `translateX(${activeIndex * 100}%)` } as CSSProperties}
        />
        {toggle.options.map((option) => (
          <button
            key={option.id}
            type="button"
            className={styles.pillButton}
            aria-pressed={option.id === mode}
            data-active={option.id === mode || undefined}
            onClick={() => choose(option.id)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
