import { ArrowUpRight } from "lucide-react";
import { Container } from "@/components/layout/Container";
import { Reveal } from "@/components/ui/Reveal";
import { builtOn } from "@/content/built-on";
import { cn } from "@/lib/cn";
import styles from "./BuiltOn.module.css";

/** What PatchLoop is built on, as text chips, and a ticker of its real commands. */
export function BuiltOn() {
  const { sectionLabel, lede, chips, commands, tickerLabel } = builtOn;

  return (
    <section className={styles.section} aria-label={sectionLabel}>
      <Container className={styles.inner}>
        <Reveal className={styles.say}>
          <p className={cn("t-lede reveal-rise", styles.lede)}>{lede}</p>
          <ul className={styles.links}>
            {chips.map((chip, index) => (
              <li key={chip.label} className="reveal-rise" style={{ transitionDelay: `${80 + index * 60}ms` }}>
                <a className={styles.link} href={chip.href} data-track="outbound" data-track-location="built-on">
                  {chip.label}
                  <ArrowUpRight aria-hidden className={styles.arrow} size={15} strokeWidth={1.5} />
                </a>
              </li>
            ))}
          </ul>
        </Reveal>

        {/* The list is repeated once so the loop has no seam. The copy is hidden from assistive technology. */}
        <div className={styles.marquee}>
          <div className={styles.track}>
            <ul className={styles.group} aria-label={tickerLabel}>
              {commands.map((command) => (
                <li key={command.name} className={styles.item}>
                  <a className={styles.command} href={command.href}>
                    {command.text}
                  </a>
                </li>
              ))}
            </ul>
            <ul className={cn(styles.group, styles.duplicate)} aria-hidden>
              {commands.map((command) => (
                <li key={command.name} className={styles.item}>
                  <a className={styles.command} href={command.href} tabIndex={-1}>
                    {command.text}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Container>
    </section>
  );
}
