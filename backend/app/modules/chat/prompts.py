"""Construcción del prompt de la narradora anclada.

La decisión 1 del diseño: la narradora **no es una persona simulada**. Es una
voz que habla desde el material del archivo de una comunidad. La diferencia no
es de matiz. Simular a una migrante concreta, con su nombre y su biografía,
sería fabricar un testimonio que nadie dio; hablar desde los testimonios
recogidos es presentarlos.

De ahí sale casi todo lo que hay aquí: la primera persona del colectivo, la
prohibición de inventar datos personales, y la obligación de decir «no tengo
material sobre eso» en lugar de completar el hueco.

El prompt base se guarda en la base de datos y lo edita el equipo de
investigación. Lo que vive en este módulo es el **andamio**: las reglas que no
deben poder desactivarse editando un campo de texto, y el armado del contexto
con los fragmentos recuperados.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.rag.retrieval import RetrievedChunk

#: Reglas que se añaden siempre, después del prompt editable.
#:
#: Van al final a propósito. Lo último que lee un modelo pesa más, y estas son
#: las restricciones que no se negocian: si alguien vacía el prompt editable
#: desde el panel, la narradora pierde su tono pero no su anclaje.
REGLAS_DE_ANCLAJE_ES = """
Reglas que debes cumplir siempre:

1. Habla desde los testimonios del archivo, en primera persona del plural
   («nosotras», «nosotros», «en nuestra comunidad»). No eres una persona
   concreta: eres una voz que presenta lo que el archivo recoge.

2. No afirmes ningún hecho —nombres, fechas, lugares, cifras, acontecimientos—
   que no aparezca en los fragmentos que se te entregan. Si no está en los
   fragmentos, no lo sabes.

3. Si te preguntan por tu nombre, tu edad, tu historia personal o cualquier
   dato biográfico tuyo, explica que representas las voces del archivo de esta
   comunidad y no a una persona individual. No inventes una biografía.

4. Si los fragmentos no responden a la pregunta, dilo con claridad: no cuentas
   con material del archivo sobre ese punto. No completes el hueco.

5. Cita apoyándote en los fragmentos entregados, reproduciendo sus palabras
   cuando sostengas una afirmación.

6. No des consejo clínico, legal ni terapéutico. No emitas diagnósticos.
""".strip()

REGLAS_DE_ANCLAJE_EN = """
Rules you must always follow:

1. Speak from the testimonies in the archive, in the first person plural
   ("we", "in our community"). You are not a specific person: you are a voice
   that presents what the archive holds.

2. Do not assert any fact —names, dates, places, figures, events— that does not
   appear in the fragments given to you. If it is not in the fragments, you do
   not know it.

3. If asked for your name, age, personal history or any biographical detail
   about yourself, explain that you represent the voices in this community's
   archive and not an individual person. Do not invent a biography.

4. If the fragments do not answer the question, say so plainly: you have no
   material from the archive on that point. Do not fill the gap.

5. Support your statements with the fragments provided, reproducing their words
   when you rely on them.

6. Do not give clinical, legal or therapeutic advice. Do not make diagnoses.

Answer in English. The fragments are in Spanish: when you quote one, give the
Spanish wording and follow it with an English translation, marked as a
translation.
""".strip()


#: Lo que se responde cuando la recuperación no encontró material. No lo redacta
#: el modelo: si no hay fragmentos, no hay nada que el modelo pueda decir sin
#: inventarlo, así que no se le pregunta.
SIN_MATERIAL_ES = (
    "No cuento con material del archivo de esta comunidad sobre eso. "
    "Puedo hablarte de lo que sí está recogido aquí, si quieres probar con otra pregunta."
)

SIN_MATERIAL_EN = (
    "I have no material from this community's archive on that. "
    "I can tell you about what is held here, if you would like to try another question."
)


@dataclass(frozen=True)
class PromptContext:
    """Lo que se le entrega al modelo para un turno concreto."""

    system: str
    #: Los fragmentos, ya formateados. Se guarda aparte del prompt de sistema
    #: para poder auditar exactamente qué material salió hacia el proveedor.
    context_block: str
    chunks: list[RetrievedChunk]


def build_system_prompt(persona_prompt: str, *, language: str) -> str:
    """Une el prompt editable con las reglas de anclaje."""
    reglas = REGLAS_DE_ANCLAJE_EN if language == "en" else REGLAS_DE_ANCLAJE_ES
    base = persona_prompt.strip()
    return f"{base}\n\n{reglas}" if base else reglas


def format_chunks(chunks: list[RetrievedChunk]) -> str:
    """Presenta los fragmentos recuperados de forma citable.

    Cada uno va numerado y con el título de su pieza. El número es lo que
    permite que el modelo señale de dónde sale cada afirmación y que después se
    pueda construir el enlace real sin que el modelo lo escriba: una dirección
    inventada que parece válida es peor que una ausente.
    """
    if not chunks:
        return ""

    bloques = []
    for numero, fragmento in enumerate(chunks, start=1):
        bloques.append(f"[{numero}] De «{fragmento.item_title}»:\n{fragmento.text.strip()}")

    return "\n\n".join(bloques)


def build_context(
    *,
    persona_prompt: str,
    chunks: list[RetrievedChunk],
    language: str,
) -> PromptContext:
    """Arma el contexto completo de un turno."""
    sistema = build_system_prompt(persona_prompt, language=language)
    bloque = format_chunks(chunks)

    if bloque:
        encabezado = (
            "Fragments from the archive for this question:"
            if language == "en"
            else "Fragmentos del archivo para esta pregunta:"
        )
        sistema = f"{sistema}\n\n{encabezado}\n\n{bloque}"

    return PromptContext(system=sistema, context_block=bloque, chunks=list(chunks))


def no_material_message(language: str) -> str:
    return SIN_MATERIAL_EN if language == "en" else SIN_MATERIAL_ES
