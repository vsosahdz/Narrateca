/**
 * Verificación de contraste de los tokens de color.
 *
 * Implementa el cálculo de relación de contraste de WCAG 2.2 y lo aplica a todas
 * las combinaciones que el sistema de diseño declara como válidas.
 *
 * Umbrales (WCAG 2.2 AA):
 *   - Texto normal .................. 4.5:1
 *   - Texto grande y componentes .... 3.0:1
 *
 * Se ejecuta en la canalización de pruebas. Cambiar un token sin volver a
 * ejecutar esta verificación es la forma más común de romper la accesibilidad
 * sin darse cuenta.
 *
 *   npm run check:contrast
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TOKENS_DIR = join(HERE, "..", "src", "styles", "tokens");

const THRESHOLD_TEXT = 4.5;
const THRESHOLD_UI = 3.0;

type Level = "text" | "ui";

interface Check {
  /** Token de primer plano. */
  fg: string;
  /** Token de fondo. */
  bg: string;
  /** Umbral aplicable. */
  level: Level;
  /** Para qué se usa esta combinación, para que un fallo sea accionable. */
  usage: string;
}

// --- Cálculo WCAG ---------------------------------------------------------

function parseHex(hex: string): [number, number, number] {
  const clean = hex.trim().replace(/^#/, "");
  const full =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean;
  if (!/^[0-9a-f]{6}$/i.test(full)) {
    throw new Error(`Color no reconocido: "${hex}"`);
  }
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

/** Luminancia relativa según WCAG 2.x. */
function relativeLuminance(hex: string): number {
  const channels = parseHex(hex).map((value) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const [lighter, darker] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (lighter + 0.05) / (darker + 0.05);
}

// --- Lectura de tokens ----------------------------------------------------

/** Extrae los tokens de color (`--nombre: #hex;`) de un bloque CSS. */
function extractColors(css: string): Record<string, string> {
  const out: Record<string, string> = {};
  const re = /--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(css)) !== null) {
    out[match[1]] = match[2];
  }
  return out;
}

/** Extrae los bloques por tema de `themes.css`. */
function extractThemes(css: string): Record<string, Record<string, string>> {
  const out: Record<string, Record<string, string>> = {};
  const re = /\[data-theme="([a-z0-9_]+)"\]\s*\{([^}]*)\}/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(css)) !== null) {
    out[match[1]] = extractColors(match[2]);
  }
  return out;
}

// --- Combinaciones declaradas como válidas --------------------------------

const BASE_CHECKS: Check[] = [
  { fg: "text-primary", bg: "surface-page", level: "text", usage: "cuerpo sobre la página" },
  { fg: "text-primary", bg: "surface-raised", level: "text", usage: "cuerpo en tarjetas" },
  { fg: "text-primary", bg: "surface-sunken", level: "text", usage: "cuerpo en zonas hundidas" },
  { fg: "text-secondary", bg: "surface-page", level: "text", usage: "texto secundario" },
  { fg: "text-secondary", bg: "surface-raised", level: "text", usage: "texto secundario en tarjetas" },
  { fg: "text-muted", bg: "surface-page", level: "text", usage: "metadatos y pies" },
  { fg: "text-muted", bg: "surface-raised", level: "text", usage: "metadatos en tarjetas" },
  { fg: "text-on-inverse", bg: "surface-inverse", level: "text", usage: "texto sobre fondo oscuro" },
  { fg: "border-strong", bg: "surface-page", level: "ui", usage: "bordes de campos y controles" },
  { fg: "focus-ring-color", bg: "surface-page", level: "ui", usage: "indicador de foco" },
  { fg: "focus-ring-color", bg: "surface-raised", level: "ui", usage: "indicador de foco en tarjetas" },
  { fg: "state-danger", bg: "surface-page", level: "text", usage: "mensajes de error" },
  { fg: "state-danger", bg: "state-danger-soft", level: "text", usage: "error sobre su fondo" },
  { fg: "state-success", bg: "state-success-soft", level: "text", usage: "éxito sobre su fondo" },
  { fg: "state-warning", bg: "state-warning-soft", level: "text", usage: "aviso sobre su fondo" },
  { fg: "accent", bg: "surface-page", level: "text", usage: "acento por defecto como texto" },
  { fg: "on-accent", bg: "accent", level: "text", usage: "texto sobre el acento por defecto" },
];

/** Combinaciones que debe cumplir el acento de cada tema. */
const THEME_CHECKS: Array<Omit<Check, "usage"> & { usage: string }> = [
  { fg: "accent", bg: "surface-page", level: "text", usage: "enlaces y énfasis sobre la página" },
  { fg: "accent", bg: "surface-raised", level: "text", usage: "enlaces y énfasis en tarjetas" },
  { fg: "accent", bg: "accent-soft", level: "text", usage: "acento sobre su propio realce" },
  { fg: "accent-strong", bg: "surface-page", level: "text", usage: "estado activo y hover" },
  { fg: "on-accent", bg: "accent", level: "text", usage: "texto sobre el acento" },
  { fg: "accent", bg: "surface-page", level: "ui", usage: "bordes y controles con acento" },
];

// --- Ejecución ------------------------------------------------------------

interface Result {
  scope: string;
  check: Check;
  ratio: number;
  threshold: number;
  pass: boolean;
}

function run(): number {
  const baseCss = readFileSync(join(TOKENS_DIR, "base.css"), "utf8");
  const themesCss = readFileSync(join(TOKENS_DIR, "themes.css"), "utf8");

  const base = extractColors(baseCss);
  const themes = extractThemes(themesCss);

  const results: Result[] = [];

  const evaluate = (scope: string, check: Check, palette: Record<string, string>) => {
    const fg = palette[check.fg] ?? base[check.fg];
    const bg = palette[check.bg] ?? base[check.bg];
    if (!fg || !bg) {
      throw new Error(
        `Token faltante en "${scope}": ${!fg ? `--${check.fg}` : `--${check.bg}`}`,
      );
    }
    const ratio = contrastRatio(fg, bg);
    const threshold = check.level === "text" ? THRESHOLD_TEXT : THRESHOLD_UI;
    results.push({ scope, check, ratio, threshold, pass: ratio >= threshold });
  };

  for (const check of BASE_CHECKS) evaluate("base", check, base);

  for (const [slug, palette] of Object.entries(themes)) {
    for (const check of THEME_CHECKS) evaluate(slug, check, palette);
  }

  // Reporte
  let currentScope = "";
  for (const r of results) {
    if (r.scope !== currentScope) {
      currentScope = r.scope;
      console.log(`\n  ${currentScope}`);
    }
    const mark = r.pass ? "✓" : "✗";
    const ratio = r.ratio.toFixed(2).padStart(6);
    const pair = `--${r.check.fg} sobre --${r.check.bg}`;
    console.log(
      `   ${mark} ${ratio}:1  (mín ${r.threshold})  ${pair.padEnd(46)} ${r.check.usage}`,
    );
  }

  const failures = results.filter((r) => !r.pass);
  console.log("");
  if (failures.length > 0) {
    console.error(
      `✗ ${failures.length} de ${results.length} combinaciones no alcanzan el mínimo de contraste.\n`,
    );
    for (const f of failures) {
      console.error(
        `   ${f.scope}: --${f.check.fg} sobre --${f.check.bg} = ${f.ratio.toFixed(2)}:1, ` +
          `se requiere ${f.threshold}:1 (${f.check.usage})`,
      );
    }
    console.error("");
    return 1;
  }

  console.log(`✓ ${results.length} combinaciones verificadas, todas cumplen WCAG 2.2 AA.\n`);
  return 0;
}

process.exit(run());
