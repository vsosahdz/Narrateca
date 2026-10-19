"""Acceso a las configuraciones de persona."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import PersonaConfig


class PersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_theme(self, theme_slug: str) -> PersonaConfig | None:
        result = await self.session.execute(
            select(PersonaConfig).where(PersonaConfig.theme_slug == theme_slug)
        )
        return result.scalar_one_or_none()

    async def get(self, persona_id: uuid.UUID) -> PersonaConfig | None:
        result = await self.session.execute(
            select(PersonaConfig).where(PersonaConfig.id == persona_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[PersonaConfig]:
        """Todas, ordenadas por la posición del tema.

        Se devuelven siempre las cuatro, en cualquier estado: el selector
        público debe mostrar las comunidades que aún no están disponibles y
        decir que llegarán, no esconderlas.
        """
        from app.modules.themes.models import Theme

        result = await self.session.execute(
            select(PersonaConfig)
            .join(Theme, Theme.id == PersonaConfig.theme_id)
            .order_by(Theme.position)
        )
        return list(result.scalars().all())

    async def add(self, persona: PersonaConfig) -> PersonaConfig:
        self.session.add(persona)
        await self.session.flush()
        return persona
