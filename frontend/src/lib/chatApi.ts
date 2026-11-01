/**
 * Cliente del chatbot, para uso desde el navegador.
 *
 * Se separa de `api.ts` porque la conversación no se renderiza en el servidor:
 * ocurre mientras la persona escribe, y la respuesta llega por partes.
 *
 * El consumo del flujo se hace con `fetch` y un lector de cuerpo en lugar de
 * `EventSource`, porque `EventSource` solo sabe hacer GET y aquí el mensaje
 * viaja en el cuerpo de un POST. El formato de eventos sí es el mismo.
 */

import { envOr } from "./env";

const API_BASE = envOr(
  process.env.NEXT_PUBLIC_API_BASE_URL,
  "http://localhost:8000",
);

export type Activation = "draft" | "coming_soon" | "active";
export type VoicePolicy = "female_only" | "any";

export interface Persona {
  theme_slug: string;
  activation: Activation;
  voice_policy: VoicePolicy;
  base_language: string;
  name_es: string;
  name_en: string;
  suggested_questions: string[];
}

export interface Citation {
  marker: number;
  text: string;
  item_title: string;
  item_slug: string;
  theme_slug: string;
  url: string;
  translation: string | null;
  cited: boolean;
}

export interface Orientation {
  theme_slug: string;
  theme_name_es: string;
  theme_name_en: string;
  matches: number;
  best_item_title: string | null;
  available: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(new URL(`/api/v1${path}`, API_BASE), {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const cuerpo = await response.json().catch(() => ({}));
    throw new ChatError(
      (cuerpo as { detail?: string }).detail ?? `Error ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

export class ChatError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ChatError";
  }
}

export function listPersonas(): Promise<Persona[]> {
  return request<Persona[]>("/chat/personas");
}

/** Pregunta a la recepción qué comunidades tienen material.
 *
 * La recepción no redacta: devuelve comunidades. Por eso aquí no hay ningún
 * campo de texto que mostrar, solo una lista hacia la que encaminar.
 */
export function orient(question: string): Promise<{ communities: Orientation[] }> {
  return request("/chat/orientacion", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export interface StreamHandlers {
  onMeta?: (meta: {
    conversation_id: string;
    language: string;
    contained: boolean;
    no_material_reason: string | null;
  }) => void;
  onDelta?: (texto: string) => void;
  onCitations?: (citas: Citation[]) => void;
  onError?: (detalle: string) => void;
}

/** Conversa con una comunidad, recibiendo la respuesta por partes.
 *
 * Devuelve cuando el flujo termina. Los eventos van llegando a los callbacks
 * conforme el servidor los emite.
 */
export async function streamChat(
  themeSlug: string,
  body: { message: string; conversation_id?: string; language?: "es" | "en" },
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    new URL(`/api/v1/chat/${themeSlug}/stream`, API_BASE),
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    },
  );

  if (!response.ok) {
    const cuerpo = await response.json().catch(() => ({}));
    throw new ChatError(
      (cuerpo as { detail?: string }).detail ?? `Error ${response.status}`,
      response.status,
    );
  }

  if (!response.body) throw new ChatError("Respuesta sin cuerpo", 500);

  const lector = response.body.getReader();
  const decodificador = new TextDecoder();
  let pendiente = "";

  // Un evento termina en línea en blanco. El troceado de la red no respeta esa
  // frontera, así que se acumula hasta tenerla completa.
  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;

    pendiente += decodificador.decode(value, { stream: true });

    let corte = pendiente.indexOf("\n\n");
    while (corte !== -1) {
      despachar(pendiente.slice(0, corte), handlers);
      pendiente = pendiente.slice(corte + 2);
      corte = pendiente.indexOf("\n\n");
    }
  }
}

function despachar(bloque: string, handlers: StreamHandlers): void {
  let evento = "";
  let datos = "";

  for (const linea of bloque.split("\n")) {
    if (linea.startsWith("event:")) evento = linea.slice(6).trim();
    else if (linea.startsWith("data:")) datos += linea.slice(5).trim();
  }

  if (!evento || !datos) return;

  let dato: unknown;
  try {
    dato = JSON.parse(datos);
  } catch {
    // Un evento ilegible no debe tumbar la conversación entera.
    return;
  }

  switch (evento) {
    case "meta":
      handlers.onMeta?.(dato as Parameters<NonNullable<StreamHandlers["onMeta"]>>[0]);
      break;
    case "delta":
      handlers.onDelta?.(String(dato));
      break;
    case "citations":
      handlers.onCitations?.(dato as Citation[]);
      break;
    case "error":
      handlers.onError?.((dato as { detail?: string }).detail ?? "Error");
      break;
  }
}
