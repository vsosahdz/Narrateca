/**
 * Direcciones del material multimedia.
 *
 * El material sensible se sirve desde almacenamiento propio; el de difusión
 * general puede venir de un servicio externo. La distinción la marca el campo
 * `sensitivity` de cada pieza y la resuelve `MediaPlayer`.
 */

import type { ContentItem } from "./api";

import { envOr } from "./env";

const MEDIA_BASE = envOr(process.env.NEXT_PUBLIC_MEDIA_BASE_URL, "/media");

export function mediaUrl(key: string): string {
  return `${MEDIA_BASE}/${key.replace(/^\/+/, "")}`;
}

/** Pista de subtítulos asociada a una pieza, por idioma.
 *
 * Convención: junto al archivo de media, con el idioma en el nombre.
 *   entrevistas/ent-014.mp4 → entrevistas/ent-014.es.vtt
 */
export function subtitleUrl(mediaKey: string, locale: "es" | "en"): string {
  const withoutExtension = mediaKey.replace(/\.[^./]+$/, "");
  return mediaUrl(`${withoutExtension}.${locale}.vtt`);
}

/** Si una pieza debe reproducirse desde almacenamiento propio.
 *
 * El material de sensibilidad alta nunca se incrusta desde un servicio de
 * terceros: un testimonio de una sobreviviente rodeado de publicidad y de un
 * carrusel de recomendaciones algorítmicas es un problema de dignidad, no solo
 * de control técnico (spec `public-site`).
 */
export function requiresOwnPlayer(item: ContentItem): boolean {
  return item.sensitivity === "high";
}

/** Extrae el identificador de un video de YouTube, si la dirección lo es. */
export function youTubeId(url: string): string | null {
  const match = url.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/,
  );
  return match ? match[1] : null;
}
