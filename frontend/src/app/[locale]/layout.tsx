import type { Metadata } from "next";
import { Inter, Noto_Serif } from "next/font/google";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { SkipLink } from "@/components/SkipLink";
import { routing } from "@/i18n/routing";

import "../globals.css";
import styles from "./layout.module.css";

/**
 * Tipografías del sistema de diseño, **autoalojadas**.
 *
 * `next/font/google` descarga los archivos durante el build y los sirve desde
 * el propio origen: el navegador de quien visita nunca contacta con Google. La
 * alternativa —un `<link>` al CDN— revelaría la dirección IP de cada visitante
 * a un tercero, inaceptable en un sitio sobre comunidades vulnerables.
 *
 * `display: "swap"` muestra el texto de inmediato con la fuente de respaldo y
 * lo cambia al cargar la definitiva, en vez de dejar la página en blanco.
 */
const notoSerif = Noto_Serif({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "600", "700"],
  variable: "--font-noto-serif",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

/**
 * No se prerrenderizan las rutas en el build, a propósito.
 *
 * Las páginas públicas obtienen su contenido de la API, así que prerrenderizar
 * obligaría a tener la API en pie para **construir la imagen**. Eso impide
 * reconstruir durante una caída, impide verificar el contenedor en integración
 * continua, y ata el artefacto a los datos que había en un momento dado.
 *
 * En su lugar, cada ruta se renderiza en la primera petición y se guarda en
 * caché según el `revalidate` de cada consulta. El HTML que recibe un buscador
 * sigue siendo completo, que es lo que importaba para la difusión.
 */
export const dynamicParams = true;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "site" });

  return {
    title: { default: t("name"), template: `%s · ${t("name")}` },
    description: t("description"),
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  // Permite el renderizado estático de las rutas por idioma.
  setRequestLocale(locale);

  return (
    // El atributo `lang` es un requisito de accesibilidad: sin él, un lector de
    // pantalla pronuncia el contenido con las reglas del idioma equivocado.
    <html lang={locale} className={`${inter.variable} ${notoSerif.variable}`}>
      <body>
        <NextIntlClientProvider>
          <SkipLink />
          <SiteHeader />
          <main id="contenido" className={styles.main} tabIndex={-1}>
            {children}
          </main>
          <SiteFooter />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
