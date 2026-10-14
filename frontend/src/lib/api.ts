/**
 * Cliente de la API de NarraTECa.
 *
 * Next.js aquí es solo capa de renderizado: no expone API propia y todo dato
 * viene de este cliente contra el backend FastAPI (ver `check:no-api-routes`).
 *
 * Los tipos reflejan los esquemas Pydantic del backend. Nótese que
 * `ContentItem` **no tiene** `person_name`: el esquema público del backend
 * tampoco lo tiene, así que el nombre real de una persona testimoniante no
 * existe de este lado de la frontera.
 */

import { envOr } from "./env";

const API_BASE = envOr(process.env.API_BASE_URL, "http://localhost:8000");

/** Segundos antes de volver a pedir el contenido al backend.
 *
 * El contenido cambia cuando el equipo publica desde el panel, no a cada
 * petición. Revalidar permite servir HTML estático casi siempre —lo que importa
 * porque Cloud Run corre con `min_instances = 0`— sin que una publicación tarde
 * horas en aparecer.
 */
const REVALIDATE_SECONDS = 60;

export type ContentType =
  | "photo"
  | "testimony"
  | "video"
  | "interview"
  | "news_post"
  | "curated_link"
  | "geo_item";

export type Attribution = "named" | "pseudonym" | "anonymous";
export type Sensitivity = "normal" | "high";

export interface Theme {
  id: string;
  slug: string;
  name_es: string;
  name_en: string;
  description_es: string | null;
  description_en: string | null;
  accent_token: string;
  position: number;
  is_active: boolean;
}

export interface ContentItem {
  id: string;
  theme_slug: string;
  type: ContentType;
  slug: string;
  title: string;
  summary: string | null;
  body: string | null;
  /** Nombre a mostrar según la atribución. Nulo si la pieza es anónima. */
  display_name: string | null;
  attribution: Attribution;
  sensitivity: Sensitivity;
  media_key: string | null;
  media_mime: string | null;
  external_url: string | null;
  source_name: string | null;
  alt_text: string | null;
  recorded_on: string | null;
  published_at: string | null;
}

export type NewsKind = "own" | "curated";

export interface NewsItem {
  id: string;
  theme_slug: string;
  /** Distingue una nota del equipo de un enlace a un medio externo. */
  kind: NewsKind;
  slug: string;
  title: string;
  summary: string | null;
  source_name: string | null;
  external_url: string | null;
  media_key: string | null;
  alt_text: string | null;
  published_at: string | null;
}

export interface TeamMember {
  id: string;
  full_name: string;
  role_title: string | null;
  bio: string;
  photo_key: string | null;
  photo_alt: string | null;
  position: number;
  is_active: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(
  path: string,
  params?: Record<string, string | undefined>,
): Promise<T> {
  const url = new URL(`/api/v1${path}`, API_BASE);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined) url.searchParams.set(key, value);
  }

  const response = await fetch(url, {
    next: { revalidate: REVALIDATE_SECONDS },
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(
      `GET ${url.pathname} devolvió ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

/** Devuelve `null` en lugar de lanzar cuando el recurso no existe.
 *
 * Una pieza retirada o inexistente no es un error del sistema: es un 404 de la
 * página, que Next.js sabe representar.
 */
async function getOrNull<T>(path: string): Promise<T | null> {
  try {
    return await get<T>(path);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export const api = {
  themes: () => get<Theme[]>("/themes"),

  theme: (slug: string) => getOrNull<Theme>(`/themes/${slug}`),

  content: (params: { theme?: string; type?: ContentType; limit?: number }) =>
    get<ContentItem[]>("/content", {
      theme: params.theme,
      type: params.type,
      limit: params.limit?.toString(),
    }),

  contentItem: (themeSlug: string, slug: string) =>
    getOrNull<ContentItem>(`/content/${themeSlug}/${slug}`),

  news: (params: { theme?: string; limit?: number }) =>
    get<NewsItem[]>("/news", {
      theme: params.theme,
      limit: params.limit?.toString(),
    }),

  team: () => get<TeamMember[]>("/team"),
};

/** Orden en que se presentan las secciones de una página temática.
 *
 * `news_post` y `curated_link` quedan fuera a propósito: la sección de noticias
 * los reúne en un solo bloque ordenado por fecha, en vez de partirlos en dos
 * listas separadas que la persona tendría que reconciliar mentalmente.
 */
export const SECTION_ORDER: ContentType[] = [
  "testimony",
  "interview",
  "video",
  "photo",
  "geo_item",
];

/** Agrupa piezas por tipo, conservando el orden de `SECTION_ORDER`.
 *
 * Los tipos sin piezas quedan fuera del resultado: una sección vacía no debe
 * mostrarse (spec `public-site`).
 */
export function groupByType(
  items: ContentItem[],
): Array<[ContentType, ContentItem[]]> {
  const groups = new Map<ContentType, ContentItem[]>();
  for (const item of items) {
    const bucket = groups.get(item.type);
    if (bucket) bucket.push(item);
    else groups.set(item.type, [item]);
  }

  return SECTION_ORDER.filter((type) => groups.has(type)).map((type) => [
    type,
    groups.get(type)!,
  ]);
}
