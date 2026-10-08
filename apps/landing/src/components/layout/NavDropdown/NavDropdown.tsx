"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { isExternal, type NavLink } from "@/content/site";
import styles from "./NavDropdown.module.css";

type Props = { label: string; items: readonly NavLink[] };

/** A disclosure in the nav. Opens on hover and on click, closes on Escape or when focus leaves. */
export function NavDropdown({ label, items }: Props) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    const onPointerDown = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  return (
    <div
      ref={wrapRef}
      className={styles.wrap}
      data-open={open || undefined}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {label}
        <ChevronDown aria-hidden className={styles.chevron} size={13} />
      </button>
      {open && (
        <div id={panelId} className={styles.panel}>
          {/* Keeps the hover alive across the gap between trigger and panel. */}
          <span className={styles.bridge} aria-hidden />
          <ul className={styles.list}>
            {items.map((item) => (
              <li key={item.label}>
                <a className={styles.item} href={item.href} data-track="outbound" data-track-location="nav-resources">
                  {item.label}
                  {isExternal(item.href) && (
                    <span className={styles.out} aria-hidden>
                      ↗
                    </span>
                  )}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
