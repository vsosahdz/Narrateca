import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

import { LanguageSwitcher } from "./LanguageSwitcher";
import styles from "./SiteHeader.module.css";

/**
 * Encabezado del sitio.
 *
 * No contiene ningún elemento de donación, aporte económico ni pasarela de pago,
 * en ninguna de sus variantes. Es un requisito explícito de la spec `public-site`.
 */
export async function SiteHeader() {
  const t = await getTranslations("nav");
  const site = await getTranslations("site");

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/" className={styles.brand}>
          <span className={styles.brandName}>{site("name")}</span>
          <span className={styles.brandTagline}>{site("tagline")}</span>
        </Link>

        <nav aria-label={t("mainLabel")} className={styles.nav}>
          <ul className={styles.navList}>
            <li>
              <Link href="/" className={styles.navLink}>
                {t("home")}
              </Link>
            </li>
            <li>
              <Link href="/chat" className={styles.navLink}>
                {t("chat")}
              </Link>
            </li>
            <li>
              <Link href="/equipo" className={styles.navLink}>
                {t("team")}
              </Link>
            </li>
          </ul>
        </nav>

        <LanguageSwitcher />
      </div>
    </header>
  );
}
