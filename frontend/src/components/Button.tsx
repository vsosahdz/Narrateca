import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

/**
 * Botón base.
 *
 * Siempre renderiza un `<button>` real. Un `<div onClick>` no es alcanzable por
 * teclado, no se anuncia como botón y no responde a Enter ni Espacio; usarlo
 * rompe la navegación por teclado que la spec `public-site` exige.
 *
 * Para una acción que navega a otra dirección, usar `<Link>`, no este componente:
 * los enlaces y los botones se anuncian distinto y admiten interacciones
 * distintas (abrir en pestaña nueva, copiar dirección).
 */
export function Button({
  variant = "secondary",
  loading = false,
  children,
  className,
  disabled,
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  /** Marca la acción en curso. Deshabilita y lo anuncia con aria-busy. */
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type={type}
      className={[styles.button, styles[variant], className].filter(Boolean).join(" ")}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {children}
    </button>
  );
}
