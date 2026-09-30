"""Esquemas del equipo de investigación."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeamMemberBase(BaseModel):
    full_name: str = Field(max_length=200)
    role_title: str | None = Field(default=None, max_length=200)
    bio: str = Field(min_length=1)
    photo_key: str | None = Field(default=None, max_length=500)
    photo_alt: str | None = Field(default=None, max_length=500)
    position: int = 0
    is_active: bool = True

    @model_validator(mode="after")
    def _foto_con_descripcion(self) -> "TeamMemberBase":
        if self.photo_key and not (self.photo_alt or "").strip():
            raise ValueError(
                "Una fotografía requiere texto alternativo. Campo faltante: photo_alt."
            )
        return self


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    role_title: str | None = Field(default=None, max_length=200)
    bio: str | None = None
    photo_key: str | None = Field(default=None, max_length=500)
    photo_alt: str | None = Field(default=None, max_length=500)
    position: int | None = None
    is_active: bool | None = None


class TeamMemberRead(TeamMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
