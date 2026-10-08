"use client";

import { useEffect, type RefObject } from "react";

type Options = {
  /** Number of stops. `--pos` runs from 0 to steps - 1. */
  steps?: number;
  /**
   * "through": 0 when the element's top reaches the viewport top, 1 when its
   * bottom reaches the viewport bottom. For tall runways with a sticky child.
   * "enter": 0 when the element's top is at the viewport bottom, 1 when its
   * top reaches the viewport top.
   */
  mode?: "through" | "enter";
  /** Called when the nearest stop changes. */
  onStep?: (index: number) => void;
};

/**
 * Writes scroll progress onto an element as CSS variables: `--pp` (0 to 1)
 * and `--pos` (0 to steps - 1). Styles read them, so scrolling never re-renders.
 */
export function usePinnedProgress(ref: RefObject<HTMLElement | null>, options: Options = {}): void {
  const { steps = 2, mode = "through", onStep } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    let frame = 0;
    let lastStep = -1;

    const update = () => {
      frame = 0;
      const rect = element.getBoundingClientRect();
      const viewport = window.innerHeight;
      let progress: number;
      if (mode === "enter") {
        progress = (viewport - rect.top) / viewport;
      } else {
        const span = rect.height - viewport;
        progress = span > 0 ? -rect.top / span : 0;
      }
      progress = Math.min(1, Math.max(0, progress));
      const position = progress * (steps - 1);
      element.style.setProperty("--pp", progress.toFixed(4));
      element.style.setProperty("--pos", position.toFixed(4));

      const step = Math.round(position);
      if (step !== lastStep) {
        lastStep = step;
        onStep?.(step);
      }
    };

    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    schedule();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [ref, steps, mode, onStep]);
}
