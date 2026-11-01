/**
 * La recepción: dice en qué comunidad hay material y encamina.
 *
 * No es una conversación. El backend que la atiende no llama al modelo de
 * lenguaje: devuelve una lista de comunidades, y por eso esta pantalla no
 * tiene ninguna burbuja de respuesta que mostrar. Lo que no puede redactar,
 * tampoco puede inventarlo.
 */

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/Button";
import type { Orientation } from "@/lib/chatApi";
import { orient } from "@/lib/chatApi";

import styles from "./Reception.module.css";

interface Props {
  locale: string;
  onChoose: (themeSlug: string) => void;
}

export function Reception({ locale, onChoose }: Props) {
  const t = useTranslations("chat");
  const [pregunta, setPregunta] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [resultado, setResultado] = useState<Orientation[] | null>(null);

  async function buscar(evento: React.FormEvent) {
    evento.preventDefault();
    const texto = pregunta.trim();
    if (!texto || buscando) return;

    setBuscando(true);
    try {
      const { communities } = await orient(texto);
      setResultado(communities);
    } catch {
      setResultado([]);
    } finally {
      setBuscando(false);
    }
  }

  return (
    <section className={styles.wrapper} aria-labelledby="recepcion">
      <form onSubmit={buscar}>
        <label className={styles.label} htmlFor="recepcion" id="recepcion">
          {t("reception_label")}
        </label>
        <div className={styles.row}>
          <input
            id="recepcion"
            className={styles.input}
            value={pregunta}
            onChange={(evento) => setPregunta(evento.target.value)}
            placeholder={t("reception_placeholder")}
            autoComplete="off"
            maxLength={2000}
          />
          <Button type="submit" variant="primary" loading={buscando}>
            {buscando ? t("reception_searching") : t("reception_submit")}
          </Button>
        </div>
      </form>

      {resultado !== null && (
        <div className={styles.result} aria-live="polite">
          {resultado.length === 0 ? (
            <p className={styles.empty}>{t("reception_empty")}</p>
          ) : (
            <>
              <p className={styles.found}>{t("reception_found")}</p>
              <ul className={styles.list}>
                {resultado.map((comunidad) => (
                  <li key={comunidad.theme_slug}>
                    <button
                      type="button"
                      className={styles.hit}
                      onClick={() => onChoose(comunidad.theme_slug)}
                    >
                      <span className={styles.hitName}>
                        {locale === "en" ? comunidad.theme_name_en : comunidad.theme_name_es}
                      </span>
                      {comunidad.best_item_title && (
                        <span className={styles.hitDetail}>{comunidad.best_item_title}</span>
                      )}
                      <span className={styles.hitCount}>
                        {t("reception_matches", { count: comunidad.matches })}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
