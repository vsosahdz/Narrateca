import { getTranslations } from "next-intl/server";

import type { ContentItem } from "@/lib/api";
import { mediaUrl, requiresOwnPlayer, subtitleUrl, youTubeId } from "@/lib/media";

import styles from "./MediaPlayer.module.css";

/**
 * Reproductor de audio y video.
 *
 * Dos reglas de la spec `public-site` viven aquí:
 *
 * 1. **El material de sensibilidad alta se sirve desde almacenamiento propio**,
 *    con reproductor propio y sin incrustar ningún servicio de terceros.
 * 2. **Todo el material lleva subtítulos en español e inglés.** Los de español
 *    cumplen función de accesibilidad; los de inglés, de traducción. Ambos salen
 *    del mismo trabajo de transcripción que alimenta el chatbot.
 */
export async function MediaPlayer({ item }: { item: ContentItem }) {
  const t = await getTranslations("media");

  const ownPlayer = requiresOwnPlayer(item) || item.external_url === null;

  if (ownPlayer) {
    if (!item.media_key) return null;

    return (
      <figure className={styles.figure}>
        {/* `controls` da al navegador su reproductor nativo, que ya es accesible
            por teclado y compatible con lectores de pantalla. Reimplementarlo a
            mano casi siempre produce algo menos accesible. */}
        <video className={styles.video} controls preload="metadata" playsInline>
          <source src={mediaUrl(item.media_key)} type={item.media_mime ?? "video/mp4"} />

          <track
            kind="subtitles"
            src={subtitleUrl(item.media_key, "es")}
            srcLang="es"
            label={t("subtitlesEs")}
            default
          />
          <track
            kind="subtitles"
            src={subtitleUrl(item.media_key, "en")}
            srcLang="en"
            label={t("subtitlesEn")}
          />

          {t("noVideoSupport")}
        </video>
      </figure>
    );
  }

  // Material de difusión general en un servicio externo.
  const videoId = item.external_url ? youTubeId(item.external_url) : null;
  if (!videoId) return null;

  return (
    <figure className={styles.figure}>
      <div className={styles.embed}>
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}`}
          title={item.title}
          allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture"
          allowFullScreen
          loading="lazy"
        />
      </div>
      {/* Se le dice a la persona que va a cargar contenido de un tercero, en
          lugar de que ocurra en silencio. */}
      <figcaption className={styles.notice}>{t("externalNotice")}</figcaption>
    </figure>
  );
}
