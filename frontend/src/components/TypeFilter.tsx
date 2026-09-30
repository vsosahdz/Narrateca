import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import type { ContentType } from "@/lib/api";

import styles from "./TypeFilter.module.css";

/**
 * Filtro por tipo de contenido dentro de una comunidad.
 *
 * Se implementa con enlaces reales y no con botones que manipulen el estado en
 * el cliente. Así cada filtro es una dirección propia: se puede compartir,
 * marcar como favorita, abrir en otra pestaña y recorrer con el historial del
 * navegador. Un filtro que solo vive en memoria pierde todo eso.
 */
export async function TypeFilter({
  themeSlug,
  available,
  active,
}: {
  themeSlug: string;
  available: ContentType[];
  active?: string;
}) {
  const t = await getTranslations();

  return (
    <nav className={styles.filter} aria-label={t("content.filterLabel")}>
      <ul className={styles.list}>
        <li>
          <Link
            href={`/${themeSlug}`}
            className={styles.item}
            aria-current={!active ? "true" : undefined}
          >
            {t("content.filterAll")}
          </Link>
        </li>
        {available.map((type) => (
          <li key={type}>
            <Link
              href={`/${themeSlug}?tipo=${type}`}
              className={styles.item}
              aria-current={active === type ? "true" : undefined}
            >
              {t(`sections.${type}`)}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
