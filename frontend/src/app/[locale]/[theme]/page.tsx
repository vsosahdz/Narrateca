import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ContentCard } from "@/components/ContentCard";
import { NewsSection } from "@/components/NewsSection";
import { TypeFilter } from "@/components/TypeFilter";
import { api, groupByType, type ContentType } from "@/lib/api";

import styles from "./page.module.css";

interface Props {
  params: Promise<{ locale: string; theme: string }>;
  searchParams: Promise<{ tipo?: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, theme: slug } = await params;
  const theme = await api.theme(slug);
  if (!theme) return {};

  const name = locale === "en" ? theme.name_en : theme.name_es;
  const description = locale === "en" ? theme.description_en : theme.description_es;

  // Los metadatos por página son parte del producto: un testimonio que al
  // compartirse se ve como una tarjeta gris sin título está fallando en su
  // misión de divulgación, no en su stack.
  return {
    title: name,
    description: description ?? undefined,
    openGraph: { title: name, description: description ?? undefined, type: "website" },
  };
}

/**
 * Página independiente de una comunidad.
 *
 * Muestra únicamente contenido de este tema y en estado publicado: ambas
 * condiciones las impone el backend, que nunca sirve borradores ni piezas
 * retiradas por la vía pública.
 */
export default async function ThemePage({ params, searchParams }: Props) {
  const { locale, theme: slug } = await params;
  const { tipo } = await searchParams;
  setRequestLocale(locale);

  const theme = await api.theme(slug);
  if (!theme) notFound();

  const t = await getTranslations();
  const name = locale === "en" ? theme.name_en : theme.name_es;
  const description = locale === "en" ? theme.description_en : theme.description_es;

  const [items, news] = await Promise.all([
    api.content({ theme: slug, type: (tipo as ContentType) || undefined, limit: 200 }),
    // Las noticias tienen su propia sección y no se ven afectadas por el filtro
    // de tipo, que aplica al contenido del archivo.
    tipo ? Promise.resolve([]) : api.news({ theme: slug, limit: 50 }),
  ]);

  // Los tipos disponibles se calculan sobre el contenido sin filtrar, para que
  // el filtro no se quede sin opciones al aplicarlo.
  const all = tipo ? await api.content({ theme: slug, limit: 200 }) : items;
  const availableTypes = groupByType(all).map(([type]) => type);
  const sections = groupByType(items);

  return (
    <div className={styles.page} data-theme={theme.accent_token}>
      <header className={styles.header}>
        <span className={styles.accent} aria-hidden="true" />
        <h1 className={styles.title}>{name}</h1>
        {description && <p className={styles.description}>{description}</p>}
      </header>

      {availableTypes.length > 1 && (
        <TypeFilter themeSlug={slug} available={availableTypes} active={tipo} />
      )}

      {sections.length === 0 && news.length === 0 ? (
        <p className={styles.empty}>{t("content.emptyTheme")}</p>
      ) : (
        sections.map(([type, group]) => (
          <section key={type} className={styles.section} aria-labelledby={`seccion-${type}`}>
            <h2 id={`seccion-${type}`} className={styles.sectionTitle}>
              {t(`sections.${type}`)}
            </h2>
            <ul className={styles.grid}>
              {group.map((item) => (
                <li key={item.id}>
                  <ContentCard item={item} />
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      <NewsSection items={news} locale={locale} />
    </div>
  );
}
