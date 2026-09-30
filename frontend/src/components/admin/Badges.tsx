"use client";

import { useTranslations } from "next-intl";

import type { ConsentScope, PublicationStatus } from "@/lib/adminApi";

import styles from "./Badges.module.css";

/**
 * Distintivos de estado y consentimiento.
 *
 * Todos comunican con **texto**, no solo con color. El color acompaña; si fuera
 * el único portador de la información, quien no lo distingue no podría saber si
 * una pieza está publicada o si alimenta al chatbot (WCAG 2.2 SC 1.4.1).
 */

export function StatusBadge({ status }: { status: PublicationStatus }) {
  const t = useTranslations("admin.status");
  return (
    <span className={styles.badge} data-status={status}>
      {t(status)}
    </span>
  );
}

export function ConsentBadge({ scope }: { scope: ConsentScope }) {
  const t = useTranslations("admin.consent");
  return (
    <span className={styles.badge} data-consent={scope}>
      {t(scope)}
    </span>
  );
}

/**
 * Si la pieza alimenta el corpus del chatbot en este momento.
 *
 * Es la información que el panel debe hacer evidente sin abrir el detalle: es
 * la diferencia entre publicar y prestar la voz de alguien a un modelo.
 */
export function IndexBadge({ indexed }: { indexed: boolean }) {
  const t = useTranslations("admin");
  return (
    <span className={styles.badge} data-indexed={indexed ? "yes" : "no"}>
      {indexed ? t("indexed") : t("notIndexed")}
    </span>
  );
}
