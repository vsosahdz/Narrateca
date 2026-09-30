"""Preparación de la consulta para la búsqueda léxica.

Dos correcciones que solo aparecen al probar con preguntas reales:

1. **`websearch_to_tsquery` exige TODOS los términos.** «¿cómo fue la primera
   noche?» se convierte en `'com' & 'primer' & 'noch'`, y el archivo no contiene
   «cómo». Una pregunta natural siempre trae palabras que no están en el corpus,
   así que con conjunción casi toda pregunta legítima queda rechazada.

2. **Los interrogativos producen coincidencias espurias.** El lematizador español
   reduce «cómo» y «comida» a la misma raíz `com`, de modo que preguntar «¿cómo
   fue…?» coincide con un testimonio que menciona comida. La palabra no aportaba
   significado y sí ruido.

La solución es quitar los interrogativos, buscar con disyunción y medir **qué
fracción de los términos con contenido coincide de verdad**.
"""

import re

from sqlalchemy import Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.models import TEXT_SEARCH_CONFIG

#: Interrogativos y muletillas que PostgreSQL no trata como vacías en español
#: pero que no aportan significado a una pregunta. Se listan ya lematizadas
#: porque es así como llegan desde `to_tsvector`.
QUESTION_LEXEMES = frozenset(
    {
        "com",  # cómo, como
        "que",  # qué, que
        "cual",  # cuál, cuáles
        "quien",  # quién, quiénes
        "dond",  # dónde, donde
        "cuand",  # cuándo, cuando
        "cuant",  # cuánto, cuánta
        "porqu",  # porqué
        "cuent",  # cuéntame
        "dim",  # dime
        "habl",  # háblame
        "expl",  # explícame
        "sab",  # sabes
        "pued",  # puedes
        "pas",  # pasó, pasa — demasiado genérico en preguntas
    }
)

_LEXEME = re.compile(r"'((?:[^']|'')+)'")


async def query_lexemes(session: AsyncSession, query: str) -> list[str]:
    """Términos con contenido de una consulta, lematizados por PostgreSQL.

    Se lematiza con el mismo motor que indexó el corpus: hacerlo en Python con
    otra librería produciría raíces distintas y las comparaciones fallarían de
    forma silenciosa.
    """
    fila = await session.execute(select(cast(func.to_tsvector(TEXT_SEARCH_CONFIG, query), Text)))
    tsv = fila.scalar_one() or ""

    vistos: list[str] = []
    for match in _LEXEME.finditer(tsv):
        lexema = match.group(1).replace("''", "'")
        if lexema in QUESTION_LEXEMES or len(lexema) < 3:
            continue
        if lexema not in vistos:
            vistos.append(lexema)

    return vistos


def or_tsquery(lexemes: list[str]) -> str:
    """Consulta de disyunción a partir de los lexemas ya normalizados."""
    return " | ".join(lexemes)
