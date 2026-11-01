"""Recepción: orienta hacia la comunidad que tiene material.

Es la quinta voz de la página del chatbot, y la única que **no es una voz**. No
llama al modelo de lenguaje: toma la pregunta, consulta el índice de cada
comunidad abierta y dice en cuáles hay material. Nada más.

La decisión es deliberada. Una recepción conversacional sería un quinto prompt
que redactar, calibrar y vigilar, con su propio riesgo de afirmar cosas que el
archivo no sostiene —y el riesgo sería mayor que en las narradoras, porque
hablaría *sobre* las cuatro comunidades en lugar de desde una—. Un enrutador
determinista hace el mismo trabajo útil y no puede inventar: lo que no esté en
el índice, no lo nombra.

Tampoco habla en primera persona, y no por disciplina de redacción sino porque
no redacta.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import ActivationState, PersonaConfig
from app.modules.chat.repository import PersonaRepository
from app.modules.rag.embeddings import EmbeddingModel
from app.modules.rag.retrieval import HybridRetriever

#: Cuántos fragmentos se piden por comunidad al orientar. Menos que en una
#: conversación: aquí no hay que sostener una respuesta, solo saber si hay algo.
SONDEO = 3


@dataclass
class Orientation:
    """Qué comunidad cubre una pregunta."""

    theme_slug: str
    theme_name_es: str
    theme_name_en: str
    #: Cuántos fragmentos con coincidencia encontró en esa comunidad.
    matches: int
    #: La pieza mejor posicionada, para poder enseñar de qué va.
    best_item_title: str | None = None
    #: Si la narradora de esa comunidad acepta conversación ahora mismo.
    available: bool = True


class ReceptionService:
    def __init__(self, session: AsyncSession, *, embedder: EmbeddingModel) -> None:
        self.session = session
        self.repo = PersonaRepository(session)
        self.retriever = HybridRetriever(session, embedder)

    async def orient(self, pregunta: str, *, is_staff: bool = False) -> list[Orientation]:
        """Comunidades con material sobre la pregunta, de más a menos.

        Se consultan todas las que quien pregunta podría usar, no solo las
        activas: a una cuenta de administración le sirve saber que el material
        está ahí aunque la narradora siga en borrador.
        """
        texto = pregunta.strip()
        if not texto:
            return []

        resultados: list[Orientation] = []

        for persona in await self.repo.list_all():
            if not persona.accepts(is_staff=is_staff):
                # Una comunidad cerrada no se orienta hacia ella: encaminar a
                # una puerta que está cerrada es peor que no mencionarla.
                continue

            encontrado = await self.retriever.retrieve(
                theme_slug=persona.corpus_slug,
                query=texto,
                top_k=SONDEO,
            )
            if not encontrado.has_material:
                continue

            resultados.append(
                Orientation(
                    theme_slug=persona.theme_slug,
                    theme_name_es=persona.theme.name_es,
                    theme_name_en=persona.theme.name_en,
                    matches=len(encontrado.chunks),
                    best_item_title=encontrado.chunks[0].item_title if encontrado.chunks else None,
                    available=persona.activation is ActivationState.ACTIVE,
                )
            )

        resultados.sort(key=lambda o: o.matches, reverse=True)
        return resultados


def derive_suggestions(titles: list[str], *, limit: int = 4) -> list[str]:
    """Preguntas de ejemplo a partir de los títulos de las piezas publicadas.

    Es el respaldo para cuando el equipo todavía no ha escrito las suyas. No
    pretende ser elegante: pretende que la primera pregunta de quien llega
    tenga material detrás, en lugar de estrenarse con un «no cuento con
    material sobre eso».
    """
    preguntas = []
    for titulo in titles[:limit]:
        limpio = titulo.strip().rstrip(".")
        # Un título que ya empieza por «sobre» produciría «¿Qué cuenta el
        # archivo sobre «Sobre el diagnóstico tardío»?».
        if limpio.lower().startswith("sobre "):
            limpio = limpio[6:].strip()
        if not limpio:
            continue
        # Minúscula inicial salvo que empiece por nombre propio, que no
        # sabemos distinguir: se deja el título tal cual entre comillas.
        preguntas.append(f"¿Qué cuenta el archivo sobre «{limpio}»?")
    return preguntas


def suggestions_for(persona: PersonaConfig, titles: list[str]) -> list[str]:
    """Las del equipo si las hay; si no, las derivadas del corpus."""
    propias = [q.strip() for q in (persona.suggested_questions or []) if q and q.strip()]
    return propias or derive_suggestions(titles)
