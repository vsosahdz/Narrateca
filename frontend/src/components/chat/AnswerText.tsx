/**
 * Texto de una respuesta, con los marcadores de cita convertidos en enlaces.
 *
 * Los marcadores son números entre corchetes que el modelo coloca junto a la
 * afirmación que sostiene cada fragmento: «la espera duró meses [2]».
 *
 * Esta es la parte frágil de presentar las citas así, y por eso el componente
 * desconfía: solo convierte en enlace los marcadores que corresponden a una
 * cita realmente recibida. Un `[9]` sobre cuatro fragmentos se descarta en
 * silencio. El servidor ya hace la misma limpieza sobre la respuesta completa;
 * aquí se repite porque durante la transmisión el texto llega por partes y
 * todavía no ha pasado por ella.
 */

"use client";

import type { Citation } from "@/lib/chatApi";

import styles from "./AnswerText.module.css";

const MARCADOR = /\[(\d{1,2})\]/g;

interface Props {
  text: string;
  citations: Citation[];
  /** Se invoca al pulsar un marcador, para destacar la fuente correspondiente. */
  onFocusCitation?: (marker: number) => void;
}

export function AnswerText({ text, citations, onFocusCitation }: Props) {
  const validos = new Set(citations.map((c) => c.marker));
  const piezas: React.ReactNode[] = [];

  let ultimo = 0;

  // `matchAll` y no `exec` en bucle: una expresión con bandera global guarda
  // su posición entre llamadas, y siendo de módulo esa posición sobreviviría
  // de un render al siguiente. El síntoma sería un marcador que unas veces se
  // enlaza y otras no, según lo que se hubiera renderizado antes.
  for (const coincidencia of text.matchAll(MARCADOR)) {
    const numero = Number(coincidencia[1]);
    const inicio = coincidencia.index;
    piezas.push(text.slice(ultimo, inicio));
    ultimo = inicio + coincidencia[0].length;

    if (!validos.has(numero)) {
      // Marcador sin fragmento detrás: se descarta y la frase sigue. Puede ser
      // correcta aunque la referencia esté mal puesta.
      continue;
    }

    piezas.push(
      <a
        key={`${inicio}-${numero}`}
        href={`#cita-${numero}`}
        className={styles.marker}
        onClick={() => onFocusCitation?.(numero)}
      >
        {numero}
      </a>,
    );
  }

  piezas.push(text.slice(ultimo));

  return <p className={styles.text}>{piezas}</p>;
}
