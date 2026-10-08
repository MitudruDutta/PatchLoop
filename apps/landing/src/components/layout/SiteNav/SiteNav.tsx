import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { LeadTrigger } from "@/components/ui/LeadDialog";
import { Logo } from "@/components/ui/Logo";
import { nav } from "@/content/site";
import { cn } from "@/lib/cn";
import { Container } from "../Container";
import { NavDropdown } from "../NavDropdown";
import { NavMenu } from "../NavMenu";
import styles from "./SiteNav.module.css";

/** The primary navigation. It sits over the hero and scrolls away with it. */
export function SiteNav() {
  return (
    <nav className={styles.nav} aria-label={nav.primaryLabel}>
      <Container className={styles.row}>
        <Link className={styles.brand} href="/" aria-label={nav.homeLabel}>
          <Logo />
        </Link>

        <div className={styles.links}>
          {nav.links.map((link) => (
            <a key={link.href} className={styles.link} href={link.href}>
              {link.label}
            </a>
          ))}
          <NavDropdown label={nav.resources.label} items={nav.resources.items} />
        </div>

        <div className={styles.actions}>
          <a
            className={cn(styles.link, styles.github)}
            href={nav.github.href}
            data-track="outbound"
            data-track-location="nav"
          >
            {nav.github.label}
          </a>
          <LeadTrigger variant="ghost" size="sm" source="nav" className={styles.talk}>
            {nav.talk}
          </LeadTrigger>
          <Button
            size="sm"
            href={nav.start.href}
            className={styles.start}
            data-track="cta_click"
            data-track-location="nav"
          >
            {nav.start.label}
          </Button>
          <NavMenu />
        </div>
      </Container>
    </nav>
  );
}
