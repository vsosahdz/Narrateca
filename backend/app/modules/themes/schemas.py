"""Esquemas de entrada y salida del módulo de temas.

En la equivalencia MVC del proyecto, los esquemas Pydantic son la *vista*: la
representación JSON que cruza la frontera HTTP.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


# Misma ortografía que los slugs de contenido: minúsculas, dígitos y guion
# medio. Ambos aparecen en la misma URL pública —`/es/temas/<tema>` y
# `/es/contenido/<pieza>`— y que uno usara guion bajo y el otro guion medio era
# una diferencia sin motivo que se veía desde fuera.
#
# El guion bajo queda excluido a propósito: si se admitieran los dos, volverían
# a convivir las dos grafías y la unificación duraría hasta el próximo tema que
# alguien diera de alta.
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ThemeBase(BaseModel):
    slug: str = Field(max_length=64, pattern=SLUG_PATTERN)
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
