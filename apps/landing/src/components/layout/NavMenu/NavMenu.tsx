"use client";

import { Menu, X } from "lucide-react";
import { useId, useRef, type MouseEvent } from "react";
import { Button } from "@/components/ui/Button";
import { LeadTrigger } from "@/components/ui/LeadDialog";
import { isExternal, nav } from "@/content/site";
import styles from "./NavMenu.module.css";

/** The small-screen menu: a full-height panel in a modal dialog, with the same links as the nav. */
export function NavMenu() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  const close = () => dialogRef.current?.close();

  const onClick = (event: MouseEvent<HTMLDialogElement>) => {
    // The backdrop, or any link inside the panel.
    if (event.target === event.currentTarget || (event.target as Element).closest("a")) close();
  };

  const links = [...nav.links, ...nav.resources.items];

  return (
    <>
      <button
        type="button"
        className={styles.toggle}
        aria-label={nav.menu.open}
        aria-haspopup="dialog"
        onClick={() => dialogRef.current?.showModal()}
      >
        <Menu aria-hidden size={22} />
      </button>
      <dialog ref={dialogRef} className={styles.dialog} aria-labelledby={titleId} onClick={onClick}>
        <div className={styles.panel}>
          <div className={styles.head}>
            <h2 id={titleId} className={styles.title}>
              {nav.menu.title}
            </h2>
            <button type="button" className={styles.close} aria-label={nav.menu.close} onClick={close}>
              <X aria-hidden size={22} />
            </button>
          </div>
          <ul className={styles.list}>
            {links.map((link) => (
              <li key={link.label}>
                <a className={styles.link} href={link.href}>
                  {link.label}
                  {isExternal(link.href) && (
                    <span className={styles.out} aria-hidden>
                      ↗
                    </span>
                  )}
                </a>
              </li>
            ))}
          </ul>
          <div className={styles.actions}>
            <LeadTrigger variant="ghost" size="block" source="menu" onBeforeOpen={close}>
              {nav.talk}
            </LeadTrigger>
            <Button size="block" href={nav.start.href} data-track="cta_click" data-track-location="menu">
              {nav.start.label}
            </Button>
          </div>
        </div>
      </dialog>
    </>
  );
}
