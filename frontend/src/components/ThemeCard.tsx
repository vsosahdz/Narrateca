import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import type { Theme } from "@/lib/api";

import styles from "./ThemeCard.module.css";

/**
 * Tarjeta de una comunidad en la página de inicio.
 *
 * El `data-theme` aplica el acento propio del tema desde la capa de tokens. El
 * valor viene del campo `accent_token` del backend, que guarda el *nombre* del
 * token y nunca un color: así, sustituir la paleta sigue siendo editar dos
 * archivos de CSS y no una migración de datos.
 *
 * Toda la tarjeta es un solo enlace, no un `div` con un enlace adentro: eso da
 * un único objetivo de foco y un área táctil amplia, en vez de obligar a apuntar
 * a un texto pequeño.
 */
export async function ThemeCard({ theme, locale }: { theme: Theme; locale: string }) {
  const t = await getTranslations("home");

  const name = locale === "en" ? theme.name_en : theme.name_es;
  const description = locale === "en" ? theme.description_en : theme.description_es;

  return (
    <Link
      href={`/${theme.slug}`}
      className={styles.card}
      data-theme={theme.accent_token}
      aria-label={t("exploreTheme", { theme: name })}
    >
      <span className={styles.accent} aria-hidden="true" />
      <h3 className={styles.name}>{name}</h3>
      {description && <p className={styles.description}>{description}</p>}
    </Link>
  );
}
