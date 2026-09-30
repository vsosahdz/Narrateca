"""Esquemas del catálogo de contenido.

La decisión importante de este archivo: existen **dos** esquemas de lectura.

`PublicContentRead` simplemente **no tiene** campo para el nombre real. No lo
oculta condicionalmente: no existe. Una regla que depende de recordar evaluar una
condición se rompe el día que alguien agrega un endpoint nuevo; una que depende
de la forma del tipo no se puede romper por olvido.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.content.models import (
    Attribution,
    ConsentScope,
    ContentType,
    PublicationStatus,
    Sensitivity,
)

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ContentCreate(BaseModel):
    theme_slug: str
    type: ContentType
    slug: str = Field(max_length=160, pattern=SLUG_PATTERN)
    title: str = Field(max_length=300)
    summary: str | None = None
    body: str | None = None

    #: Se omite a propósito de la creación: el valor por defecto del modelo es
    #: `no_ai` y elevarlo debe ser un acto explícito y auditable.
    consent_scope: ConsentScope = ConsentScope.NO_AI

    attribution: Attribution = Attribution.ANONYMOUS
    person_name: str | None = Field(default=None, max_length=200)
    pseudonym: str | None = Field(default=None, max_length=200)
    sensitivity: Sensitivity = Sensitivity.NORMAL

    media_key: str | None = None
    media_mime: str | None = None
    external_url: str | None = None
    source_name: str | None = None
    alt_text: str | None = Field(default=None, max_length=500)

    source_ref: str | None = None
    recorded_on: date | None = None

    @model_validator(mode="after")
    def _atribucion_coherente(self) -> "ContentCreate":
        if self.attribution is Attribution.NAMED and not self.person_name:
            raise ValueError("Una pieza con atribución 'named' requiere person_name.")
        if self.attribution is Attribution.PSEUDONYM and not self.pseudonym:
            raise ValueError("Una pieza con atribución 'pseudonym' requiere pseudonym.")
        return self


class ContentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    summary: str | None = None
    body: str | None = None
    consent_scope: ConsentScope | None = None
    attribution: Attribution | None = None
    person_name: str | None = Field(default=None, max_length=200)
    pseudonym: str | None = Field(default=None, max_length=200)
    sensitivity: Sensitivity | None = None
    media_key: str | None = None
    media_mime: str | None = None
    external_url: str | None = None
    source_name: str | None = None
    alt_text: str | None = Field(default=None, max_length=500)
    recorded_on: date | None = None


class PublicContentRead(BaseModel):
    """Representación pública de una pieza.

    No incluye `person_name` ni `consent_scope`. El nombre real no se expone
    jamás por esta vía, y el alcance de consentimiento es información interna de
    gestión, no del público.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    theme_slug: str
    type: ContentType
    slug: str
    title: str
    summary: str | None
    body: str | None
    #: Nombre a mostrar: real solo si la atribución es 'named'; el seudónimo si
    #: es 'pseudonym'; nulo si es anónima.
    display_name: str | None
    attribution: Attribution
    sensitivity: Sensitivity
    media_key: str | None
    media_mime: str | None
    external_url: str | None
    source_name: str | None
    alt_text: str | None
    recorded_on: date | None
    published_at: datetime | None


class AdminContentRead(PublicContentRead):
    """Representación para el panel de administración.

    Añade lo que el equipo necesita para gestionar y auditar, incluido el nombre
    real y el alcance de consentimiento.
    """

    status: PublicationStatus
    consent_scope: ConsentScope
    person_name: str | None
    pseudonym: str | None
    is_indexable: bool
    source_ref: str | None
    imported_at: datetime | None
    created_at: datetime
    updated_at: datetime
