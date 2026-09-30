/**
 * Configuración de stylelint.
 *
 * La regla que importa en este proyecto: **los componentes no declaran colores
 * literales**. La paleta vive en `src/styles/tokens/` y solo ahí se editan
 * valores, para que sustituir la paleta completa sea editar dos archivos y no
 * rastrear colores por todo el código (spec `design-tokens`).
 */

const COLOR_PROPERTY_MESSAGE =
  "Los componentes no declaran colores literales. Usa un token: var(--accent), " +
  "var(--text-primary), … La paleta vive en src/styles/tokens/.";

const config = {
  extends: "stylelint-config-standard",

  rules: {
    "custom-property-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    "selector-class-pattern": null,
    "import-notation": "string",
    "color-hex-length": "long",

    // Reglas cosméticas desactivadas a propósito:
    // - value-keyword-case bajaría a minúsculas los nombres de familias
    //   tipográficas ("Georgia" → "georgia"), lo cual es incorrecto.
    // - las líneas en blanco entre grupos de tokens son la documentación de la
    //   paleta; forzar su ausencia haría el archivo ilegible.
    "value-keyword-case": null,
    "custom-property-empty-line-before": null,
    "declaration-empty-line-before": null,
  },

  overrides: [
    {
      // Componentes y estilos globales: solo tokens.
      files: ["src/**/*.css"],
      rules: {
        "color-no-hex": [true, { message: COLOR_PROPERTY_MESSAGE }],
        "color-named": ["never", { message: COLOR_PROPERTY_MESSAGE }],
        "function-disallowed-list": [
          ["rgb", "rgba", "hsl", "hsla", "color-mix", "oklch", "lab"],
          {
            message:
              "Los componentes no calculan colores. Si hace falta una variante, " +
              "defínela como token en src/styles/tokens/.",
          },
        ],
      },
    },
    {
      // Única excepción: la definición de la paleta.
      files: ["src/styles/tokens/**/*.css"],
      rules: {
        "color-no-hex": null,
        "color-named": null,
        "function-disallowed-list": null,
      },
    },
  ],
};

export default config;
