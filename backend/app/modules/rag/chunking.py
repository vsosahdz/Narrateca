"""Segmentación de textos en fragmentos indexables.

Tamaño fijo con solape, ajustando el corte a la frontera de oración más cercana
(`design.md`, decisión 19).

El ajuste a la oración no es cosmético. Sin él, una cita del chatbot puede
empezar a media frase, y en un testimonio eso cambia lo que la persona dijo:
«no dormí en tres días» y «dormí en tres días» son afirmaciones opuestas
separadas por un corte mal puesto.
"""

import re
from dataclasses import dataclass

#: Fin de oración seguido de espacio. Incluye los signos de cierre del español
#: y las comillas, porque una cita suele terminar con ellas.
SENTENCE_END = re.compile(r'[.!?…](?:["»”\')\]]+)?\s')

#: Ventana alrededor del corte teórico donde se busca un fin de oración. Más
#: allá de esto, forzar la frontera desbalancearía demasiado los fragmentos.
SEARCH_WINDOW = 200

#: Un fragmento más corto que esto casi nunca aporta contexto suficiente para
#: entenderse solo, y como cita quedaría desnudo.
MIN_CHUNK_CHARS = 120


@dataclass(frozen=True)
class TextChunk:
    text: str
    ordinal: int
    char_start: int
    char_end: int


def _normalize(text: str) -> str:
    """Colapsa espacios sin perder los saltos de párrafo."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _find_boundary(text: str, target: int) -> int:
    """Frontera de oración más cercana a `target`, dentro de la ventana."""
    lo = max(0, target - SEARCH_WINDOW)
    hi = min(len(text), target + SEARCH_WINDOW)

    candidatos = [m.end() for m in SENTENCE_END.finditer(text, lo, hi)]
    if candidatos:
        return min(candidatos, key=lambda pos: abs(pos - target))

    # Sin fin de oración cerca, se corta en un espacio antes que a media
    # palabra: partir «frontera» en «fron» + «tera» destruiría la coincidencia
    # léxica además de quedar ilegible.
    espacio = text.rfind(" ", lo, target)
    return espacio + 1 if espacio > lo else target


def _next_boundary(text: str, desde: int, *, limite: int) -> int:
    """Primer inicio de oración a partir de `desde`, sin pasar de `limite`.

    Si no encuentra ninguno, retrocede a un inicio de palabra: perder algo de
    solape es preferible a que un fragmento empiece a media palabra.
    """
    match = SENTENCE_END.search(text, desde, min(limite, len(text)))
    if match is not None:
        return match.end()

    espacio = text.find(" ", desde, limite)
    return espacio + 1 if espacio != -1 else desde


def chunk_text(
    text: str,
    *,
    size: int = 800,
    overlap: int = 120,
) -> list[TextChunk]:
    """Divide un texto en fragmentos con solape.

    Los desplazamientos devueltos corresponden al texto **normalizado**, que es
    el que se almacena, de modo que puedan usarse para resaltar la cita dentro
    de la pieza.
    """
    if size <= 0:
        raise ValueError("El tamaño de fragmento debe ser positivo.")
    if overlap >= size:
        raise ValueError("El solape debe ser menor que el tamaño del fragmento.")

    normalizado = _normalize(text)
    if not normalizado:
        return []

    if len(normalizado) <= size:
        return [TextChunk(normalizado, 0, 0, len(normalizado))]

    fragmentos: list[TextChunk] = []
    inicio = 0
    ordinal = 0

    while inicio < len(normalizado):
        objetivo = inicio + size

        if objetivo >= len(normalizado):
            fin = len(normalizado)
        else:
            fin = _find_boundary(normalizado, objetivo)
            # La búsqueda de frontera puede devolver una posición anterior al
            # inicio si el texto no tiene puntuación ni espacios en la ventana.
            # Sin esta salvaguarda, el bucle no avanzaría.
            if fin <= inicio:
                fin = objetivo

        pieza = normalizado[inicio:fin].strip()
        if pieza:
            fragmentos.append(TextChunk(pieza, ordinal, inicio, fin))
            ordinal += 1

        if fin >= len(normalizado):
            break

        # El inicio del siguiente fragmento también se ajusta a una frontera de
        # oración. Sin esto, el ajuste del final no sirve de nada: el solape
        # haría que cada fragmento arrancara a media frase, y el inicio de un
        # fragmento es exactamente donde empieza una cita.
        crudo = max(fin - overlap, inicio + 1)
        inicio = _next_boundary(normalizado, crudo, limite=fin)

    # El último fragmento puede quedar demasiado corto por efecto del solape.
    # Se funde con el anterior en lugar de dejar una cita de dos líneas sin
    # contexto.
    if len(fragmentos) > 1 and len(fragmentos[-1].text) < MIN_CHUNK_CHARS:
        ultimo = fragmentos.pop()
        anterior = fragmentos.pop()
        fundido = normalizado[anterior.char_start : ultimo.char_end].strip()
        fragmentos.append(
            TextChunk(fundido, anterior.ordinal, anterior.char_start, ultimo.char_end)
        )

    return fragmentos


def build_indexable_text(title: str, summary: str | None, body: str | None) -> str:
    """Texto que se indexa de una pieza.

    Incluye el título y el resumen además del cuerpo: son las palabras que mejor
    describen la pieza y suelen ser las que alguien usaría al preguntar. Dejarlos
    fuera desperdiciaría la señal léxica más fuerte que tiene el catálogo.
    """
    partes = [title.strip()]
    if summary and summary.strip():
        partes.append(summary.strip())
    if body and body.strip():
        partes.append(body.strip())
    return "\n\n".join(partes)
