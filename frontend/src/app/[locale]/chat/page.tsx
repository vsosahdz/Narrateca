import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { ChatPage } from "@/components/chat/ChatPage";
import type { Persona } from "@/lib/chatApi";
import { envOr } from "@/lib/env";

import styles from "./page.module.css";

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "chat" });
  return { title: t("title"), description: t("intro") };
}

/**
 * Página del chatbot.
 *
 * El listado de narradoras se pide en el servidor para que el selector llegue
 * pintado en el primer HTML: la conversación necesita JavaScript, pero saber
 * qué comunidades hay y cuáles están abiertas, no.
 *
 * Si la API no responde, la página se muestra con el selector vacío en lugar
 * de romperse. Un fallo del backend del chatbot no debería tumbar una ruta del
 * sitio público.
 */
export default async function ChatRoute({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  const personas = await fetchPersonas();

  return (
    <div className={styles.page}>
      <ChatPage personas={personas} locale={locale} />
    </div>
  );
}

async function fetchPersonas(): Promise<Persona[]> {
  const base = envOr(process.env.API_BASE_URL, "http://localhost:8000");
  try {
    const response = await fetch(new URL("/api/v1/chat/personas", base), {
      // El estado de activación lo cambia el equipo desde el panel, no cada
      // visita. Revalidar permite servir esto casi siempre desde caché, que
      // importa porque Cloud Run corre sin instancias en reposo.
      next: { revalidate: 60 },
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return [];
    return (await response.json()) as Persona[];
  } catch {
    return [];
  }
}
