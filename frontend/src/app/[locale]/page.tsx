import { getTranslations, setRequestLocale } from "next-intl/server";

import { ThemeCard } from "@/components/ThemeCard";
import { api } from "@/lib/api";

import styles from "./page.module.css";

/**
 * Página de inicio: las cuatro comunidades.
 *
 * No contiene ningún elemento de donación, aporte económico ni pasarela de pago.
 * Es un requisito explícito de la spec `public-site`, verificado además por una
 * prueba automatizada.
 */
export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const [t, themes] = await Promise.all([getTranslations(), api.themes()]);

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>{t("site.name")}</h1>
        <p className={styles.lead}>{t("home.intro")}</p>
      </section>

      <section aria-labelledby="comunidades">
        {/* El encabezado existe para la estructura del documento y para los
            lectores de pantalla, aunque las tarjetas ya sean autoexplicativas
            visualmente. */}
        <h2 id="comunidades" className="visually-hidden">
          {t("home.themesHeading")}
        </h2>

        <ul className={styles.themeGrid}>
          {themes.map((theme) => (
            <li key={theme.slug}>
              <ThemeCard theme={theme} locale={locale} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
