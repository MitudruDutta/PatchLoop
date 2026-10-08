import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import styles from "./not-found.module.css";

const copy = {
  code: "404",
  title: "This page does not exist.",
  text: "The address may be mistyped, or the page may have moved.",
  home: "Back to the home page",
};

export default function NotFound() {
  return (
    <main id="main-content" className={styles.page}>
      <Link className={styles.brand} href="/">
        <Logo />
      </Link>
      <p className="t-eyebrow">{copy.code}</p>
      <h1 className={styles.title}>{copy.title}</h1>
      <p className={styles.text}>{copy.text}</p>
      <Link className={styles.home} href="/">
        {copy.home}
      </Link>
    </main>
  );
}
