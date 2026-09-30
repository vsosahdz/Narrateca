"""Esquemas de entrada y salida del módulo de temas.

En la equivalencia MVC del proyecto, los esquemas Pydantic son la *vista*: la
representación JSON que cruza la frontera HTTP.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ThemeBase(BaseModel):
    slug: str = Field(max_length=64, pattern=r"^[a-z0-9_]+$")
    name_es: str = Field(max_length=160)
    name_en: str = Field(max_length=160)
    description_es: str | None = None
    description_en: str | None = None
    accent_token: str = Field(max_length=64)
    position: int = 0
    is_active: bool = True


class ThemeCreate(ThemeBase):
    pass


class ThemeUpdate(BaseModel):
    name_es: str | None = Field(default=None, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    description_es: str | None = None
    description_en: str | None = None
    accent_token: str | None = Field(default=None, max_length=64)
    position: int | None = None
    is_active: bool | None = None


class ThemeRead(ThemeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
