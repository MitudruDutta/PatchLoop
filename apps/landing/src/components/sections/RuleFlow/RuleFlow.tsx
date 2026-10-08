"use client";

import { Ban, FileText, MessageCircleQuestion, ScanSearch, Zap, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { TabPlateau } from "@/components/ui/TabPlateau";
import { rules, type ThenKind } from "@/content/rules";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/cn";
import styles from "./RuleFlow.module.css";

const thenIcons: Record<ThenKind, LucideIcon> = { deny: Ban, record: FileText, ask: MessageCircleQuestion };

function Node({
  icon: Icon,
  label,
  tone,
  children,
}: {
  icon: LucideIcon;
  label: string;
  tone?: "deny";
  children: ReactNode;
}) {
  return (
    <div className={cn(styles.node, tone === "deny" && styles.nodeDeny)}>
      <span className={styles.nodeIcon}>
        <Icon aria-hidden size={18} strokeWidth={1.5} />
      </span>
      <span className={styles.nodeCopy}>
        <span className={cn("t-label", styles.nodeLabel)}>{label}</span>
        <span className={styles.nodeText}>{children}</span>
      </span>
    </div>
  );
}

/** A straight wire between two nodes, with a pulse travelling along it. */
function Wire() {
  return (
    <span className={styles.wire} aria-hidden>
      <svg className={styles.wireH} viewBox="0 0 96 84" fill="none">
        <path className={styles.line} d="M0 42H96" />
        <circle className={styles.pulse} r="3">
          <animateMotion dur="2.6s" repeatCount="indefinite" path="M0 42H96" />
        </circle>
      </svg>
      <span className={styles.wireV} />
    </span>
  );
}

/** One wire that splits to reach the two "then" nodes. */
function Fork() {
  const top = "M0 104C52 104 44 42 96 42";
  const bottom = "M0 104C52 104 44 166 96 166";
  return (
    <span className={styles.wire} aria-hidden>
      <svg className={styles.forkH} viewBox="0 0 96 208" fill="none">
        <path className={styles.line} d={top} />
        <path className={styles.line} d={bottom} />
        <circle className={styles.pulse} r="3">
          <animateMotion dur="2.6s" begin="0.9s" repeatCount="indefinite" path={top} />
        </circle>
        <circle className={styles.pulse} r="3">
          <animateMotion dur="2.6s" begin="0.9s" repeatCount="indefinite" path={bottom} />
        </circle>
      </svg>
      <span className={styles.wireV} />
    </span>
  );
}

/** The four violation types as When, Check, Then flows, one per tab. */
export function RuleFlow() {
  const { heading, lede, items, labels, tablistLabel, previous, next } = rules;
  const [active, setActive] = useState(0);
  const rule = items[active];

  const select = (index: number) => {
    setActive(index);
    track("rule_tab", { rule: items[index].id });
  };

  return (
    <section id="rules" className={styles.section} aria-labelledby="rules-heading">
      <div className={styles.inner}>
        <SectionHeader id="rules-heading" heading={heading} lede={lede} />

        <Reveal className={cn("reveal-chip", styles.frame)}>
          <TabPlateau
            tabs={items.map((item) => ({ id: item.id, label: item.tab }))}
            active={active}
            onSelect={select}
            label={tablistLabel}
            previousLabel={previous}
            nextLabel={next}
            idPrefix="rules"
          />
          <div className={styles.grid} aria-hidden />
          <div className={styles.bloom} aria-hidden />

          <div
            id="rules-panel"
            className={styles.panel}
            role="tabpanel"
            aria-labelledby={`rules-tab-${rule.id}`}
            tabIndex={0}
          >
            {/* Keyed by rule so each change replays the swap. */}
            <div key={rule.id} className={styles.row}>
              <Node icon={Zap} label={labels.when}>
                {rule.when.code && <code className={styles.code}>{rule.when.code}</code>} {rule.when.text}
              </Node>
              <Wire />
              <Node icon={ScanSearch} label={labels.check}>
                {rule.check}
              </Node>
              <Fork />
              <div className={styles.thenColumn}>
                {rule.then.map((outcome, index) => (
                  <div key={outcome.kind} className={styles.thenItem}>
                    {index > 0 && <span className={styles.thenGap} aria-hidden />}
                    <Node
                      icon={thenIcons[outcome.kind]}
                      label={labels[outcome.kind]}
                      tone={outcome.kind === "deny" ? "deny" : undefined}
                    >
                      {outcome.text}
                    </Node>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
