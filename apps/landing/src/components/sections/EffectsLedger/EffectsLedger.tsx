import type { CSSProperties } from "react";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { ledger } from "@/content/ledger";
import { cn } from "@/lib/cn";
import { LedgerReadouts } from "./LedgerReadouts";
import styles from "./EffectsLedger.module.css";

/**
 * What was attempted, what executed and what still works, read from the
 * evidence files. Every figure here comes from content/evidence.generated.ts.
 */
export function EffectsLedger() {
  const { heading, lede, tools, gates, sourceLabel, note, noteLink, scope } = ledger;

  return (
    <section id="evidence" className={styles.section} aria-labelledby="ledger-heading">
      <div className={styles.inner}>
        <SectionHeader id="ledger-heading" heading={heading} lede={lede} tone="dark" />

        <Reveal className={styles.board}>
          <LedgerReadouts />
          <div className={cn("reveal-rise", styles.hairline)} style={{ transitionDelay: "120ms" }} />

          <div className={styles.body}>
            <div className={cn("reveal-rise", styles.tools)} style={{ transitionDelay: "160ms" }}>
              <table className={styles.table}>
                <caption className="sr-only-text">{tools.title}</caption>
                <thead>
                  <tr>
                    <th scope="col">{tools.columns.tool}</th>
                    <th scope="col">{tools.columns.kind}</th>
                  </tr>
                </thead>
                <tbody>
                  {tools.rows.map((tool) => (
                    <tr key={tool.name}>
                      <td>
                        <code>{tool.name}</code>
                      </td>
                      <td>{tools.kinds[tool.kind]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className={cn("reveal-rise", styles.gates)} style={{ transitionDelay: "220ms" }}>
              <h3 className={styles.gatesTitle}>{gates.title}</h3>
              <ul className={styles.gateList}>
                {gates.rows.map((gate, index) => (
                  <li key={gate.label} className={styles.gate} tabIndex={0}>
                    <span className={styles.gateLabel}>{gate.label}</span>
                    <span className={styles.gateCount}>
                      {gate.count}
                      <span className="sr-only-text"> {gates.passedLabel}</span>
                    </span>
                    <span className={styles.gateTrack} aria-hidden>
                      <span
                        className={cn("reveal-bar", styles.gateBar)}
                        style={{ transitionDelay: `${260 + index * 70}ms` } as CSSProperties}
                      />
                    </span>
                    <span className={styles.provenance}>
                      <span className="t-label">{sourceLabel}</span>
                      {gate.source}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className={cn("reveal-rise", styles.note)} style={{ transitionDelay: "300ms" }}>
            {note}{" "}
            <a className={styles.noteLink} href={noteLink.href} data-track="outbound" data-track-location="ledger">
              {noteLink.label}
            </a>
          </p>
          <p className={cn("t-eyebrow reveal-rise", styles.scope)} style={{ transitionDelay: "340ms" }}>
            {scope}
          </p>
        </Reveal>
      </div>
    </section>
  );
}
