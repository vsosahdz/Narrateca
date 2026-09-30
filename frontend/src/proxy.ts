import createMiddleware from "next-intl/middleware";

import { routing } from "@/i18n/routing";

/**
 * Negociación de idioma y prefijo de ruta.
 *
 * En Next.js 16 esta convención de archivo se llama `proxy` (antes `middleware`).
 * La firma es la misma.
 */
export default createMiddleware(routing);

export const config = {
  // Se excluyen archivos estáticos y rutas internas de Next.
  // No se excluye `/api` porque el frontend no expone API: el backend es un
  // servicio aparte (ver `npm run check:no-api-routes`).
  matcher: ["/((?!_next|_vercel|.*\\..*).*)"],
};
