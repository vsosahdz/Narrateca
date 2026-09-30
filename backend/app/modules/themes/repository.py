"""Acceso a datos de temas.

El repositorio solo sabe leer y escribir. No contiene reglas de negocio: esas
viven en el servicio.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.themes.models import Theme


class ThemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, *, only_active: bool = False) -> list[Theme]:
        stmt = select(Theme).order_by(Theme.position, Theme.slug)
        if only_active:
            stmt = stmt.where(Theme.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, theme_id: uuid.UUID) -> Theme | None:
        return await self.session.get(Theme, theme_id)

    async def get_by_slug(self, slug: str) -> Theme | None:
        result = await self.session.execute(select(Theme).where(Theme.slug == slug))
        return result.scalar_one_or_none()

    async def add(self, theme: Theme) -> Theme:
        self.session.add(theme)
        await self.session.flush()
        return theme

    async def delete(self, theme: Theme) -> None:
        await self.session.delete(theme)
        await self.session.flush()
