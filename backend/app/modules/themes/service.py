"""Reglas de negocio de temas.

El servicio no conoce HTTP. Recibe y devuelve objetos de dominio, y lanza errores
de `app.core.errors` que el router traduce.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.modules.themes.models import Theme
from app.modules.themes.repository import ThemeRepository
from app.modules.themes.schemas import ThemeCreate, ThemeUpdate


class ThemeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ThemeRepository(session)

    async def list_themes(self, *, only_active: bool = False) -> list[Theme]:
        return await self.repo.list_all(only_active=only_active)

    async def get_by_slug(self, slug: str) -> Theme:
        theme = await self.repo.get_by_slug(slug)
        if theme is None:
            raise NotFoundError(f"No existe el tema '{slug}'.")
        return theme

    async def get_by_id(self, theme_id: uuid.UUID) -> Theme:
        theme = await self.repo.get_by_id(theme_id)
        if theme is None:
            raise NotFoundError("No existe el tema solicitado.")
        return theme

    async def create(self, payload: ThemeCreate) -> Theme:
        if await self.repo.get_by_slug(payload.slug) is not None:
            raise ConflictError(f"Ya existe un tema con el identificador '{payload.slug}'.")
        theme = await self.repo.add(Theme(**payload.model_dump()))
        await self.session.commit()
        return theme

    async def update(self, theme_id: uuid.UUID, payload: ThemeUpdate) -> Theme:
        theme = await self.get_by_id(theme_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(theme, field, value)
        await self.session.commit()
        return theme

    async def delete(self, theme_id: uuid.UUID) -> None:
        theme = await self.get_by_id(theme_id)
        await self.repo.delete(theme)
        await self.session.commit()
