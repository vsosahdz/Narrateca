import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

/**
 * Envoltorios de navegación conscientes del idioma.
 *
 * Usar estos en lugar de los de `next/link` y `next/navigation` es lo que hace
 * que cambiar de idioma conserve la página actual en vez de devolver al inicio.
 */
export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
