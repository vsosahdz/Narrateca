"""Endpoints HTTP de temas.

En la equivalencia MVC del proyecto, el router es el *controlador*: valida la
entrada, delega en el servicio y traduce errores de dominio a códigos HTTP.
No contiene reglas de negocio.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.themes.schemas import ThemeCreate, ThemeRead, ThemeUpdate
from app.modules.themes.service import ThemeService

router = APIRouter(prefix="/themes", tags=["Temas"])


def get_service(session: AsyncSession = Depends(get_session)) -> ThemeService:
    return ThemeService(session)


@router.get(
    "",
    response_model=list[ThemeRead],
    summary="Listar temas",
    description=(
        "Devuelve las comunidades registradas en la plataforma. Los temas son datos, "
        "no valores codificados: dar de alta una comunidad nueva no requiere cambios "
        "de código."
    ),
)
async def list_themes(
    only_active: bool = True,
    service: ThemeService = Depends(get_service),
) -> list[ThemeRead]:
    themes = await service.list_themes(only_active=only_active)
    return [ThemeRead.model_validate(theme) for theme in themes]


@router.get(
    "/{slug}",
    response_model=ThemeRead,
    summary="Obtener un tema por su identificador",
)
async def get_theme(slug: str, service: ThemeService = Depends(get_service)) -> ThemeRead:
    return ThemeRead.model_validate(await service.get_by_slug(slug))


@router.post(
    "",
    response_model=ThemeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un tema",
)
async def create_theme(
    payload: ThemeCreate,
    service: ThemeService = Depends(get_service),
) -> ThemeRead:
    return ThemeRead.model_validate(await service.create(payload))


@router.patch(
    "/{theme_id}",
    response_model=ThemeRead,
    summary="Actualizar un tema",
)
async def update_theme(
    theme_id: uuid.UUID,
    payload: ThemeUpdate,
    service: ThemeService = Depends(get_service),
) -> ThemeRead:
    return ThemeRead.model_validate(await service.update(theme_id, payload))


@router.delete(
    "/{theme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un tema",
)
async def delete_theme(
    theme_id: uuid.UUID,
    service: ThemeService = Depends(get_service),
) -> None:
    await service.delete(theme_id)
