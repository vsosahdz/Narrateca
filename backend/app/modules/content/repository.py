"""Acceso a datos del catálogo de contenido."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import (
    ContentItem,
    ContentType,
    PublicationStatus,
)
from app.modules.themes.models import Theme


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self) -> Select[tuple[ContentItem]]:
        return select(ContentItem).join(Theme, ContentItem.theme_id == Theme.id)

    async def list_items(
        self,
        *,
        theme_slug: str | None = None,
        content_type: ContentType | None = None,
        content_types: Sequence[ContentType] | None = None,
        status: PublicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContentItem]:
        stmt = self._base_query()

        if theme_slug is not None:
            stmt = stmt.where(Theme.slug == theme_slug)
        if content_type is not None:
            stmt = stmt.where(ContentItem.type == content_type)
        if content_types is not None:
            stmt = stmt.where(ContentItem.type.in_(list(content_types)))
        if status is not None:
            stmt = stmt.where(ContentItem.status == status)

        stmt = (
            stmt.order_by(
                ContentItem.published_at.desc().nullslast(),
                ContentItem.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_by_id(self, item_id: uuid.UUID) -> ContentItem | None:
        return await self.session.get(ContentItem, item_id)

    async def get_by_theme_and_slug(self, theme_slug: str, slug: str) -> ContentItem | None:
        stmt = self._base_query().where(Theme.slug == theme_slug, ContentItem.slug == slug)
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_source_ref(self, source_ref: str) -> ContentItem | None:
        stmt = select(ContentItem).where(ContentItem.source_ref == source_ref)
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def add(self, item: ContentItem) -> ContentItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item, ["theme"])
        return item

    async def delete(self, item: ContentItem) -> None:
        await self.session.delete(item)
        await self.session.flush()
