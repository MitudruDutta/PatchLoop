"use client";

import { X } from "lucide-react";
import {
  createContext,
  use,
  useCallback,
  useId,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import { lead } from "@/content/lead";
import { contactEmail, leadEndpoint } from "@/content/site";
import { track } from "@/lib/analytics";
import { Button, type Props as ButtonProps } from "../Button";
import styles from "./LeadDialog.module.css";

type LeadContextValue = { open: (source: string) => void };

const LeadContext = createContext<LeadContextValue | null>(null);

/** Opens the "Talk to us" dialog. `source` names the button, for analytics. */
export function useLeadDialog(): LeadContextValue["open"] {
  const context = use(LeadContext);
  return context?.open ?? (() => {});
}

type Phase = "form" | "sending" | "sent" | "mailto";
type Field = "name" | "email" | "agent";
type Errors = Partial<Record<Field | "send", string>>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Holds the one dialog for the page. Wrap the page in it; open it with `LeadTrigger`. */
export function LeadDialogProvider({ children }: { children: ReactNode }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const sourceRef = useRef("unknown");
  const titleId = useId();
  const [phase, setPhase] = useState<Phase>("form");
  const [errors, setErrors] = useState<Errors>({});

  const open = useCallback((source: string) => {
    sourceRef.current = source;
    track("lead_open", { source });
    dialogRef.current?.showModal();
  }, []);

  const value = useMemo(() => ({ open }), [open]);

  const close = () => dialogRef.current?.close();

  const reset = () => {
    formRef.current?.reset();
    setPhase("form");
    setErrors({});
  };

  // A click on the backdrop lands on the dialog element itself.
  const onBackdropClick = (event: MouseEvent<HTMLDialogElement>) => {
    if (event.target === event.currentTarget) close();
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const values = {
      name: String(data.get("name") ?? "").trim(),
      email: String(data.get("email") ?? "").trim(),
      agent: String(data.get("agent") ?? "").trim(),
      stack: String(data.get("stack") ?? ""),
    };

    const found: Errors = {};
    if (!values.name) found.name = lead.errors.name;
    if (!EMAIL.test(values.email)) found.email = lead.errors.email;
    if (!values.agent) found.agent = lead.errors.agent;
    setErrors(found);
    const firstInvalid = (["name", "email", "agent"] as const).find((field) => found[field]);
    if (firstInvalid) {
      form.querySelector<HTMLElement>(`[name="${firstInvalid}"]`)?.focus();
      return;
    }

    if (leadEndpoint) {
      setPhase("sending");
      try {
        const response = await fetch(leadEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...values, source: sourceRef.current }),
        });
        if (!response.ok) throw new Error(String(response.status));
        track("lead_submit", { source: sourceRef.current, route: "endpoint" });
        setPhase("sent");
      } catch {
        setPhase("form");
        setErrors({ send: lead.errors.send });
      }
      return;
    }

    if (contactEmail) {
      const body = [
        `${lead.fields.name.label}: ${values.name}`,
        `${lead.fields.email.label}: ${values.email}`,
        `${lead.fields.stack.label} ${values.stack}`,
        "",
        values.agent,
      ].join("\n");
      window.location.href = `mailto:${contactEmail}?subject=${encodeURIComponent(lead.mailSubject)}&body=${encodeURIComponent(body)}`;
      track("lead_submit", { source: sourceRef.current, route: "mailto" });
      setPhase("mailto");
    }
  };

  const configured = Boolean(leadEndpoint || contactEmail);
  const describedBy = (field: Field) => (errors[field] ? `${titleId}-${field}-error` : undefined);

  return (
    <LeadContext value={value}>
      {children}
      <dialog
        ref={dialogRef}
        className={styles.dialog}
        aria-labelledby={titleId}
        onClose={reset}
        onClick={onBackdropClick}
      >
        <div className={styles.panel}>
          <div className={styles.head}>
            <h2 id={titleId} className={styles.title}>
              {lead.title}
            </h2>
            <button type="button" className={styles.close} aria-label={lead.close} onClick={close}>
              <X aria-hidden size={18} />
            </button>
          </div>

          {!configured ? (
            <div className={styles.message}>
              <p>{lead.unconfigured.text}</p>
              <Button tone="onLight" size="block" href={lead.unconfigured.action.href}>
                {lead.unconfigured.action.label}
              </Button>
            </div>
          ) : phase === "sent" || phase === "mailto" ? (
            <div className={styles.message} role="status">
              <p className={styles.successTitle}>{lead.success.title}</p>
              <p>{phase === "sent" ? lead.success.sent : lead.success.mailto}</p>
              <Button tone="onLight" variant="ghost" size="block" onClick={close}>
                {lead.close}
              </Button>
            </div>
          ) : (
            <form ref={formRef} className={styles.form} noValidate onSubmit={onSubmit}>
              <p className={styles.intro}>{lead.intro}</p>

              <label className={styles.field}>
                <span className={styles.label}>{lead.fields.name.label}</span>
                <input
                  className={styles.input}
                  name="name"
                  type="text"
                  autoComplete="name"
                  placeholder={lead.fields.name.placeholder}
                  aria-invalid={Boolean(errors.name)}
                  aria-describedby={describedBy("name")}
                />
                {errors.name && (
                  <span id={`${titleId}-name-error`} className={styles.error}>
                    {errors.name}
                  </span>
                )}
              </label>

              <label className={styles.field}>
                <span className={styles.label}>{lead.fields.email.label}</span>
                <input
                  className={styles.input}
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder={lead.fields.email.placeholder}
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={describedBy("email")}
                />
                {errors.email && (
                  <span id={`${titleId}-email-error`} className={styles.error}>
                    {errors.email}
                  </span>
                )}
              </label>

              <label className={styles.field}>
                <span className={styles.label}>{lead.fields.agent.label}</span>
                <textarea
                  className={styles.input}
                  name="agent"
                  rows={3}
                  placeholder={lead.fields.agent.placeholder}
                  aria-invalid={Boolean(errors.agent)}
                  aria-describedby={describedBy("agent")}
                />
                {errors.agent && (
                  <span id={`${titleId}-agent-error`} className={styles.error}>
                    {errors.agent}
                  </span>
                )}
              </label>

              <fieldset className={styles.fieldset}>
                <legend className={styles.label}>{lead.fields.stack.label}</legend>
                <div className={styles.options}>
                  {lead.fields.stack.options.map((option, index) => (
                    <label key={option} className={styles.option}>
                      <input type="radio" name="stack" value={option} defaultChecked={index === 0} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {errors.send && (
                <p className={styles.error} role="alert">
                  {errors.send}
                </p>
              )}

              <Button tone="onLight" size="block" type="submit" disabled={phase === "sending"}>
                {phase === "sending" ? lead.sending : lead.submit}
              </Button>
            </form>
          )}
        </div>
      </dialog>
    </LeadContext>
  );
}

type TriggerProps = Omit<Extract<ButtonProps, { href?: undefined }>, "onClick"> & {
  /** Names this button in analytics, for example "nav" or "pricing". */
  source: string;
  /** Runs before the dialog opens, for example to close a menu. */
  onBeforeOpen?: () => void;
};

/** A button that opens the "Talk to us" dialog. */
export function LeadTrigger({ source, onBeforeOpen, children, ...button }: TriggerProps) {
  const open = useLeadDialog();
  return (
    <Button
      {...button}
      onClick={() => {
        onBeforeOpen?.();
        open(source);
      }}
    >
      {children}
    </Button>
  );
}
