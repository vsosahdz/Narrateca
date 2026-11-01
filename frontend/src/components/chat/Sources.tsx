/**
 * Las fuentes de una respuesta.
 *
 * Se separan las citadas de las que no lo fueron. Un fragmento recuperado que
 * la respuesta no llegó a usar sigue siendo material válido del archivo —puede
 * valer como lectura relacionada— pero no sostiene ninguna afirmación, y
 * presentarlo junto a las citadas engañaría sobre qué apoya qué.
 */

"use client";

import { useTranslations } from "next-intl";

import type { Citation } from "@/lib/chatApi";

import styles from "./Sources.module.css";

interface Props {
  citations: Citation[];
  locale: string;
}

export function Sources({ citations, locale }: Props) {
  const t = useTranslations("chat");

  if (citations.length === 0) return null;

  const citadas = citations.filter((c) => c.cited);
  const relacionadas = citations.filter((c) => !c.cited);

  return (
    <div className={styles.wrapper}>
      {citadas.length > 0 && (
        <>
          <h3 className={styles.heading}>{t("sources")}</h3>
          <ol className={styles.list}>
            {citadas.map((cita) => (
              <Fuente key={cita.marker} cita={cita} locale={locale} label={t("source_link")} />
            ))}
          </ol>
        </>
      )}

      {relacionadas.length > 0 && (
        <details className={styles.related}>
          <summary className={styles.summary}>{t("uncited")}</summary>
          <ol className={styles.list}>
            {relacionadas.map((cita) => (
              <Fuente key={cita.marker} cita={cita} locale={locale} label={t("source_link")} />
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function Fuente({
  cita,
  locale,
  label,
}: {
  cita: Citation;
  locale: string;
  label: string;
}) {
  return (
    <li className={styles.item} id={`cita-${cita.marker}`}>
      <span className={styles.marker} aria-hidden="true">
        {cita.marker}
      </span>
      <div className={styles.body}>
        {/* Las palabras del archivo, tal cual. No se reformulan ni se recortan
            a media frase: el fragmento es la prueba de la afirmación. */}
        <blockquote className={styles.quote} lang="es">
          {cita.text}
        </blockquote>

        {cita.translation && (
          <p className={styles.translation} lang={locale}>
            <span className={styles.translationTag}>translation</span>
            {cita.translation}
          </p>
        )}

        <a className={styles.link} href={`/${locale}${cita.url.replace(/^\/[a-z]{2}/, "")}`}>
          {cita.item_title} · {label}
        </a>
      </div>
    </li>
  );
}
