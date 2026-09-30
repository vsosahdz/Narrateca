import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Lang } from "@/components/Lang";
import { MediaPlayer } from "@/components/MediaPlayer";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { mediaUrl } from "@/lib/media";

import styles from "./page.module.css";

interface Props {
  params: Promise<{ locale: string; theme: string; slug: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { theme, slug } = await params;
  const item = await api.contentItem(theme, slug);
  if (!item) return {};

  return {
    title: item.title,
    description: item.summary ?? undefined,
    openGraph: {
      title: item.title,
      description: item.summary ?? undefined,
      type: "article",
    },
  };
}

/**
 * Detalle de una pieza, en su dirección propia y estable.
 *
 * Esa dirección es la que el chatbot enlaza al citar un fragmento: si dejara de
 * ser estable, las citas de las respuestas quedarían rotas.
 *
 * Una pieza retirada devuelve 404 y no expone su contenido; el backend ya no la
 * sirve por la vía pública, así que aquí simplemente no llega.
 */
export default async function ContentDetailPage({ params }: Props) {
  const { locale, theme: themeSlug, slug } = await params;
  setRequestLocale(locale);

  const [item, theme] = await Promise.all([
    api.contentItem(themeSlug, slug),
    api.theme(themeSlug),
  ]);

  if (!item || !theme) notFound();

  const t = await getTranslations();
  const themeName = locale === "en" ? theme.name_en : theme.name_es;
  const hasMedia = item.media_key !== null || item.external_url !== null;
  const isImage = item.media_mime?.startsWith("image/") ?? false;

  return (
    <article className={styles.page} data-theme={theme.accent_token}>
      <nav className={styles.breadcrumb}>
        <Link href={`/${themeSlug}`}>{t("content.backToTheme", { theme: themeName })}</Link>
      </nav>

      <header className={styles.header}>
        <p className={styles.kicker}>{t(`sections.${item.type}`)}</p>
        <h1 className={styles.title}>{item.title}</h1>

        <p className={styles.attribution}>
          {item.display_name ?? t("content.anonymous")}
          {item.recorded_on && (
            <>
              {" · "}
              <time dateTime={item.recorded_on}>
                {t("content.recordedOn", {
                  date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                    new Date(item.recorded_on),
                  ),
                })}
              </time>
            </>
          )}
        </p>
      </header>

      {isImage && item.media_key ? (
        <figure className={styles.figure}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={mediaUrl(item.media_key)} alt={item.alt_text ?? ""} className={styles.image} />
          {item.alt_text && <figcaption className={styles.caption}>{item.alt_text}</figcaption>}
        </figure>
      ) : (
        hasMedia && <MediaPlayer item={item} />
      )}

      {item.body && (
        // El contenido del archivo permanece en español aunque la interfaz esté
        // en inglés. Sin declarar el idioma, un lector de pantalla en inglés
        // pronunciaría el testimonio con fonética inglesa y lo volvería
        // incomprensible (WCAG 2.2 SC 3.1.2).
        <Lang locale="es" as="div" className={styles.body}>
          {item.body.split(/\n{2,}/).map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </Lang>
      )}

      {item.external_url && item.source_name && (
        <p className={styles.source}>
          {t("content.externalSource", { source: item.source_name })}{" "}
          <a href={item.external_url} rel="noopener noreferrer" target="_blank">
            {t("content.openExternal")}
          </a>
        </p>
      )}
    </article>
  );
}
