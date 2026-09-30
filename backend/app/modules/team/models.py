"""Equipo de investigación."""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class TeamMember(Base, TimestampMixin):
    __tablename__ = "team_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    #: Adscripción o cargo, por ejemplo "Investigadora, Escuela de Humanidades".
    role_title: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str] = mapped_column(Text, nullable=False)

    photo_key: Mapped[str | None] = mapped_column(String(500))
    #: Obligatorio cuando hay fotografía. Una foto sin descripción deja fuera a
    #: quien usa lector de pantalla, y este proyecto no puede permitírselo.
    photo_alt: Mapped[str | None] = mapped_column(String(500))

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TeamMember {self.full_name}>"
