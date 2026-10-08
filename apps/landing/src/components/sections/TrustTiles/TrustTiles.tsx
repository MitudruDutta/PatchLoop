import type { CSSProperties, ReactNode } from "react";
import { TraceWaterfall } from "@/components/mocks/TraceWaterfall";
import { VersionRail } from "@/components/mocks/VersionRail";
import { Chip } from "@/components/ui/Chip";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { trust } from "@/content/trust";
import { cn } from "@/lib/cn";
import styles from "./TrustTiles.module.css";

type TileProps = {
  title: string;
  text: string;
  /** Described to assistive technology in place of the decorative art. */
  alt: string;
  wide?: boolean;
  delay?: number;
  children: ReactNode;
};

function Tile({ title, text, alt, wide = false, delay = 0, children }: TileProps) {
  return (
    <Reveal className={cn("reveal-rise", styles.tile, wide && styles.wide)} style={{ transitionDelay: `${delay}ms` }}>
      <div className={styles.head}>
        <h3 className={cn("t-subhead", styles.title)}>{title}</h3>
        <p className={cn("t-body", styles.text)}>{text}</p>
      </div>
      <div className={styles.art} role="img" aria-label={alt}>
        <div className={styles.artInner} aria-hidden>
          {children}
        </div>
      </div>
    </Reveal>
  );
}

/** Five reasons the result can be audited. */
export function TrustTiles() {
  const { heading, lede, identity, sandbox, trace, promotion, runner } = trust;

  return (
    <section id="trust" className={styles.section} aria-labelledby="trust-heading">
      <div className={styles.inner}>
        <SectionHeader id="trust-heading" heading={heading} lede={lede} className={styles.header} />

        <div className={styles.rows}>
          <div className={styles.row}>
            <Tile {...identity}>
              <div className={styles.identity}>
                {identity.rows.map((row, index) => (
                  <div
                    key={row.source}
                    className={cn("reveal-chip", styles.identityRow)}
                    style={{ transitionDelay: `${200 + index * 90}ms` } as CSSProperties}
                  >
                    <span className={styles.identitySource}>
                      <span className="t-label">{row.source}</span>
                      <code>{row.value}</code>
                    </span>
                    <StatusBadge kind={row.tone === "allow" ? "allowed" : "neutral"}>{row.verdict}</StatusBadge>
                  </div>
                ))}
                <Chip className={cn("reveal-chip", styles.identityChip)}>{identity.chip}</Chip>
              </div>
            </Tile>

            <Tile {...sandbox} delay={90}>
              <div className={styles.sandbox}>
                <span className={cn(styles.ring, styles.ringOuter)} />
                <span className={cn(styles.ring, styles.ringMiddle)} />
                <span className={cn(styles.ring, styles.ringInner)}>
                  <code>{sandbox.core}</code>
                </span>
                {sandbox.chips.map((chip, index) => (
                  <Chip key={chip} mono className={cn("reveal-chip", styles.sandboxChip, index === 1 && styles.sandboxChipLow)}>
                    {chip}
                  </Chip>
                ))}
              </div>
            </Tile>

            <Tile {...trace} delay={180}>
              <div className={styles.trace}>
                <TraceWaterfall />
                <Chip mono className={cn("reveal-chip", styles.traceChip)}>
                  {trace.chip}
                </Chip>
              </div>
            </Tile>
          </div>

          <div className={styles.row}>
            <Tile {...promotion} wide>
              <VersionRail />
            </Tile>

            <Tile {...runner} wide delay={90}>
              <div className={styles.runner}>
                {runner.places.map((place, index) => (
                  <div
                    key={place}
                    className={cn("reveal-chip", styles.place)}
                    style={{ transitionDelay: `${160 + index * 100}ms` } as CSSProperties}
                  >
                    <span className={styles.placeBox}>
                      <code>{runner.core}</code>
                    </span>
                    <Chip>{place}</Chip>
                  </div>
                ))}
              </div>
            </Tile>
          </div>
        </div>
      </div>
    </section>
  );
}
