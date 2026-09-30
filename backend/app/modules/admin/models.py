"""Cuentas de administración, roles y registro de auditoría."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Table, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.themes.models import Theme


class Role(enum.StrEnum):
    """Roles del panel.

    `admin` opera sobre todos los temas y gestiona cuentas y configuración.
    `editor` solo puede tocar el contenido de los temas que tiene asignados, lo
    que refleja que distintos investigadores son responsables de distintas
    comunidades.
    """

    ADMIN = "admin"
    EDITOR = "editor"


#: Temas asignados a una cuenta con rol `editor`. Para `admin` es irrelevante:
#: su alcance es total por definición del rol, no por asignación.
account_themes = Table(
    "account_themes",
    Base.metadata,
    Column(
        "account_id",
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "theme_id",
        UUID(as_uuid=True),
        ForeignKey("themes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    #: Hash Argon2id. Nunca la contraseña en claro ni cifrada de forma
    #: reversible.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[Role] = mapped_column(
        Enum(Role, name="account_role", values_callable=lambda m: [i.value for i in m]),
        nullable=False,
        default=Role.EDITOR,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    themes: Mapped[list[Theme]] = relationship(secondary=account_themes, lazy="selectin")

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    def can_edit_theme(self, theme_id: uuid.UUID) -> bool:
        """Si esta cuenta puede modificar contenido del tema indicado."""
        if self.is_admin:
            return True
        return any(theme.id == theme_id for theme in self.themes)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account {self.email} ({self.role.value})>"


class AuditLogEntry(Base):
    """Registro de acciones administrativas sobre el contenido.

    Existe para responder "¿quién publicó esto y cuándo?", que en un archivo
    testimonial no es una curiosidad sino una obligación de trazabilidad.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    #: Se conserva la entrada aunque la cuenta se elimine: el registro de
    #: auditoría no puede depender de que quien actuó siga existiendo.
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL")
    )
    account_email: Mapped[str] = mapped_column(String(320), nullable=False)

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    #: Detalle de la acción. Para cambios de consentimiento guarda el valor
    #: anterior y el nuevo, que es justo lo que se querrá auditar.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
