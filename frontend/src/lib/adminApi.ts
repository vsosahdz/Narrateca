/**
 * Cliente de administración, para uso desde el navegador.
 *
 * Se separa de `api.ts` porque las condiciones son distintas: aquí las
 * peticiones salen del navegador y deben llevar la cookie de sesión, mientras
 * que el sitio público se renderiza en el servidor y no necesita credenciales.
 *
 * `credentials: "include"` es lo que hace que la cookie viaje. La cookie es
 * `httponly`, así que este código nunca la ve ni puede leerla: solo pide al
 * navegador que la adjunte.
 */

import type { ContentItem, ContentType, Sensitivity, Theme } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Role = "admin" | "editor";
export type ConsentScope = "public" | "site_only" | "no_ai";
export type PublicationStatus = "draft" | "published" | "withdrawn";

export interface Account {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  themes: Array<{ id: string; slug: string; name_es: string }>;
}

export interface AdminContentItem extends ContentItem {
  status: PublicationStatus;
  consent_scope: ConsentScope;
  person_name: string | null;
  pseudonym: string | null;
  /** Si la pieza alimenta el corpus del chatbot en este momento. */
  is_indexable: boolean;
  source_ref: string | null;
  imported_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubtitleTrack {
  locale: "es" | "en";
  key: string;
  exists: boolean;
}

export interface UploadResult {
  media_key: string;
  media_mime: string;
  scope: "public" | "sensitive";
}

export interface ThemeCoverage {
  theme_slug: string;
  theme_name: string;
  total: number;
  draft: number;
  published: number;
  withdrawn: number;
  /** Publicadas Y con consentimiento para uso con IA. Techo del corpus. */
  indexable: number;
  excluded_no_ai: number;
  excluded_site_only: number;
  /** Piezas visuales bloqueadas por falta de texto alternativo. */
  blocked_missing_alt_text: number;
}

export interface ArchiveHealth {
  by_status: Record<string, number>;
  needs_attention: number;
  pending_import: number;
  failed: number;
  last_scan_at: string | null;
}

export interface DashboardAlert {
  level: "info" | "warning" | "blocking";
  message: string;
  count: number;
}

export interface PendingSection {
  key: string;
  label: string;
  reason: string;
}

export interface Dashboard {
  generated_at: string;
  themes: ThemeCoverage[];
  types: Array<{ type: string; count: number }>;
  total_items: number;
  total_published: number;
  total_indexable: number;
  archive: ArchiveHealth;
  recent_activity: Array<{
    account_email: string;
    action: string;
    entity_type: string;
    created_at: string;
  }>;
  alerts: DashboardAlert[];
  /** Secciones cuyos datos aún no existen. Se declaran en vez de mostrar cero. */
  pending_sections: PendingSection[];
}

export interface ScanReport {
  root: string;
  scanned: number;
  new: string[];
  modified: string[];
  missing: string[];
  unchanged: number;
  unknown_theme: string[];
  unclassified: string[];
  hashed: number;
  needs_attention: number;
}

export class AdminApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AdminApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  params?: Record<string, string | undefined>,
): Promise<T> {
  const url = new URL(`/api/v1${path}`, API_BASE);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) url.searchParams.set(key, value);
  }

  const response = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    // El backend responde con `detail`, que puede ser texto o la lista de
    // errores de validación de Pydantic. Se normaliza a algo legible para que
    // el formulario pueda mostrarlo tal cual.
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((e: { loc?: string[]; msg: string }) => `${e.loc?.at(-1) ?? ""}: ${e.msg}`).join(" · ")
          : `La operación falló (${response.status}).`;
    throw new AdminApiError(message, response.status);
  }

  return payload as T;
}

export const adminApi = {
  // --- Sesión ---------------------------------------------------------------
  login: (email: string, password: string) =>
    request<Account>("/admin/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request<void>("/admin/logout", { method: "POST" }),

  me: () => request<Account>("/admin/me"),

  // --- Contenido ------------------------------------------------------------
  listContent: (params: { theme?: string; type?: ContentType; limit?: number }) =>
    request<AdminContentItem[]>("/admin/content", {}, {
      theme: params.theme,
      type: params.type,
      limit: String(params.limit ?? 200),
    }),

  getContent: (id: string) => request<AdminContentItem>(`/admin/content/${id}`),

  createContent: (payload: Record<string, unknown>) =>
    request<AdminContentItem>("/admin/content", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateContent: (id: string, payload: Record<string, unknown>) =>
    request<AdminContentItem>(`/admin/content/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  publish: (id: string) =>
    request<AdminContentItem>(`/admin/content/${id}/publish`, { method: "POST" }),

  withdraw: (id: string) =>
    request<AdminContentItem>(`/admin/content/${id}/withdraw`, { method: "POST" }),

  setConsent: (id: string, scope: ConsentScope) =>
    request<AdminContentItem>(`/admin/content/${id}/consent`, { method: "PUT" }, { scope }),

  deleteContent: (id: string) =>
    request<void>(`/admin/content/${id}`, { method: "DELETE" }),

  // --- Media ----------------------------------------------------------------
  uploadMedia: (file: File, themeSlug: string, sensitivity: Sensitivity) => {
    const body = new FormData();
    body.append("file", file);
    body.append("theme_slug", themeSlug);
    body.append("sensitivity", sensitivity);
    return request<UploadResult>("/admin/media", { method: "POST", body });
  },

  subtitleStatus: (itemId: string) =>
    request<SubtitleTrack[]>(`/admin/media/subtitles/${itemId}`),

  readSubtitle: (itemId: string, locale: "es" | "en") =>
    request<{ content: string }>(`/admin/media/subtitles/${itemId}/${locale}`),

  writeSubtitle: (itemId: string, locale: "es" | "en", content: string) =>
    request<void>(`/admin/media/subtitles/${itemId}/${locale}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),

  // --- Panel de control -----------------------------------------------------
  dashboard: () => request<Dashboard>("/admin/dashboard"),

  scanArchive: () =>
    request<ScanReport>("/admin/archive/scan", { method: "POST" }),

  // --- Temas ----------------------------------------------------------------
  themes: () => request<Theme[]>("/themes"),
};

/** Tipos de contenido que el panel permite crear. */
export const CREATABLE_TYPES: ContentType[] = [
  "testimony",
  "interview",
  "video",
  "photo",
  "news_post",
  "curated_link",
  "geo_item",
];

export const CONSENT_SCOPES: ConsentScope[] = ["no_ai", "site_only", "public"];
