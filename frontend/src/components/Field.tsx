"use client";

import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import styles from "./Field.module.css";

/**
 * Campo de formulario con etiqueta, ayuda y error correctamente asociados.
 *
 * Tres cosas que este componente resuelve y que casi siempre se hacen mal:
 *
 * 1. La etiqueta se asocia con `htmlFor`/`id`. Un texto suelto junto a un campo
 *    no es una etiqueta: un lector de pantalla anuncia el campo sin nombre.
 * 2. La ayuda y el error se enlazan con `aria-describedby`, para que se
 *    anuncien al enfocar el campo y no solo se vean.
 * 3. El error se marca con `aria-invalid` y se anuncia con `role="alert"`.
 *
 * El error nunca se comunica solo con color: lleva texto. Depender del color
 * excluye a quien no lo distingue (WCAG 2.2 SC 1.4.1).
 */
export function Field({
  label,
  hint,
  error,
  required,
  id: providedId,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  /** Texto de ayuda permanente. */
  hint?: ReactNode;
  /** Mensaje de error. Su presencia marca el campo como inválido. */
  error?: string;
}) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;

  const describedBy = [hint ? hintId : null, error ? errorId : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {required && (
          <span className={styles.required} aria-hidden="true">
            *
          </span>
        )}
        {required && <span className="visually-hidden">(obligatorio)</span>}
      </label>

      {hint && (
        <p id={hintId} className={styles.hint}>
          {hint}
        </p>
      )}

      <input
        id={id}
        className={[styles.input, error ? styles.inputError : null]
          .filter(Boolean)
          .join(" ")}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        {...rest}
      />

      {error && (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
