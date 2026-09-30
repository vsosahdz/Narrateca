import { defineRouting } from "next-intl/routing";

/**
 * Configuración de idiomas.
 *
 * El español es el idioma principal de NarraTECa; el inglés es secundario.
 * Ambos tienen prefijo de ruta propio (`/es/...`, `/en/...`) para que cualquier
 * página en un idioma determinado sea enlazable directamente, requisito de la
 * spec `i18n-subtitles`.
 *
 * Se usa `localePrefix: "always"` a propósito: sin prefijo en el idioma por
 * defecto, la misma dirección devolvería contenido distinto según la
 * negociación del navegador, y un enlace compartido dejaría de ser estable.
 */
export const routing = defineRouting({
  locales: ["es", "en"],
  defaultLocale: "es",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];

/** Etiquetas de idioma en su propio idioma, como recomienda WCAG. */
export const localeLabels: Record<Locale, string> = {
  es: "Español",
  en: "English",
};
