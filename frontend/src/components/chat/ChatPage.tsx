/**
 * La página del chatbot: recepción, selector y conversación.
 *
 * Dos estados: sin comunidad elegida se ve la recepción y las cuatro
 * comunidades; con una elegida, la conversación.
 *
 * Cambiar de comunidad desmonta `Conversation`, y con ella se va el hilo. Es
 * intencional: el historial de una comunidad no debe viajar al prompt de otra,
 * porque entonces la segunda narradora estaría leyendo testimonios ajenos.
 */

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import type { Persona } from "@/lib/chatApi";

import { Conversation } from "./Conversation";
import { Reception } from "./Reception";
import styles from "./ChatPage.module.css";

const ESTADO: Record<Persona["activation"], string> = {
  active: "state_active",
  coming_soon: "state_coming_soon",
  draft: "state_draft",
};

interface Props {
  personas: Persona[];
  locale: string;
}

export function ChatPage({ personas, locale }: Props) {
  const t = useTranslations("chat");
  const [elegida, setElegida] = useState<string | null>(null);

  const persona = personas.find((p) => p.theme_slug === elegida) ?? null;

  if (persona) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.conversationHeader}>
          <button type="button" className={styles.back} onClick={() => setElegida(null)}>
            ← {t("back")}
          </button>
          <h1 className={styles.conversationTitle}>
            {locale === "en" ? persona.name_en : persona.name_es}
          </h1>
        </div>

        <Aviso />

        <div data-theme={persona.theme_slug}>
          <Conversation persona={persona} locale={locale} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>{t("title")}</h1>
      <p className={styles.intro}>{t("intro")}</p>

      <Aviso />

      <Reception locale={locale} onChoose={setElegida} />

      <section aria-labelledby="comunidades">
        <h2 className={styles.sectionTitle} id="comunidades">
          {t("communities")}
        </h2>

        {/* Se muestran las cuatro siempre, incluidas las que no están
            abiertas. Esconder una comunidad porque su material aún se revisa
            daría a entender que no existe. */}
        <ul className={styles.grid}>
          {personas.map((p) => {
            const disponible = p.activation === "active";
            return (
              <li key={p.theme_slug}>
                <div className={styles.card} data-theme={p.theme_slug}>
                  <span className={styles.accent} aria-hidden="true" />
                  <h3 className={styles.cardName}>
                    {locale === "en" ? p.name_en : p.name_es}
                  </h3>
                  <p
                    className={disponible ? styles.stateOpen : styles.stateClosed}
                  >
                    {t(ESTADO[p.activation])}
                  </p>

                  {disponible ? (
                    <button
                      type="button"
                      className={styles.open}
                      onClick={() => setElegida(p.theme_slug)}
                    >
                      {t("open")}
                    </button>
                  ) : (
                    <p className={styles.unavailable}>{t("unavailable_note")}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
        <p className={styles.switchNote}>{t("switch_warning")}</p>
      </section>
    </div>
  );
}

/** Aviso de sistema automatizado.
 *
 * Aparece antes de cualquier intercambio, y no como letra pequeña. La materia
 * del archivo —violencia, migración, discapacidad— hace que quien escribe
 * pueda estar buscando a alguien que la escuche, y dejarle creer que ese
 * alguien existe sería el fallo más grave que esta página puede cometer.
 */
function Aviso() {
  const t = useTranslations("chat");
  return (
    <aside className={styles.disclaimer} role="note">
      <strong className={styles.disclaimerTitle}>{t("disclaimer_title")}</strong>
      <p className={styles.disclaimerBody}>{t("disclaimer_body")}</p>
    </aside>
  );
}
