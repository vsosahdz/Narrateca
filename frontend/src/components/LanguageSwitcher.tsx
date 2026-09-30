"use client";

import { useLocale, useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";
import { localeLabels, routing, type Locale } from "@/i18n/routing";

import styles from "./LanguageSwitcher.module.css";

/**
 * Cambio de idioma que conserva la página actual.
 *
 * Usa `usePathname` de `@/i18n/navigation`, que devuelve la ruta *sin* el
 * prefijo de idioma. Eso es lo que permite volver a enlazar a la misma página en
 * el otro idioma en lugar de devolver al inicio, requisito de la spec
 * `i18n-subtitles`.
 *
 * Se implementa con enlaces reales y no con un `<select>` para que cada idioma
 * sea una dirección navegable, compartible e indexable.
 */
export function LanguageSwitcher() {
  const pathname = usePathname();
  const active = useLocale() as Locale;
  const t = useTranslations("language");

  return (
    <nav className={styles.switcher} aria-label={t("label")}>
      <ul className={styles.list}>
        {routing.locales.map((locale) => {
          const isActive = locale === active;
          return (
            <li key={locale}>
              <Link
                href={pathname}
                locale={locale}
                lang={locale}
                hrefLang={locale}
                className={styles.item}
                aria-current={isActive ? "true" : undefined}
                aria-label={
                  isActive
                    ? t("current", { language: localeLabels[locale] })
                    : t("switchTo", { language: localeLabels[locale] })
                }
              >
                {localeLabels[locale]}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
