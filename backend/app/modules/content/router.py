"""Endpoints del catálogo de contenido.

Los endpoints públicos devuelven `PublicContentRead`, que no tiene campo para el
nombre real de la persona testimoniante. Los de administración devuelven
`AdminContentRead` y quedarán protegidos por sesión y rol en el grupo 6.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.dependencies import get_current_account
from app.modules.admin.models import Account
from app.modules.content.indexing import IndexSynchronizer, get_index_synchronizer
from app.modules.content.models import ConsentScope, ContentItem, ContentType
from app.modules.content.schemas import (
    AdminContentRead,
    ContentCreate,
    ContentUpdate,
    PublicContentRead,
)
from app.modules.content.service import ContentService

router = APIRouter(prefix="/content", tags=["Contenido"])
admin_router = APIRouter(prefix="/admin/content", tags=["Administración"])


def get_service(
    session: AsyncSession = Depends(get_session),
    indexer: IndexSynchronizer = Depends(get_index_synchronizer),
) -> ContentService:
    """Servicio sin cuenta, para las lecturas del sitio público."""
    return ContentService(session, indexer)


def get_authed_service(
    session: AsyncSession = Depends(get_session),
    indexer: IndexSynchronizer = Depends(get_index_synchronizer),
    account: Account = Depends(get_current_account),
) -> ContentService:
    """Servicio con la cuenta de la sesión.

    Depender de `get_current_account` hace que toda la sección de administración
    exija sesión activa: sin cookie válida, la petición nunca llega al manejador.
    """
    return ContentService(session, indexer, actor=account)


def _to_public(item: ContentItem) -> PublicContentRead:
    return PublicContentRead(
        id=item.id,
        theme_slug=item.theme.slug,
        type=item.type,
        slug=item.slug,
        title=item.title,
        summary=item.summary,
        body=item.body,
        display_name=item.display_name,
        attribution=item.attribution,
        sensitivity=item.sensitivity,
        media_key=item.media_key,
        media_mime=item.media_mime,
        external_url=item.external_url,
        source_name=item.source_name,
        alt_text=item.alt_text,
        recorded_on=item.recorded_on,
        published_at=item.published_at,
    )


def _to_admin(item: ContentItem) -> AdminContentRead:
    return AdminContentRead(
        **_to_public(item).model_dump(),
        status=item.status,
        consent_scope=item.consent_scope,
        person_name=item.person_name,
        pseudonym=item.pseudonym,
        is_indexable=item.is_indexable,
        source_ref=item.source_ref,
        imported_at=item.imported_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# --- Público ----------------------------------------------------------------


@router.get(
    "",
    response_model=list[PublicContentRead],
    summary="Listar contenido publicado",
    description=(
        "Devuelve únicamente piezas en estado publicado. El contenido en borrador o "
        "retirado no es visible por esta vía. El nombre real de la persona "
        "testimoniante nunca se incluye: solo el nombre a mostrar según su atribución."
    ),
)
async def list_content(
    theme: str | None = Query(default=None, description="Identificador del tema."),
    type: ContentType | None = Query(default=None, description="Tipo de contenido."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ContentService = Depends(get_service),
) -> list[PublicContentRead]:
    items = await service.list_public(
        theme_slug=theme, content_type=type, limit=limit, offset=offset
    )
    return [_to_public(item) for item in items]


@router.get(
    "/{theme_slug}/{slug}",
    response_model=PublicContentRead,
    summary="Obtener una pieza publicada por su dirección estable",
)
async def get_content(
    theme_slug: str,
    slug: str,
    service: ContentService = Depends(get_service),
) -> PublicContentRead:
    return _to_public(await service.get_public(theme_slug, slug))


# --- Administración ---------------------------------------------------------


@admin_router.get(
    "",
    response_model=list[AdminContentRead],
    summary="Listar contenido para administración",
)
async def admin_list_content(
    theme: str | None = Query(default=None),
    type: ContentType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ContentService = Depends(get_authed_service),
) -> list[AdminContentRead]:
    items = await service.repo.list_items(
        theme_slug=theme, content_type=type, limit=limit, offset=offset
    )
    return [_to_admin(item) for item in items]


@admin_router.get(
    "/{item_id}",
    response_model=AdminContentRead,
    summary="Obtener una pieza para edición",
    description=(
        "Incluye el estado de publicación, el alcance de consentimiento y el nombre "
        "real de la persona testimoniante, que el sitio público nunca expone."
    ),
)
async def admin_get_content(
    item_id: uuid.UUID,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.get_by_id(item_id))


@admin_router.post(
    "",
    response_model=AdminContentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una pieza de contenido",
    description=(
        "La pieza se crea en estado borrador. Si no se especifica `consent_scope`, "
        "se asigna `no_ai`: incorporar contenido al chatbot es siempre una decisión "
        "explícita."
    ),
)
async def create_content(
    payload: ContentCreate,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.create(payload))


@admin_router.patch(
    "/{item_id}",
    response_model=AdminContentRead,
    summary="Actualizar una pieza de contenido",
)
async def update_content(
    item_id: uuid.UUID,
    payload: ContentUpdate,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.update(item_id, payload))


@admin_router.post(
    "/{item_id}/publish",
    response_model=AdminContentRead,
    summary="Publicar una pieza",
    description=(
        "Verifica los requisitos de publicación. El contenido visual sin texto "
        "alternativo se rechaza; como borrador sí puede guardarse incompleto."
    ),
)
async def publish_content(
    item_id: uuid.UUID,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.publish(item_id))


@admin_router.post(
    "/{item_id}/withdraw",
    response_model=AdminContentRead,
    summary="Retirar una pieza del sitio",
    description="Retira la pieza del sitio público y elimina sus fragmentos del índice.",
)
async def withdraw_content(
    item_id: uuid.UUID,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.withdraw(item_id))


@admin_router.put(
    "/{item_id}/consent",
    response_model=AdminContentRead,
    summary="Cambiar el alcance de consentimiento",
    description=(
        "Cambiar a `no_ai` elimina de inmediato los fragmentos de la pieza del índice "
        "del chatbot, sin afectar su publicación en el sitio."
    ),
)
async def set_consent(
    item_id: uuid.UUID,
    scope: ConsentScope,
    service: ContentService = Depends(get_authed_service),
) -> AdminContentRead:
    return _to_admin(await service.set_consent_scope(item_id, scope))


@admin_router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una pieza",
)
async def delete_content(
    item_id: uuid.UUID,
    service: ContentService = Depends(get_authed_service),
) -> None:
    await service.delete(item_id)
