"""Esquemas de entrada y salida del chatbot."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.chat.models import ActivationState, VoicePolicy


class Citation(BaseModel):
    """Una cita: el fragmento textual y el enlace a la pieza que lo contiene.

    El enlace lo construye el servidor a partir de los slugs reales, nunca el
    modelo de lenguaje. Una dirección inventada que parece plausible es peor
    que ninguna: conduce a un 404 con apariencia de fuente.
    """

    #: Número con el que aparece en el texto de la respuesta.
    marker: int
    #: Palabras del archivo, tal cual. No se reformulan.
    text: str
    item_title: str
    item_slug: str
    theme_slug: str
    #: Ruta pública de la pieza en el sitio.
    url: str
    #: Traducción al inglés de la cita, cuando la respuesta va en inglés y el
    #: fragmento está en español. `None` cuando no aplica.
    translation: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    #: Identificador de la conversación en curso. Ausente en el primer turno.
    conversation_id: uuid.UUID | None = None
    #: Fuerza el idioma de la respuesta. Si no se indica, se detecta.
    language: Literal["es", "en"] | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    language: str
    citations: list[Citation] = []

    #: Por qué no hubo respuesta apoyada en el archivo, cuando aplica. Se
    #: expone para que el panel pueda revisar si el criterio fue correcto.
    no_material_reason: str | None = None

    #: Si se emitió el mensaje de contención en lugar de una respuesta de la
    #: narradora. La interfaz lo presenta distinto.
    contained: bool = False


class PersonaRead(BaseModel):
    """Cómo ve el público una narradora.

    No incluye el prompt de sistema: es el instrumento de trabajo del equipo y
    exponerlo facilitaría eludirlo.
    """

    model_config = ConfigDict(from_attributes=True)

    theme_slug: str
    activation: ActivationState
    voice_policy: VoicePolicy
    base_language: str

    @property
    def available(self) -> bool:
        return self.activation is ActivationState.ACTIVE


class PersonaAdminRead(PersonaRead):
    """Lo que ve una cuenta de administración, con el prompt incluido."""

    id: uuid.UUID
    system_prompt: str
    corpus_slug: str
    safety_enabled: bool
    safety_message_es: str | None = None
    safety_message_en: str | None = None


class PersonaUpdate(BaseModel):
    """Campos editables desde el panel.

    El tema no se puede cambiar: una narradora pertenece a su comunidad. Mover
    una configuración de tema sería cambiar de qué corpus habla, y eso se hace
    dando de alta otra, no reescribiendo esta.
    """

    system_prompt: str | None = Field(default=None, max_length=20000)
    corpus_slug: str | None = Field(default=None, max_length=64)
    activation: ActivationState | None = None
    voice_policy: VoicePolicy | None = None
    base_language: Literal["es", "en"] | None = None
    safety_enabled: bool | None = None
    safety_message_es: str | None = Field(default=None, max_length=4000)
    safety_message_en: str | None = Field(default=None, max_length=4000)
