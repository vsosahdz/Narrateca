"use client";

import { useTranslations } from "next-intl";

import styles from "./SkipLink.module.css";

/**
 * Enlace de salto al contenido principal.
 *
 * Es el primer elemento enfocable de la página. Permite a quien navega con
 * teclado o lector de pantalla saltarse el encabezado repetido en cada página
 * (WCAG 2.2 SC 2.4.1, "Evitar bloques").
 *
 * Está oculto hasta recibir foco, momento en el que debe ser claramente
 * visible: un enlace de salto que permanece invisible al enfocarse no cumple.
 */
export function SkipLink() {
  const t = useTranslations("nav");

  return (
    <a href="#contenido" className={styles.skipLink}>
      {t("skipToContent")}
    </a>
  );
}
