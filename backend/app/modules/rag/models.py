"""Índice del corpus del chatbot.

Cada fragmento guarda **dos** representaciones del mismo texto: un vector para la
similitud semántica y un `tsvector` en español para la coincidencia léxica. La
recuperación fusiona ambas (ver `design.md`, decisión 17).

La razón es concreta y medida: los modelos e5 producen similitudes altas para
cualquier par de textos, así que una consulta sin relación con el archivo puntúa
casi igual que una relevante. Sin la señal léxica, el chatbot respondería a una
pregunta sobre mole poblano citando el testimonio de una migrante.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base, TimestampMixin
from app.modules.content.models import ContentItem

#: Configuración de búsqueda de texto de PostgreSQL. El corpus está en español;
#: usar la configuración por defecto trataría «testimonios» y «testimonio» como
#: palabras distintas y perdería la mitad de las coincidencias.
TEXT_SEARCH_CONFIG = "spanish"


class ChunkReviewStatus:
    """Estados de revisión de un fragmento indexado.

    Un fragmento entra al índice de inmediato al publicarse la pieza, pero queda
    marcado como pendiente hasta que alguien lo apruebe (`design.md`, decisión 7).
    """

    PENDING = "pending"
    APPROVED = "approved"


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_content_item", "content_item_id"),
        Index("ix_chunks_theme_review", "theme_slug", "review_status"),
        # Índice invertido para la búsqueda léxica. Sin él, cada consulta
        # recorrería el corpus completo.
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
        # HNSW para la búsqueda vectorial: da mejor recuperación que IVFFlat en
        # corpus pequeños y no exige entrenar el índice antes de usarlo, que con
        # un archivo que crece pieza a pieza sería un estorbo.
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    item: Mapped[ContentItem] = relationship(lazy="joined")

    #: Se desnormaliza el tema para poder filtrar sin unir con `content_items`.
    #: La partición por comunidad se aplica en cada consulta, así que conviene
    #: que sea barata.
    theme_slug: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Posición del fragmento dentro de la pieza, para poder reconstruir el
    #: orden y mostrar contexto alrededor de una cita.
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    #: Desplazamientos en el texto original. Permiten resaltar la cita dentro de
    #: la pieza completa en lugar de mostrarla descontextualizada.
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embeddings_dimensions), nullable=False
    )

    #: Columna generada por PostgreSQL a partir de `text`. Al ser generada, no
    #: puede desincronizarse del texto: no hay forma de actualizar uno y olvidar
    #: el otro.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            f"to_tsvector('{TEXT_SEARCH_CONFIG}', coalesce(text, ''))",
            persisted=True,
        ),
    )

    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ChunkReviewStatus.PENDING
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Chunk {self.theme_slug}#{self.ordinal}>"
