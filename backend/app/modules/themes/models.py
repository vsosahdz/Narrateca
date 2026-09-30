"""Modelo de tema (comunidad).

Los cuatro temas de NarraTECa son **datos**, no valores codificados en la
aplicación. Dar de alta una quinta comunidad debe ser un registro, no un
refactor (ver spec `content-catalog`, requisito de modelo compartido).
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Theme(Base, TimestampMixin):
    __tablename__ = "themes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Identificador estable usado en rutas y en la partición del índice vectorial.
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    name_es: Mapped[str] = mapped_column(String(160), nullable=False)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)

    description_es: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)

    #: Nombre del token de acento, no un color literal. La paleta vive en el
    #: código del frontend y es intercambiable desde ahí
    #: (ver spec `design-tokens`).
    accent_token: Mapped[str] = mapped_column(String(64), nullable=False)

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Theme {self.slug}>"
