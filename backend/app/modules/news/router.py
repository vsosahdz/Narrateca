"""Endpoints de la sección de noticias.

Las noticias no tienen entidad propia: son una **vista** sobre el catálogo de
contenido, filtrada a los tipos `news_post` (notas del equipo) y `curated_link`
(enlaces a medios externos con resumen propio).

Modelarlas como entidad aparte habría duplicado el gestor de contenidos, la
autorización por tema y las reglas de consentimiento.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.content.models import ContentType, PublicationStatus
from app.modules.content.repository import ContentRepository
from app.modules.news.schemas import NewsItemRead

router = APIRouter(prefix="/news", tags=["Noticias"])

#: Tipos que componen la sección de noticias.
NEWS_TYPES = (ContentType.NEWS_POST, ContentType.CURATED_LINK)


@router.get(
    "",
    response_model=list[NewsItemRead],
    summary="Listar noticias publicadas",
    description=(
        "Devuelve notas redactadas por el equipo y enlaces curados a medios externos, "
        "de la más reciente a la más antigua. El campo `kind` distingue el origen de "
        "cada pieza. No se recolecta ni clasifica nada de forma automática: toda "
        "entrada proviene de una acción explícita de un editor."
    ),
)
async def list_news(
    theme: str | None = Query(default=None, description="Identificador del tema."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[NewsItemRead]:
    items = await ContentRepository(session).list_items(
        theme_slug=theme,
        content_types=NEWS_TYPES,
        status=PublicationStatus.PUBLISHED,
        limit=limit,
        offset=offset,
    )
    return [NewsItemRead.from_item(item) for item in items]
