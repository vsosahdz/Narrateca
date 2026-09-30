/**
 * Verifica la convención de que el frontend NO expone API routes.
 *
 * El backend de NarraTECa es un servicio FastAPI independiente. Next.js es
 * exclusivamente capa de renderizado y ruteo. Escribir un route handler aquí
 * abre una segunda puerta trasera al dominio, fuera de la documentación Swagger,
 * fuera de la autorización por tema del panel y fuera de las verificaciones de
 * consentimiento del backend.
 *
 * Si de verdad hace falta un endpoint, va en `backend/app/modules/<dominio>/`.
 *
 *   npm run check:no-api-routes
 */

import { readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const APP_DIR = join(ROOT, "src", "app");

/** Nombres de archivo que Next.js trata como manejadores de servidor. */
const HANDLER_FILES = new Set([
  "route.ts",
  "route.tsx",
  "route.js",
  "route.mjs",
  "route.jsx",
]);

const offenders = [];

function walk(dir) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return; // el directorio aún no existe
  }
  for (const entry of entries) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walk(full);
    } else if (HANDLER_FILES.has(entry)) {
      offenders.push(relative(ROOT, full));
    }
  }
}

walk(APP_DIR);

if (offenders.length > 0) {
  console.error("\n✗ Se encontraron route handlers en el frontend:\n");
  for (const file of offenders) console.error(`   ${file}`);
  console.error(
    "\n  El frontend no expone API. Todo endpoint vive en el backend FastAPI,\n" +
      "  donde está la documentación Swagger, la autorización por tema y las\n" +
      "  verificaciones de consentimiento.\n",
  );
  process.exit(1);
}

console.log("✓ Sin route handlers en el frontend: Next.js es solo capa de render y ruteo.");
