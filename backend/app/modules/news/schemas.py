"""Esquemas de la sección de noticias."""

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.content.models import ContentItem, ContentType


class NewsKind(enum.StrEnum):
    """Origen de una pieza de la sección de noticias.

    La distinción es visible en el sitio a propósito: quien lee debe poder saber
    si está ante una nota del equipo de investigación o ante el resumen de algo
    publicado por un medio externo.
    """

    OWN = "own"
    CURATED = "curated"


class NewsItemRead(BaseModel):
    id: uuid.UUID
    theme_slug: str
    kind: NewsKind
    slug: str
    title: str
    #: Para una nota propia, su entrada. Para un enlace curado, el resumen
    #: redactado por el equipo, que siempre es obligatorio.
    summary: str | None
    #: Nombre del medio, solo para enlaces curados.
    source_name: str | None
    #: Dirección del artículo original, solo para enlaces curados.
    external_url: str | None
    media_key: str | None
    alt_text: str | None
    published_at: datetime | None

    @classmethod
    def from_item(cls, item: ContentItem) -> "NewsItemRead":
        kind = NewsKind.CURATED if item.type is ContentType.CURATED_LINK else NewsKind.OWN
        return cls(
            id=item.id,
            theme_slug=item.theme.slug,
            kind=kind,
            slug=item.slug,
            title=item.title,
            summary=item.summary,
            # El nombre del medio y la dirección externa solo tienen sentido en
            # un enlace curado; en una nota propia se omiten aunque el registro
            # los tuviera por error.
            source_name=item.source_name if kind is NewsKind.CURATED else None,
            external_url=item.external_url if kind is NewsKind.CURATED else None,
            media_key=item.media_key,
            alt_text=item.alt_text,
            published_at=item.published_at,
        )
