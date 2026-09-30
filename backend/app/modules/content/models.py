"""Modelo de contenido compartido por los cuatro temas.

Una sola entidad `ContentItem`, discriminada por `type` y `theme`. Construir un
esquema por comunidad habría significado construir el gestor de contenidos y el
importador cuatro veces, y convertiría el alta de una quinta comunidad en un
refactor en vez de un registro (ver `design.md`, decisión 5).
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.themes.models import Theme


class ContentType(enum.StrEnum):
    """Tipos de pieza del catálogo."""

    PHOTO = "photo"
    TESTIMONY = "testimony"
    VIDEO = "video"
    INTERVIEW = "interview"
    NEWS_POST = "news_post"
    CURATED_LINK = "curated_link"
    GEO_ITEM = "geo_item"


#: Tipos cuya publicación exige texto alternativo, porque su contenido principal
#: es visual y sin descripción resulta inaccesible.
VISUAL_TYPES = frozenset({ContentType.PHOTO})


class ConsentScope(enum.StrEnum):
    """Alcance del consentimiento otorgado por la persona testimoniante.

    Publicar en el sitio y alimentar al chatbot son permisos **distintos**. Una
    persona puede autorizar la difusión de su testimonio sin autorizar que un
    modelo de lenguaje lo reformule.
    """

    #: Puede publicarse y puede entrar al índice del chatbot.
    PUBLIC = "public"
    #: Puede publicarse en el sitio, pero no entra al índice del chatbot.
    SITE_ONLY = "site_only"
    #: Puede publicarse en el sitio, y NUNCA entra al índice del chatbot.
    NO_AI = "no_ai"


#: Alcances que permiten indexar para el chatbot. Cualquier otro queda fuera.
INDEXABLE_SCOPES = frozenset({ConsentScope.PUBLIC})


class Attribution(enum.StrEnum):
    NAMED = "named"
    PSEUDONYM = "pseudonym"
    ANONYMOUS = "anonymous"


class Sensitivity(enum.StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class PublicationStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Enum de PostgreSQL que almacena el *valor*, no el nombre del miembro."""
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class ContentItem(Base, TimestampMixin):
    __tablename__ = "content_items"
    __table_args__ = (
        # La dirección pública de una pieza es /<tema>/<slug>, así que el slug
        # solo necesita ser único dentro de su tema.
        UniqueConstraint("theme_id", "slug", name="uq_content_items_theme_id_slug"),
        Index("ix_content_items_theme_type_status", "theme_id", "type", "status"),
        Index("ix_content_items_consent_scope", "consent_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    theme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("themes.id", ondelete="RESTRICT"), nullable=False
    )
    theme: Mapped[Theme] = relationship(lazy="joined")

    type: Mapped[ContentType] = mapped_column(_pg_enum(ContentType, "content_type"), nullable=False)

    #: Identificador legible para la dirección pública de la pieza.
    slug: Mapped[str] = mapped_column(String(160), nullable=False)

    #: El contenido escrito del archivo permanece en español (design.md, i18n).
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)

    # --- Publicación --------------------------------------------------------
    status: Mapped[PublicationStatus] = mapped_column(
        _pg_enum(PublicationStatus, "publication_status"),
        nullable=False,
        default=PublicationStatus.DRAFT,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Consentimiento -----------------------------------------------------
    #: Por defecto `no_ai`: incorporar una pieza al chatbot es siempre una
    #: decisión explícita, nunca un efecto secundario de importar o publicar.
    consent_scope: Mapped[ConsentScope] = mapped_column(
        _pg_enum(ConsentScope, "consent_scope"),
        nullable=False,
        default=ConsentScope.NO_AI,
        server_default=ConsentScope.NO_AI.value,
    )

    # --- Atribución ---------------------------------------------------------
    attribution: Mapped[Attribution] = mapped_column(
        _pg_enum(Attribution, "attribution"),
        nullable=False,
        default=Attribution.ANONYMOUS,
    )
    #: Nombre real. No aparece en ningún esquema público: la garantía es
    #: estructural, no una condición que alguien pueda olvidar evaluar.
    person_name: Mapped[str | None] = mapped_column(String(200))
    pseudonym: Mapped[str | None] = mapped_column(String(200))

    sensitivity: Mapped[Sensitivity] = mapped_column(
        _pg_enum(Sensitivity, "sensitivity"),
        nullable=False,
        default=Sensitivity.NORMAL,
    )

    # --- Media --------------------------------------------------------------
    #: Ruta en almacenamiento propio.
    media_key: Mapped[str | None] = mapped_column(String(500))
    media_mime: Mapped[str | None] = mapped_column(String(120))
    #: Recurso externo: enlace curado a un medio, o video de difusión general
    #: alojado en un servicio de terceros.
    external_url: Mapped[str | None] = mapped_column(String(1000))
    #: Nombre del medio, para enlaces curados.
    source_name: Mapped[str | None] = mapped_column(String(200))

    #: Texto alternativo del contenido visual. Obligatorio para publicar una
    #: pieza visual, opcional mientras sea borrador.
    alt_text: Mapped[str | None] = mapped_column(String(500))

    # --- Procedencia --------------------------------------------------------
    #: Identificador o ruta en el archivo original. Permite que la importación
    #: sea idempotente y que cada pieza sea rastreable hasta su origen.
    source_ref: Mapped[str | None] = mapped_column(String(1000), unique=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Fecha en que se registró el testimonio o la entrevista, si se conoce.
    recorded_on: Mapped[date | None] = mapped_column(Date)

    # --- Propiedades derivadas ---------------------------------------------

    @property
    def is_indexable(self) -> bool:
        """Si la pieza puede alimentar el corpus del chatbot.

        Exige estar publicada **y** tener consentimiento para uso con IA. Ambas
        condiciones, no cualquiera de las dos.
        """
        return self.status is PublicationStatus.PUBLISHED and (
            self.consent_scope in INDEXABLE_SCOPES
        )

    @property
    def display_name(self) -> str | None:
        """Nombre a mostrar públicamente, según la atribución.

        Nunca devuelve el nombre real de una pieza anónima o con seudónimo.
        """
        if self.attribution is Attribution.NAMED:
            return self.person_name
        if self.attribution is Attribution.PSEUDONYM:
            return self.pseudonym
        return None

    @property
    def requires_alt_text(self) -> bool:
        return (
            self.type in VISUAL_TYPES
            or self.media_mime is not None
            and (self.media_mime.startswith("image/"))
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ContentItem {self.type.value}:{self.slug}>"
