"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  /** Share of the element that must be on screen before it goes live. */
  threshold?: number;
  id?: string;
  "aria-hidden"?: boolean;
};

/**
 * Marks its element `data-reveal="pending"` if it mounts below the fold, then
 * `data-reveal="live"` once it scrolls in. The reveal-* classes in
 * styles/motion.css and component styles key off that attribute.
 *
 * The attribute is set on the DOM node directly, so the server HTML carries no
 * hidden state: without scripting, or with reduced motion, nothing is hidden.
 */
export function Reveal({ children, threshold = 0.2, ...rest }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const rect = element.getBoundingClientRect();
    const onScreen = rect.top < window.innerHeight && rect.bottom > 0;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (onScreen || reduced) {
      element.dataset.reveal = "live";
      return;
    }

    element.dataset.reveal = "pending";
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          element.dataset.reveal = "live";
          observer.disconnect();
        }
      },
      { threshold: [0, threshold], rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold]);

  return (
    <div ref={ref} {...rest}>
      {children}
    </div>
  );
}
