"use client";

import { useEffect } from "react";

type Options = {
  /** Number of items to cycle through. */
  count: number;
  /** The item currently shown. */
  index: number;
  /** Time each item stays open, in milliseconds. */
  dwell: number;
  /** While true the timer is stopped. It restarts from zero when released. */
  paused: boolean;
  onAdvance: (next: number) => void;
};

/** Moves to the next item after `dwell` ms. The timer resets whenever `index` changes. */
export function useAutoAdvance({ count, index, dwell, paused, onAdvance }: Options): void {
  useEffect(() => {
    if (paused || count < 2) return;
    const timer = window.setTimeout(() => onAdvance((index + 1) % count), dwell);
    return () => window.clearTimeout(timer);
  }, [count, index, dwell, paused, onAdvance]);
}
