import type { ElementType, ReactNode } from "react";

/**
 * Marca un bloque de contenido cuyo idioma difiere del de la página.
 *
 * Es indispensable en NarraTECa: el contenido del archivo permanece en español
 * aunque la interfaz esté en inglés. Sin este marcado, un lector de pantalla en
 * inglés pronuncia un testimonio en español con fonética inglesa y lo vuelve
 * incomprensible (WCAG 2.2 SC 3.1.2, "Idioma de las partes").
 *
 *   <Lang locale="es">No dormí tres días.</Lang>
 */
export function Lang({
  locale,
  as: Component = "span",
  children,
  className,
}: {
  /** Código de idioma del contenido, por ejemplo "es" o "en". */
  locale: string;
  /** Elemento a renderizar. Usar "blockquote" o "p" cuando corresponda. */
  as?: ElementType;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Component lang={locale} className={className}>
      {children}
    </Component>
  );
}
