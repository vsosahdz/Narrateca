import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import type { NewsItem } from "@/lib/api";

import styles from "./NewsSection.module.css";

/**
 * Sección de noticias de una comunidad.
 *
 * Reúne notas del equipo y enlaces a medios externos en una sola lista ordenada
 * por fecha, con la distinción visible: quien lee debe poder saber si está ante
 * algo escrito por el equipo de investigación o ante el resumen de una nota
 * publicada por otro medio.
 *
 * Un enlace externo abre en pestaña nueva y lo anuncia en su nombre accesible,
 * para que la apertura no sea una sorpresa para quien navega con lector de
 * pantalla.
 */
export async function NewsSection({ items, locale }: { items: NewsItem[]; locale: string }) {
  const t = await getTranslations();
  if (items.length === 0) return null;

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(new Date(value));

  return (
    <section className={styles.section} aria-labelledby="seccion-noticias">
      <h2 id="seccion-noticias" className={styles.title}>
        {t("sections.news_post")}
      </h2>

      <ul className={styles.list}>
        {items.map((news) => (
          <li key={news.id} className={styles.item}>
            <p className={styles.meta}>
              <span
                className={styles.badge}
                data-kind={news.kind}
              >
                {news.kind === "curated"
                  ? (news.source_name ?? t("news.external"))
                  : t("news.own")}
              </span>
              {news.published_at && (
                <time dateTime={news.published_at}>{formatDate(news.published_at)}</time>
              )}
            </p>

            <h3 className={styles.itemTitle}>
              {news.kind === "curated" && news.external_url ? (
                <a
                  href={news.external_url}
                  className={styles.link}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {news.title}
                  <span className="visually-hidden"> {t("news.opensInNewTab")}</span>
                </a>
              ) : (
                <Link href={`/${news.theme_slug}/${news.slug}`} className={styles.link}>
                  {news.title}
                </Link>
              )}
            </h3>

            {news.summary && <p className={styles.summary}>{news.summary}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
