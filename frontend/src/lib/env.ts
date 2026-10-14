/**
 * Lectura de variables de entorno.
 *
 * `process.env.X ?? "valor"` parece correcto y no lo es: `??` solo cae al valor
 * por defecto cuando la variable es `undefined`. Una variable **definida pero
 * vacía** —que es lo que produce un `ARG` de Docker sin valor— pasa el filtro y
 * llega como cadena vacía.
 *
 * El síntoma fue concreto: el build del frontend falló con `TypeError: Invalid
 * URL` porque `new URL(ruta, "")` no es una dirección válida. Costó más
 * entenderlo que arreglarlo, precisamente porque el error aparecía lejos de la
 * causa.
 */

/** Devuelve el valor de la variable, o el de respaldo si está ausente o vacía. */
export function envOr(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}
