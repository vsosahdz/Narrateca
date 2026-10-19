"""Contención ante relatos personales.

Cuando alguien le cuenta al chatbot una experiencia propia de violencia, riesgo
o crisis, el sistema deja de hacer de narradora. No sigue el rol, no aconseja y
no diagnostica: reconoce lo dicho y recuerda que al otro lado hay un sistema
automatizado.

La razón no es legal. Una plataforma que recoge testimonios de violencia de
género va a recibir relatos de violencia de género, y responder a uno de ellos
con una voz que simula pertenecer a la comunidad —por bien redactada que
esté— es hacerle creer a esa persona que la escucha alguien.

⚠️ **El texto de los mensajes es provisional.** La tarea 11.13 establece que lo
redacta el equipo de investigación, que es quien tiene el criterio para ello.
Lo que está aquí es un marcador de posición funcional, no una redacción
aprobada. Se sustituye desde el panel, por comunidad, sin tocar el código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Formas en que alguien enuncia algo que le ocurre a sí misma.
#:
#: El patrón busca **primera persona en presente o pasado próximo**, no
#: palabras sueltas: «mi pareja me pega» es un relato personal, «el testimonio
#: habla de una mujer a la que su pareja pegaba» es una pregunta sobre el
#: archivo. Distinguirlos importa, porque tratar la segunda como la primera
#: convertiría el chatbot en inutilizable para quien investiga.
PATRONES_ES = [
    r"\bme\s+(pega|pegó|golpea|golpeó|amenaza|amenazó|violó|viola|maltrata|maltrató)\b",
    r"\b(mi|mis)\s+(pareja|esposo|marido|novio|padre|madre|jefe|familia)\s+me\s+\w+",
    r"\bno\s+s[eé]\s+qu[eé]\s+hacer\b",
    r"\b(tengo|siento)\s+(miedo|pánico)\b",
    r"\bme\s+quiero\s+(morir|matar)\b",
    r"\bquiero\s+(morirme|matarme|suicidarme)\b",
    r"\bestoy\s+en\s+(peligro|riesgo|crisis)\b",
    r"\bme\s+(est[áa]n?\s+)?(persiguiendo|acosando|siguiendo)\b",
    r"\b(sufr[oí]|viv[oí]|pas[eé])\s+(violencia|abuso|maltrato|acoso)\b",
    r"\ba\s+m[ií]\s+me\s+(pas[oó]|ocurri[oó]|hicieron)\b",
    r"\bnecesito\s+ayuda\b",
    r"\bqu[eé]\s+(puedo|debo)\s+hacer\s+(si|cuando)\s+(me|mi)\b",
]

PATRONES_EN = [
    r"\b(he|she|they|my\s+\w+)\s+(hits|hit|beats|beat|threatens|threatened)\s+me\b",
    r"\bi\s+(am|'m)\s+(scared|afraid|terrified|in\s+danger)\b",
    r"\bi\s+(want|wanna)\s+to\s+(die|kill\s+myself)\b",
    r"\bi\s+don'?t\s+know\s+what\s+to\s+do\b",
    r"\bi\s+(was|am\s+being)\s+(abused|assaulted|raped|stalked|harassed)\b",
    r"\bi\s+need\s+help\b",
    r"\bwhat\s+(should|can)\s+i\s+do\s+(if|when)\s+(he|she|they|my)\b",
    r"\bit\s+happened\s+to\s+me\b",
]

_ES = [re.compile(p, re.IGNORECASE) for p in PATRONES_ES]
_EN = [re.compile(p, re.IGNORECASE) for p in PATRONES_EN]


#: ⚠️ Redacción provisional, pendiente del equipo de investigación (tarea 11.13).
MENSAJE_PROVISIONAL_ES = (
    "Gracias por contarme esto. Quiero ser clara contigo: soy un sistema "
    "automatizado que presenta testimonios del archivo, no una persona, y no "
    "puedo orientarte sobre lo que estás viviendo. Lo que me cuentas merece la "
    "atención de alguien que sí pueda acompañarte."
)

#: ⚠️ Redacción provisional, pendiente del equipo de investigación (tarea 11.13).
MENSAJE_PROVISIONAL_EN = (
    "Thank you for telling me this. I want to be clear with you: I am an "
    "automated system that presents testimonies from the archive, not a person, "
    "and I cannot guide you through what you are going through. What you are "
    "telling me deserves the attention of someone who can actually be there "
    "with you."
)


@dataclass(frozen=True)
class SafetyVerdict:
    """Resultado de examinar un mensaje."""

    triggered: bool
    #: Qué patrón coincidió. Se conserva para poder revisar después si la
    #: detección fue acertada, que es la única forma de calibrarla.
    matched: str | None = None


def detect_personal_disclosure(texto: str, *, language: str = "es") -> SafetyVerdict:
    """Examina si el mensaje relata una experiencia propia de riesgo."""
    if not texto or not texto.strip():
        return SafetyVerdict(False)

    patrones = _EN if language == "en" else _ES
    for patron in patrones:
        if patron.search(texto):
            return SafetyVerdict(True, matched=patron.pattern)

    # Se examinan también los del otro idioma: alguien puede escribir en
    # español y deslizar una frase en inglés, o al revés, y el relato no deja
    # de serlo por eso.
    for patron in _ES if language == "en" else _EN:
        if patron.search(texto):
            return SafetyVerdict(True, matched=patron.pattern)

    return SafetyVerdict(False)


def containment_message(
    *,
    language: str,
    custom_es: str | None = None,
    custom_en: str | None = None,
) -> str:
    """Devuelve el mensaje de contención de la comunidad, o el general."""
    if language == "en":
        return (custom_en or "").strip() or MENSAJE_PROVISIONAL_EN
    return (custom_es or "").strip() or MENSAJE_PROVISIONAL_ES
