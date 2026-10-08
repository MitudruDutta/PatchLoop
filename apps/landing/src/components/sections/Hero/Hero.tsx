import { ArrowDown, ArrowRight } from "lucide-react";
import { LoopField } from "@/components/art/LoopField";
import { SiteNav } from "@/components/layout/SiteNav";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { hero } from "@/content/hero";
import { cn } from "@/lib/cn";
import styles from "./Hero.module.css";

export function Hero() {
  return (
    <section className={styles.hero} aria-label={hero.sectionLabel}>
      <div className={styles.light} aria-hidden />
      <div className={styles.art} aria-hidden>
        <div className={styles.pool} />
        <LoopField id="hero-loop" className={styles.loop} />
      </div>
      <div className={styles.feather} aria-hidden />

      <SiteNav />

      <div className={styles.copy}>
        <Eyebrow className={styles.arrive}>{hero.eyebrow}</Eyebrow>
        <h1 className={cn(styles.headline, styles.arrive)} style={{ animationDelay: "110ms" }}>
          {hero.headline[0]} <br />
          <span className={styles.foil}>{hero.headline[1]}</span>
        </h1>
        <p className={cn("t-hero-lede", styles.lede, styles.arrive)} style={{ animationDelay: "250ms" }}>
          {hero.lede}
        </p>
        <div className={cn(styles.actions, styles.arrive)} style={{ animationDelay: "380ms" }}>
          <Button href={hero.primary.href} data-track="cta_click" data-track-location="hero">
            {hero.primary.label}
            <ArrowRight className={styles.go} size={16} strokeWidth={1.5} aria-hidden />
          </Button>
          <Button variant="ghost" href={hero.secondary.href} data-track="cta_click" data-track-location="hero">
            {hero.secondary.label}
            <ArrowDown className={styles.down} size={16} strokeWidth={1.5} aria-hidden />
          </Button>
        </div>
      </div>
    </section>
  );
}
