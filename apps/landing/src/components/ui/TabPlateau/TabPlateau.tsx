"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";
import styles from "./TabPlateau.module.css";

type Props = {
  tabs: readonly { id: string; label: string }[];
  active: number;
  onSelect: (index: number) => void;
  /** Accessible name of the tab list. */
  label: string;
  previousLabel: string;
  nextLabel: string;
  /** Tab ids are `${idPrefix}-tab-${id}`; they all control `${idPrefix}-panel`. */
  idPrefix: string;
  className?: string;
};

/**
 * Tabs in a notch that hangs from the top edge of a frame. When there is no
 * room for every tab it becomes a stepper: the active tab, a counter and
 * previous and next buttons.
 */
export function TabPlateau({ tabs, active, onSelect, label, previousLabel, nextLabel, idPrefix, className }: Props) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const count = tabs.length;

  const move = (index: number, focus: boolean) => {
    const next = (index + count) % count;
    onSelect(next);
    if (focus) tabRefs.current[next]?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keys: Record<string, number> = {
      ArrowRight: active + 1,
      ArrowLeft: active - 1,
      Home: 0,
      End: count - 1,
    };
    if (!(event.key in keys)) return;
    event.preventDefault();
    move(keys[event.key], true);
  };

  return (
    <div className={cn(styles.hold, className)}>
      <div className={styles.strip}>
        <button type="button" className={styles.step} aria-label={previousLabel} onClick={() => move(active - 1, false)}>
          <ChevronLeft aria-hidden size={16} />
        </button>
        <div role="tablist" aria-label={label} className={styles.tabs} onKeyDown={onKeyDown}>
          {tabs.map((tab, index) => (
            <button
              key={tab.id}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              type="button"
              role="tab"
              id={`${idPrefix}-tab-${tab.id}`}
              aria-selected={index === active}
              aria-controls={`${idPrefix}-panel`}
              tabIndex={index === active ? 0 : -1}
              data-active={index === active || undefined}
              className={styles.tab}
              onClick={() => onSelect(index)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <span className={styles.count} aria-hidden>
          {active + 1} / {count}
        </span>
        <button type="button" className={styles.step} aria-label={nextLabel} onClick={() => move(active + 1, false)}>
          <ChevronRight aria-hidden size={16} />
        </button>
      </div>
    </div>
  );
}
