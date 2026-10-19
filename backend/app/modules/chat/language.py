"""Detección del idioma del mensaje.

Solo distingue español de inglés, que son los dos idiomas de la plataforma. No
se usa una biblioteca de detección porque el problema real es mucho más
estrecho que el que esas bibliotecas resuelven: aquí no hay que elegir entre
setenta idiomas, sino entre dos, sobre mensajes cortos donde los detectores
estadísticos generales se equivocan con frecuencia.

El criterio es el peso de palabras funcionales. Son las que más se repiten en
cualquier frase y las que menos se comparten entre los dos idiomas.
"""

from __future__ import annotations

import re

#: Palabras funcionales que aparecen casi sin excepción en una frase del
#: idioma, y casi nunca en el otro. Se excluyen a propósito las que coinciden
#: —«no», «me», «a», «sin»— porque no aportan y sí confunden.
PALABRAS_ES = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "pero",
        "porque",
        "que",
        "qué",
        "cómo",
        "cuándo",
        "dónde",
        "quién",
        "cuál",
        "cuáles",
        "es",
        "son",
        "era",
        "fue",
        "ser",
        "estar",
        "está",
        "están",
        "para",
        "por",
        "con",
        "su",
        "sus",
        "mi",
        "mis",
        "tu",
        "tus",
        "se",
        "lo",
        "les",
        "nos",
        "yo",
        "tú",
        "él",
        "ella",
        "ellos",
        "ellas",
        "hay",
        "tiene",
        "tienen",
        "hacer",
        "puede",
        "pueden",
        "más",
        "muy",
        "cuenta",
        "cuéntame",
        "háblame",
        "dime",
        "sobre",
        "también",
        # Saludos y cortesías. Un mensaje de una sola palabra no tiene ninguna
        # palabra funcional que desempatar, y «hola» a secas es un primer turno
        # perfectamente normal.
        "hola",
        "buenos",
        "buenas",
        "gracias",
        "adiós",
    }
)

PALABRAS_EN = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "and",
        "or",
        "but",
        "because",
        "that",
        "what",
        "how",
        "when",
        "where",
        "who",
        "which",
        "why",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "for",
        "by",
        "with",
        "his",
        "her",
        "their",
        "my",
        "your",
        "its",
        "it",
        "he",
        "she",
        "they",
        "we",
        "you",
        "i",
        "there",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "can",
        "could",
        "tell",
        "about",
        "would",
        "should",
        "more",
        "very",
        "please",
        "hello",
        "hi",
        "hey",
        "thanks",
        "thank",
        "goodbye",
        "bye",
    }
)

#: Caracteres que en la práctica solo aparecen en español. Se usan como
#: desempate, no como criterio principal: un mensaje en español escrito sin
#: acentos sigue siendo español.
MARCAS_ES = re.compile(r"[áéíóúñü¿¡]", re.IGNORECASE)

_PALABRAS = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)

IDIOMA_POR_DEFECTO = "es"


def detect_language(texto: str) -> str:
    """Devuelve `"es"` o `"en"`.

    Ante la duda devuelve español, que es el idioma principal de la plataforma
    y el del archivo. Equivocarse hacia el español deja a la persona leyendo el
    idioma del material que está consultando; equivocarse hacia el inglés la
    deja leyendo una traducción que no pidió.
    """
    if not texto or not texto.strip():
        return IDIOMA_POR_DEFECTO

    palabras = [p.lower() for p in _PALABRAS.findall(texto)]
    if not palabras:
        return IDIOMA_POR_DEFECTO

    puntos_es = sum(1 for p in palabras if p in PALABRAS_ES)
    puntos_en = sum(1 for p in palabras if p in PALABRAS_EN)

    if puntos_es != puntos_en:
        return "es" if puntos_es > puntos_en else "en"

    # Empate —habitual en mensajes de dos o tres palabras—: decide la
    # ortografía. «¿Cómo están?» no deja duda aunque ninguna palabra funcional
    # desempate.
    if MARCAS_ES.search(texto):
        return "es"

    return IDIOMA_POR_DEFECTO
