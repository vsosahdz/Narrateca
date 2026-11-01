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

    async def published_titles(self, theme_slug: str, *, limit: int = 8) -> list[str]:
        """Títulos de las piezas publicadas e indexables de una comunidad.

        Alimenta las preguntas sugeridas cuando el equipo aún no ha escrito las
        suyas. Se filtra por consentimiento además de por publicación: sugerir
        una pregunta sobre una pieza que el chatbot no puede usar llevaría
        directo a «no cuento con material».
        """
        from app.modules.content.models import INDEXABLE_SCOPES, ContentItem, PublicationStatus
        from app.modules.themes.models import Theme

        result = await self.session.execute(
            select(ContentItem.title)
            .join(Theme, Theme.id == ContentItem.theme_id)
            .where(
                Theme.slug == theme_slug,
                ContentItem.status == PublicationStatus.PUBLISHED,
                ContentItem.consent_scope.in_(list(INDEXABLE_SCOPES)),
            )
            .order_by(ContentItem.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, persona: PersonaConfig) -> PersonaConfig:
        self.session.add(persona)
        await self.session.flush()
        return persona
