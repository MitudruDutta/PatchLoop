import { LoopField } from "@/components/art/LoopField";
import { Button } from "@/components/ui/Button";
import { LeadTrigger } from "@/components/ui/LeadDialog";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { pricing } from "@/content/pricing";
import { plannedTag } from "@/content/site";
import { cn } from "@/lib/cn";
import styles from "./Pricing.module.css";

function Tick() {
  return (
    <svg className={styles.tick} width="10" height="8" viewBox="0 0 10 8" fill="none" aria-hidden>
      <path d="M1 4.2 3.6 6.8 9 1.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Two plans: what is free today, and what is being built with design partners. No prices. */
export function Pricing() {
  const { heading, lede, plans } = pricing;

  return (
    <section id="pricing" className={styles.section} aria-labelledby="pricing-heading">
      <div className={styles.backdrop} aria-hidden>
        <LoopField id="pricing-loop" quiet />
      </div>

      <div className={styles.inner}>
        <div className={styles.header}>
          <h2 id="pricing-heading" className={cn("t-h2", styles.heading)}>
            {heading}
          </h2>
          <div className={styles.aside}>
            <p className={cn("t-lede", styles.stand)}>{lede}</p>
          </div>
        </div>

        <div className={styles.plans}>
          {plans.map((plan) => (
            <article
              key={plan.id}
              className={cn(styles.plan, plan.solid && styles.planSolid)}
              aria-labelledby={`plan-${plan.id}`}
            >
              <h3 id={`plan-${plan.id}`} className={styles.name}>
                {plan.name}
              </h3>
              <p className={styles.blurb}>{plan.blurb}</p>
              <p className={styles.price}>{plan.price}</p>
              <p className={styles.priceNote}>{plan.priceNote}</p>

              <div className={styles.action}>
                {plan.action.kind === "lead" ? (
                  <LeadTrigger tone="onLight" size="block" source="pricing">
                    {plan.action.label}
                  </LeadTrigger>
                ) : (
                  <Button
                    variant="ghost"
                    size="block"
                    href={plan.action.href}
                    data-track="cta_click"
                    data-track-location="pricing"
                  >
                    {plan.action.label}
                  </Button>
                )}
              </div>

              <div className={styles.rule} />
              {plan.lead && <p className={styles.lead}>{plan.lead}</p>}
              <ul className={cn(styles.features, plan.lead && styles.featuresWithLead)}>
                {plan.features.map((feature) => (
                  <li key={feature.text} className={styles.feature}>
                    <Tick />
                    <span className={styles.featureText}>{feature.text}</span>
                    {feature.planned && <StatusBadge kind="planned">{plannedTag}</StatusBadge>}
                  </li>
                ))}
              </ul>

              {plan.footnote && (
                <p className={styles.note}>
                  <span className={styles.noteRule} />
                  {plan.footnote.text}{" "}
                  <a className={styles.noteLink} href={plan.footnote.link.href}>
                    {plan.footnote.link.label}
                  </a>
                </p>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
