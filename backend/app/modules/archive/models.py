"""Registro de ingesta del archivo.

Lleva la cuenta de qué documentos del archivo físico ya se incorporaron al
catálogo y cuáles no. Sin este registro, cada ejecución del importador tendría
que adivinar qué es nuevo, y la única forma de evitar duplicados sería no volver
a ejecutarlo nunca.

El registro es **independiente del catálogo** a propósito: un documento puede
estar detectado y no importado (por ejemplo, porque falló o porque el equipo aún
no decide su consentimiento), y esa situación debe ser visible en vez de
desaparecer.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.modules.content.models import ContentType


class DocumentStatus(enum.StrEnum):
    """Situación de un documento del archivo frente al catálogo."""

    #: Detectado en el árbol de archivos, todavía sin importar.
    DISCOVERED = "discovered"
    #: Importado: existe una pieza de contenido que lo representa.
    IMPORTED = "imported"
    #: Importado, pero el archivo cambió en disco desde entonces.
    MODIFIED = "modified"
    #: Estaba registrado y ya no aparece en el árbol de archivos.
    MISSING = "missing"
    #: La importación falló. `error` explica por qué.
    FAILED = "failed"
    #: Deliberadamente fuera del catálogo (material de trabajo, duplicados).
    SKIPPED = "skipped"


class ArchiveDocument(Base, TimestampMixin):
    __tablename__ = "archive_documents"
    __table_args__ = (Index("ix_archive_documents_theme_status", "theme_slug", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Ruta relativa a la raíz del archivo. Es la identidad del documento y lo
    #: que permite que una segunda ejecución reconozca lo ya visto.
    relative_path: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)

    #: Tema deducido de la primera carpeta de la ruta.
    theme_slug: Mapped[str] = mapped_column(String(64), nullable=False)

    #: Tipo deducido de la segunda carpeta o del formato del archivo. Nulo
    #: cuando no se pudo clasificar: eso es información, no un error.
    detected_type: Mapped[ContentType | None] = mapped_column(
        Enum(
            ContentType,
            name="content_type",
            values_callable=lambda members: [m.value for m in members],
            create_type=False,
        )
    )

    #: SHA-256 del contenido. Es lo que distingue un archivo modificado de uno
    #: solo tocado, y lo que permite detectar el mismo material en dos rutas.
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    #: Fecha de modificación en disco. Junto al tamaño evita volver a calcular
    #: el hash de archivos que no cambiaron, que en horas de video es la
    #: diferencia entre un escaneo de segundos y uno de muchos minutos.
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda members: [m.value for m in members],
        ),
        nullable=False,
        default=DocumentStatus.DISCOVERED,
    )

    #: Pieza de contenido que representa a este documento, si se importó.
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL")
    )

    error: Mapped[str | None] = mapped_column(Text)

    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def needs_attention(self) -> bool:
        """Si el documento requiere una decisión del equipo."""
        return self.status in {
            DocumentStatus.DISCOVERED,
            DocumentStatus.MODIFIED,
            DocumentStatus.MISSING,
            DocumentStatus.FAILED,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ArchiveDocument {self.relative_path} ({self.status.value})>"
