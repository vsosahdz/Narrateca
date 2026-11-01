/**
 * La conversación con la narradora de una comunidad.
 *
 * El estado vive aquí y no sube a la página porque cambiar de comunidad
 * **empieza una conversación nueva**: al desmontarse este componente se va
 * todo con él, que es exactamente lo que debe pasar. El historial de una
 * comunidad no viaja al prompt de otra.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/Button";
import type { Citation, Persona } from "@/lib/chatApi";
import { ChatError, streamChat } from "@/lib/chatApi";

import { AnswerText } from "./AnswerText";
import { Sources } from "./Sources";
import styles from "./Conversation.module.css";

interface Turno {
  id: string;
  pregunta: string;
  respuesta: string;
  citations: Citation[];
  contained: boolean;
  noMaterial: boolean;
  error: string | null;
  enCurso: boolean;
}

interface Props {
  persona: Persona;
  locale: string;
}

export function Conversation({ persona, locale }: Props) {
  const t = useTranslations("chat");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [borrador, setBorrador] = useState("");
  const [enviando, setEnviando] = useState(false);
  const conversacion = useRef<string | undefined>(undefined);
  const aborto = useRef<AbortController | null>(null);
  const finDelHilo = useRef<HTMLDivElement>(null);

  // Al desmontar se corta cualquier respuesta en vuelo. Sin esto, cambiar de
  // comunidad dejaría llegando trozos de la anterior.
  useEffect(() => () => aborto.current?.abort(), []);

  useEffect(() => {
    finDelHilo.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnos]);

  async function preguntar(texto: string) {
    const pregunta = texto.trim();
    if (!pregunta || enviando) return;

    const id = crypto.randomUUID();
    setBorrador("");
    setEnviando(true);
    setTurnos((previos) => [
      ...previos,
      {
        id,
        pregunta,
        respuesta: "",
        citations: [],
        contained: false,
        noMaterial: false,
        error: null,
        enCurso: true,
      },
    ]);

    const actualizar = (cambio: Partial<Turno>) =>
      setTurnos((previos) =>
        previos.map((turno) => (turno.id === id ? { ...turno, ...cambio } : turno)),
      );

    const controlador = new AbortController();
    aborto.current = controlador;

    try {
      await streamChat(
        persona.theme_slug,
        { message: pregunta, conversation_id: conversacion.current },
        {
          onMeta: (meta) => {
            conversacion.current = meta.conversation_id;
            actualizar({
              contained: meta.contained,
              noMaterial: meta.no_material_reason !== null,
            });
          },
          onDelta: (trozo) =>
            setTurnos((previos) =>
              previos.map((turno) =>
                turno.id === id ? { ...turno, respuesta: turno.respuesta + trozo } : turno,
              ),
            ),
          onCitations: (citas) => actualizar({ citations: citas }),
          onError: (detalle) => actualizar({ error: detalle }),
        },
        controlador.signal,
      );
    } catch (error) {
      if (!controlador.signal.aborted) {
        actualizar({
          error: error instanceof ChatError ? error.message : t("error"),
        });
      }
    } finally {
      actualizar({ enCurso: false });
      setEnviando(false);
      aborto.current = null;
    }
  }

  const sugerencias = persona.suggested_questions;

  return (
    <div className={styles.wrapper}>
      {turnos.length === 0 && sugerencias.length > 0 && (
        <section className={styles.suggestions} aria-labelledby="sugerencias">
          <h2 className={styles.suggestionsTitle} id="sugerencias">
            {t("suggested")}
          </h2>
          <ul className={styles.suggestionList}>
            {sugerencias.map((pregunta) => (
              <li key={pregunta}>
                <button
                  type="button"
                  className={styles.suggestion}
                  onClick={() => preguntar(pregunta)}
                >
                  {pregunta}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ol className={styles.thread}>
        {turnos.map((turno) => (
          <li key={turno.id} className={styles.turn}>
            <p className={styles.question}>
              <span className={styles.who}>{t("you")}</span>
              {turno.pregunta}
            </p>

            <div className={styles.answer}>
              {(turno.contained || turno.noMaterial) && (
                <p className={styles.note}>
                  {turno.contained ? t("contained_note") : t("no_material_note")}
                </p>
              )}

              {/* `aria-live` para que quien usa lector de pantalla reciba la
                  respuesta a medida que llega, en lugar de un silencio seguido
                  de un bloque de texto. */}
              <div aria-live="polite" aria-busy={turno.enCurso}>
                <AnswerText text={turno.respuesta} citations={turno.citations} />
              </div>

              {turno.error && <p className={styles.error}>{turno.error}</p>}

              <Sources citations={turno.citations} locale={locale} />
            </div>
          </li>
        ))}
      </ol>
      <div ref={finDelHilo} />

      <form
        className={styles.form}
        onSubmit={(evento) => {
          evento.preventDefault();
          preguntar(borrador);
        }}
      >
        <label className={styles.label} htmlFor="pregunta">
          {t("input_label")}
        </label>
        <div className={styles.row}>
          <input
            id="pregunta"
            className={styles.input}
            value={borrador}
            onChange={(evento) => setBorrador(evento.target.value)}
            placeholder={t("input_placeholder")}
            autoComplete="off"
            maxLength={2000}
            disabled={enviando}
          />
          {enviando ? (
            <Button type="button" variant="secondary" onClick={() => aborto.current?.abort()}>
              {t("stop")}
            </Button>
          ) : (
            <Button type="submit" variant="primary" disabled={!borrador.trim()}>
              {t("send")}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
