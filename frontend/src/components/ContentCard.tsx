import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import type { ContentItem } from "@/lib/api";
import { mediaUrl } from "@/lib/media";

import styles from "./ContentCard.module.css";

/**
 * Tarjeta de una pieza en el listado de una comunidad.
 *
 * La atribución se muestra tal como la definió el consentimiento: el nombre
 * cuando lo hay, el seudónimo cuando corresponde, y una etiqueta neutra cuando
 * es anónima. El nombre real de una pieza anónima nunca llega hasta aquí porque
 * el esquema público del backend no lo incluye.
 */
export async function ContentCard({ item }: { item: ContentItem }) {
  const t = await getTranslations("content");

  const isImage = item.media_key !== null && item.media_mime?.startsWith("image/");

  return (
    <article className={styles.card}>
      {isImage && item.media_key && (
        // Imagen sin optimizar por ahora: el host del almacenamiento se define
        // al montar la infraestructura, y `next/image` requiere declararlo en
        // `remotePatterns`. El texto alternativo es obligatorio de todas formas.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className={styles.image}
          src={mediaUrl(item.media_key)}
          alt={item.alt_text ?? ""}
          loading="lazy"
        />
      )}

      <div className={styles.body}>
        <h3 className={styles.title}>
          <Link href={`/${item.theme_slug}/${item.slug}`} className={styles.link}>
            {item.title}
          </Link>
        </h3>

        {item.summary && <p className={styles.summary}>{item.summary}</p>}

        <p className={styles.attribution}>
          {item.display_name ?? t("anonymous")}
        </p>
      </div>
    </article>
  );
}
