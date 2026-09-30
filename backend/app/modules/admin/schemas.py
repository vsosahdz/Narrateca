"""Esquemas de administración.

`AccountRead` no incluye `password_hash`. Igual que con el nombre real de las
personas testimoniantes, la garantía es estructural: el campo no existe en el
tipo de salida, así que no puede filtrarse por olvido.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.admin.models import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ThemeRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name_es: str


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None
    themes: list[ThemeRef]


class AccountCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(max_length=200)
    #: Longitud mínima generosa en vez de reglas de composición: la evidencia
    #: indica que exigir símbolos y mayúsculas produce contraseñas peores y más
    #: fáciles de olvidar que exigir longitud.
    password: str = Field(min_length=12, max_length=200)
    role: Role = Role.EDITOR
    #: Temas asignados. Solo tiene efecto para el rol `editor`.
    theme_slugs: list[str] = Field(default_factory=list)


class AccountUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    role: Role | None = None
    is_active: bool | None = None
    theme_slugs: list[str] | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=200)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_email: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    details: dict | None
    created_at: datetime
