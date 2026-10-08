import { siteName } from "@/content/site";
import { cn } from "@/lib/cn";
import styles from "./Logo.module.css";

type MarkProps = { size?: number; className?: string };

/** The PatchLoop mark. Same drawing as packages/brand/logo/mark-*.svg, in the current text colour. */
export function LogoMark({ size = 28, className }: MarkProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="0.75" y="0.75" width="26.5" height="26.5" rx="7.25" strokeWidth="1.5" />
      <g transform="translate(14 14) scale(0.6) translate(-12 -12)" strokeWidth="2.5">
        <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
        <path d="M21 3v5h-5" />
      </g>
    </svg>
  );
}

/** The mark followed by the wordmark. */
export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn(styles.logo, className)}>
      <LogoMark />
      <span className={styles.word}>{siteName}</span>
    </span>
  );
}
