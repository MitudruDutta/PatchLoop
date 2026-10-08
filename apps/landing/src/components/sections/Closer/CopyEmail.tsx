"use client";

import { useEffect, useState } from "react";
import { closer } from "@/content/closer";
import { track } from "@/lib/analytics";
import styles from "./Closer.module.css";

/** The contact address with a button that copies it. */
export function CopyEmail({ email }: { email: string }) {
  const [copied, setCopied] = useState(false);
  const { contact } = closer;

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      track("copy_command", { target: "email" });
    } catch {
      // Clipboard access was refused. The address is still a mailto link.
    }
  };

  return (
    <div className={styles.emailField}>
      <a className={styles.contactEmail} href={`mailto:${email}`}>
        {email}
      </a>
      <button type="button" className={styles.copyEmail} aria-label={contact.copyLabel(email)} onClick={copy}>
        <span aria-live="polite">{copied ? contact.copied : contact.copy}</span>
      </button>
    </div>
  );
}
