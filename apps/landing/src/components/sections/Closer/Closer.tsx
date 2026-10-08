import { LoopMark } from "@/components/art/LoopMark";
import { Container } from "@/components/layout/Container";
import { Brackets } from "@/components/ui/Brackets";
import { Logo } from "@/components/ui/Logo";
import { closer } from "@/content/closer";
import { isExternal } from "@/content/site";
import { CloserBand } from "./CloserBand";
import { CopyEmail } from "./CopyEmail";
import styles from "./Closer.module.css";

/** The closing band and the site footer. */
export function Closer() {
  const { blurb, contact, columns, footerLabel, foot } = closer;

  return (
    <footer className={styles.closer}>
      <CloserBand />

      <div className={styles.plinth}>
        <Container>
          <div className={styles.rule} />
          <div className={styles.columns}>
            <div className={styles.brand}>
              <div className={styles.brandRow}>
                <Logo />
                <LoopMark />
              </div>
              <p className={styles.blurb}>{blurb}</p>

              <div className={styles.contact}>
                <Brackets />
                <p className={styles.contactTitle}>{contact.title}</p>
                <p className={styles.contactBlurb}>{contact.blurb}</p>
                {contact.email ? (
                  <CopyEmail email={contact.email} />
                ) : (
                  <div className={styles.emailField}>
                    <a
                      className={styles.contactEmail}
                      href={contact.fallback.href}
                      data-track="outbound"
                      data-track-location="footer-contact"
                    >
                      {contact.fallback.label}
                      <span aria-hidden>↗</span>
                    </a>
                  </div>
                )}
              </div>
            </div>

            <nav className={styles.linkColumns} aria-label={footerLabel}>
              {columns.map((column) => (
                <div key={column.title}>
                  <h2 className={styles.columnTitle}>{column.title}</h2>
                  <ul className={styles.columnList}>
                    {column.links.map((link) => (
                      <li key={link.label}>
                        <a
                          className={styles.link}
                          href={link.href}
                          {...(isExternal(link.href)
                            ? { "data-track": "outbound", "data-track-location": "footer" }
                            : {})}
                        >
                          {link.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </div>

          <div className={styles.foot}>{foot}</div>
        </Container>
      </div>
    </footer>
  );
}
