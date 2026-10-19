"""Orquestación de una conversación.

El orden de los pasos no es casual, y es donde viven las garantías del
proyecto:

1. Se resuelve la narradora y si quien pregunta puede hablar con ella.
2. Se examina si el mensaje es un relato personal de riesgo. **Antes de
   recuperar y antes de llamar al modelo**: si alguien está contando algo que
   le ocurre, no hay nada que buscar en el archivo ni nada que un modelo deba
   redactar.
3. Se recupera del corpus de esa comunidad, filtrado por consentimiento.
4. Si no hay material, se responde que no lo hay. **Sin llamar al modelo**: si
   no hay fragmentos, cualquier cosa que el modelo escriba estaría inventada,
   así que no se le pregunta.
5. Solo entonces se arma el prompt y se transmite.

Los pasos 2 y 4 cortan antes de llegar al proveedor. Eso no es una
optimización: es la diferencia entre un sistema que puede inventar y uno que
no tiene ocasión de hacerlo.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError, PermissionDeniedError
from app.modules.chat import prompts, safety
from app.modules.chat.language import detect_language
from app.modules.chat.llm import GenerationError, LanguageModel, Message
from app.modules.chat.models import ActivationState, PersonaConfig
from app.modules.chat.repository import PersonaRepository
from app.modules.chat.schemas import Citation
from app.modules.rag.embeddings import EmbeddingModel
from app.modules.rag.retrieval import HybridRetriever, RetrievedChunk

#: Mensaje para una comunidad anunciada pero todavía cerrada.
PROXIMAMENTE_ES = (
    "Esta comunidad estará disponible próximamente. Su material se está preparando y revisando."
)
PROXIMAMENTE_EN = (
    "This community is not yet available for conversation. "
    "Its material is still being prepared and reviewed."
)


class PersonaNotAvailableError(PermissionDeniedError):
    """La narradora existe pero no acepta esta conversación."""


@dataclass
class ChatTurn:
    """Resultado de un turno, ya resuelto."""

    conversation_id: uuid.UUID
    reply: str
    language: str
    citations: list[Citation] = field(default_factory=list)
    no_material_reason: str | None = None
    contained: bool = False

    #: Lo que se envió al proveedor, para poder auditarlo. `None` cuando no se
    #: llegó a llamar —contención o ausencia de material—, que es justamente lo
    #: que interesa poder distinguir.
    sent_messages: list[Message] | None = None


@dataclass
class Prepared:
    """Lo resuelto antes de llamar al proveedor.

    `closed` lleva el turno ya terminado cuando no hay que llamar al modelo
    —contención o ausencia de material—; en caso contrario viene a `None` y lo
    que vale son `chunks` y `messages`.

    Es una clase y no una tupla porque el identificador de conversación tiene
    que sobrevivir a este paso: generarlo aquí y volver a generarlo después
    daba una conversación distinta en cada turno.
    """

    conversation_id: uuid.UUID
    persona: PersonaConfig
    language: str
    closed: ChatTurn | None = None
    chunks: list[RetrievedChunk] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)


def public_url(theme_slug: str, item_slug: str, language: str) -> str:
    """Ruta pública de una pieza en el sitio.

    La construye el servidor a partir de los slugs reales. El modelo de
    lenguaje nunca escribe direcciones: una que parezca válida y no lo sea es
    peor que ninguna, porque invita a seguirla.
    """
    locale = "en" if language == "en" else "es"
    return f"/{locale}/{theme_slug}/{item_slug}"


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        model: LanguageModel,
        embedder: EmbeddingModel,
    ) -> None:
        self.session = session
        self.repo = PersonaRepository(session)
        self.model = model
        self.retriever = HybridRetriever(session, embedder)

    # --- Personas -----------------------------------------------------------

    async def list_personas(self) -> list[PersonaConfig]:
        return await self.repo.list_all()

    async def get_persona(self, theme_slug: str) -> PersonaConfig:
        persona = await self.repo.get_by_theme(theme_slug)
        if persona is None:
            raise NotFoundError(f"No hay una narradora configurada para '{theme_slug}'.")
        return persona

    # --- Conversación -------------------------------------------------------

    async def prepare(
        self,
        *,
        theme_slug: str,
        message: str,
        is_staff: bool,
        language: str | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> Prepared:
        """Resuelve todo lo previo a llamar al modelo.

        Se separa de la transmisión para que el camino con transmisión
        progresiva y el sin ella compartan exactamente las mismas decisiones,
        en lugar de reimplementarlas y divergir.
        """
        persona = await self.get_persona(theme_slug)

        if not persona.accepts(is_staff=is_staff):
            idioma = language or detect_language(message)
            if persona.activation is ActivationState.COMING_SOON:
                raise PersonaNotAvailableError(
                    PROXIMAMENTE_EN if idioma == "en" else PROXIMAMENTE_ES
                )
            raise PersonaNotAvailableError(
                "This community is not available."
                if idioma == "en"
                else "Esta comunidad no está disponible."
            )

        idioma = language or detect_language(message)
        conversacion = conversation_id or uuid.uuid4()

        # Contención: antes de recuperar y antes del modelo.
        if persona.safety_enabled:
            veredicto = safety.detect_personal_disclosure(message, language=idioma)
            if veredicto.triggered:
                return Prepared(
                    conversation_id=conversacion,
                    persona=persona,
                    language=idioma,
                    closed=ChatTurn(
                        conversation_id=conversacion,
                        reply=safety.containment_message(
                            language=idioma,
                            custom_es=persona.safety_message_es,
                            custom_en=persona.safety_message_en,
                        ),
                        language=idioma,
                        contained=True,
                    ),
                )

        resultado = await self.retriever.retrieve(
            theme_slug=persona.corpus_slug,
            query=message,
            top_k=settings.rag_top_k,
        )

        if not resultado.has_material:
            return Prepared(
                conversation_id=conversacion,
                persona=persona,
                language=idioma,
                closed=ChatTurn(
                    conversation_id=conversacion,
                    reply=prompts.no_material_message(idioma),
                    language=idioma,
                    no_material_reason=resultado.rejection_reason,
                ),
            )

        contexto = prompts.build_context(
            persona_prompt=persona.system_prompt,
            chunks=resultado.chunks,
            language=idioma,
        )

        # Lo único que sale hacia el proveedor: prompt de sistema con los
        # fragmentos recuperados, y el mensaje de la persona. El corpus
        # completo no se envía nunca, y los fragmentos ya vienen filtrados por
        # consentimiento desde la recuperación.
        mensajes = [
            Message(role="system", content=contexto.system),
            Message(role="user", content=message),
        ]

        return Prepared(
            conversation_id=conversacion,
            persona=persona,
            language=idioma,
            chunks=resultado.chunks,
            messages=mensajes,
        )

    def build_citations(self, chunks: list[RetrievedChunk], language: str) -> list[Citation]:
        """Convierte los fragmentos recuperados en citas con enlace real."""
        return [
            Citation(
                marker=numero,
                text=fragmento.text.strip(),
                item_title=fragmento.item_title,
                item_slug=fragmento.item_slug,
                theme_slug=fragmento.theme_slug,
                url=public_url(fragmento.theme_slug, fragmento.item_slug, language),
            )
            for numero, fragmento in enumerate(chunks, start=1)
        ]

    async def respond(
        self,
        *,
        theme_slug: str,
        message: str,
        is_staff: bool = False,
        language: str | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> ChatTurn:
        """Un turno completo, con la respuesta ya acumulada."""
        listo = await self.prepare(
            theme_slug=theme_slug,
            message=message,
            is_staff=is_staff,
            language=language,
            conversation_id=conversation_id,
        )
        if listo.closed is not None:
            return listo.closed

        texto = await self.model.generate(listo.messages)

        return ChatTurn(
            conversation_id=listo.conversation_id,
            reply=texto.strip(),
            language=listo.language,
            citations=self.build_citations(listo.chunks, listo.language),
            sent_messages=listo.messages,
        )

    async def stream(
        self,
        *,
        theme_slug: str,
        message: str,
        is_staff: bool = False,
        language: str | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> AsyncIterator[tuple[str, object]]:
        """Produce `(tipo, dato)` a medida que la respuesta se genera.

        Los tipos son `"meta"`, `"delta"`, `"citations"`, `"error"` y `"done"`.
        El router los traduce a eventos de transporte; el servicio sigue sin
        saber nada de HTTP.
        """
        listo = await self.prepare(
            theme_slug=theme_slug,
            message=message,
            is_staff=is_staff,
            language=language,
            conversation_id=conversation_id,
        )

        if listo.closed is not None:
            cerrado = listo.closed
            yield (
                "meta",
                {
                    "conversation_id": str(cerrado.conversation_id),
                    "language": cerrado.language,
                    "contained": cerrado.contained,
                    "no_material_reason": cerrado.no_material_reason,
                },
            )
            yield "delta", cerrado.reply
            yield "done", {}
            return

        yield (
            "meta",
            {
                "conversation_id": str(listo.conversation_id),
                "language": listo.language,
                "contained": False,
                "no_material_reason": None,
            },
        )

        try:
            async for trozo in self.model.stream(listo.messages):
                yield "delta", trozo
        except GenerationError as error:
            # El fallo del proveedor llega como evento y no como excepción: a
            # estas alturas la respuesta ya empezó a transmitirse, y el código
            # de estado HTTP se envió hace rato.
            yield "error", {"detail": str(error)}
            return

        # Las citas van al final, cuando el texto ya está completo: así la
        # interfaz puede enlazarlas con los marcadores que aparecieron.
        citas = self.build_citations(listo.chunks, listo.language)
        yield "citations", [c.model_dump() for c in citas]
        yield "done", {}
