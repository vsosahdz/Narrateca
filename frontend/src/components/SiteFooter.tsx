import { getTranslations } from "next-intl/server";

import styles from "./SiteFooter.module.css";

/**
 * Pie del sitio.
 *
 * Igual que el encabezado, no contiene ningún elemento de donación. El aviso
 * sobre el consentimiento del archivo es deliberado: la procedencia del material
 * es parte de lo que la plataforma comunica, no letra chica.
 */
export async function SiteFooter() {
  const t = await getTranslations("footer");
  const site = await getTranslations("site");
  const year = new Date().getFullYear();

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <p className={styles.notice}>{t("archiveNotice")}</p>
        <p className={styles.credit}>
          {site("name")} · {t("rights")} · {year}
        </p>
      </div>
    </footer>
  );
}
