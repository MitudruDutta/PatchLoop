import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Button.module.css";

type Common = {
  variant?: "solid" | "ghost";
  /** The surface the button sits on. */
  tone?: "onDark" | "onLight";
  size?: "sm" | "md" | "block";
  className?: string;
  children: ReactNode;
};

type LinkProps = Common & { href: string } & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href" | "className">;
type ButtonProps = Common & { href?: undefined } & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

export type Props = LinkProps | ButtonProps;

/** A link when `href` is given, otherwise a button. */
export function Button(props: Props) {
  const { variant = "solid", tone = "onDark", size = "md", className, children, ...rest } = props;
  const classes = cn(styles.btn, styles[size], styles[variant], tone === "onLight" && styles.onLight, className);

  if (typeof rest.href === "string") {
    return (
      <a className={classes} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)}>
        {children}
      </a>
    );
  }

  const { type = "button", ...buttonRest } = rest as ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button className={classes} type={type} {...buttonRest}>
      {children}
    </button>
  );
}
