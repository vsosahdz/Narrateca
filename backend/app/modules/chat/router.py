"""Endpoints del chatbot.

El router traduce entre HTTP y el servicio. No decide nada sobre anclaje,
contención ni consentimiento: todo eso vive en `service.py`, que es también
donde se puede verificar.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.dependencies import get_optional_account
from app.modules.admin.models import Account
from app.modules.chat.llm import LanguageModel, get_language_model
from app.modules.chat.schemas import ChatRequest, ChatResponse, PersonaRead
from app.modules.chat.service import ChatService
from app.modules.rag.embeddings import EmbeddingModel, get_embedding_model

router = APIRouter(prefix="/chat", tags=["Chatbot"])


def get_service(
    session: AsyncSession = Depends(get_session),
    model: LanguageModel = Depends(get_language_model),
    embedder: EmbeddingModel = Depends(get_embedding_model),
) -> ChatService:
    return ChatService(session, model=model, embedder=embedder)


@router.get(
    "/personas",
    response_model=list[PersonaRead],
    summary="Listar las narradoras y su disponibilidad",
    description=(
        "Devuelve **siempre las cuatro comunidades**, en cualquier estado. El "
        "selector público debe mostrar las que aún no están disponibles y "
        "señalarlo, no esconderlas.\n\n"
        "No incluye el prompt de sistema: es el instrumento de trabajo del equipo "
        "y exponerlo facilitaría eludirlo."
    ),
)
async def list_personas(service: ChatService = Depends(get_service)) -> list[PersonaRead]:
    personas = await service.list_personas()
    return [PersonaRead.model_validate(p) for p in personas]


@router.post(
    "/{theme_slug}",
    response_model=ChatResponse,
    summary="Conversar con la narradora de una comunidad",
    description=(
        "Devuelve la respuesta completa. Para la interfaz se prefiere "
        "`/chat/{theme_slug}/stream`, que transmite a medida que se genera.\n\n"
        "La respuesta se apoya exclusivamente en fragmentos recuperados del corpus "
        "de esa comunidad. Si la recuperación no encuentra material, se declara y "
        "**no se consulta al modelo de lenguaje**."
    ),
)
async def chat(
    theme_slug: str,
    payload: ChatRequest,
    service: ChatService = Depends(get_service),
    account: Account | None = Depends(get_optional_account),
) -> ChatResponse:
    turno = await service.respond(
        theme_slug=theme_slug,
        message=payload.message,
        is_staff=account is not None,
        language=payload.language,
        conversation_id=payload.conversation_id,
    )
    return ChatResponse(
        conversation_id=turno.conversation_id,
        reply=turno.reply,
        language=turno.language,
        citations=turno.citations,
        no_material_reason=turno.no_material_reason,
        contained=turno.contained,
    )


def _sse(evento: str, dato: object) -> str:
    """Formatea un evento con el formato de «eventos enviados por el servidor».

    Se usa SSE y no un socket web porque el flujo es de ida: el servidor emite
    y el cliente escucha. Un socket añadiría una conexión bidireccional que
    nadie necesita, con su reconexión y su estado.
    """
    return f"event: {evento}\ndata: {json.dumps(dato, ensure_ascii=False)}\n\n"


@router.post(
    "/{theme_slug}/stream",
    summary="Conversar con transmisión progresiva",
    description=(
        "Transmite la respuesta a medida que se genera, con el formato de eventos "
        "enviados por el servidor (`text/event-stream`).\n\n"
        "Eventos: `meta` con el identificador de conversación y el idioma; `delta` "
        "con cada trozo de texto; `citations` con las citas y sus enlaces, al "
        "terminar; `error` si el proveedor falla a mitad; `done` al cerrar."
    ),
    response_description="Flujo de eventos `text/event-stream`.",
)
async def chat_stream(
    theme_slug: str,
    payload: ChatRequest,
    service: ChatService = Depends(get_service),
    account: Account | None = Depends(get_optional_account),
) -> StreamingResponse:
    async def eventos() -> AsyncIterator[str]:
        async for tipo, dato in service.stream(
            theme_slug=theme_slug,
            message=payload.message,
            is_staff=account is not None,
            language=payload.language,
            conversation_id=payload.conversation_id,
        ):
            yield _sse(tipo, dato)

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Sin esto, un proxy intermedio puede acumular la respuesta y
            # entregarla de golpe, que es justo lo contrario de transmitir.
            "X-Accel-Buffering": "no",
        },
    )
