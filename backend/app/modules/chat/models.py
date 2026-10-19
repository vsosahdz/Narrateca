"""Configuración de la narradora de cada comunidad.

Una `PersonaConfig` por tema. Es **dato**, no código: la especificación exige
que el equipo de investigación pueda ajustar el prompt de sistema y el estado
de activación sin desplegar.
"""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, pg_enum


class ActivationState(enum.StrEnum):
    """Hasta dónde llega una narradora.

    Los estados son independientes entre comunidades: que la de migrantes esté
    activa no dice nada de las demás. Cada una se abre cuando su material y su
    revisión lo permiten, no cuando el código esté listo.
    """

    #: En preparación. Solo cuentas de administración pueden conversar, para
    #: poder revisar el comportamiento antes de abrirlo al público.
    DRAFT = "draft"
    #: Anunciada pero cerrada. El selector la muestra y explica que llegará.
    COMING_SOON = "coming_soon"
    #: Abierta al público.
    ACTIVE = "active"


class VoicePolicy(enum.StrEnum):
    """Qué voces admite la síntesis de esta comunidad.

    Se modela ahora aunque la síntesis sea de la fase 2. El motivo no es
    técnico: la restricción de voz femenina exclusiva para las iniciativas de
    mujeres es una decisión del equipo de investigación sobre cómo se
    representan esas voces, y registrarla junto al resto de la configuración
    evita que en la fase 2 haya que reconstruirla de memoria.
    """

    #: Exclusivamente voz femenina.
    FEMALE_ONLY = "female_only"
    #: Voz femenina o masculina.
    ANY = "any"


class PersonaConfig(Base, TimestampMixin):
    __tablename__ = "persona_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    theme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    #: Se guarda además del `theme_id` porque es la clave con la que se
    #: particiona el índice vectorial, y tenerla aquí evita una unión en el
    #: camino caliente de cada mensaje.
    theme_slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    #: El prompt que define a la narradora. Editable desde el panel: es el
    #: instrumento con el que el equipo ajusta el tono y los límites.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    #: De qué partición del índice recupera. Normalmente coincide con
    #: `theme_slug`, pero se declara aparte para poder apuntar una narradora a
    #: un corpus distinto durante una revisión sin tocar el resto.
    corpus_slug: Mapped[str] = mapped_column(String(64), nullable=False)

    activation: Mapped[ActivationState] = mapped_column(
        pg_enum(ActivationState, "activation_state"),
        nullable=False,
        # Una narradora nace cerrada. Abrirla es un acto deliberado, no el
        # estado en el que aparece por omisión.
        default=ActivationState.DRAFT,
        server_default=ActivationState.DRAFT.value,
    )

    voice_policy: Mapped[VoicePolicy] = mapped_column(
        pg_enum(VoicePolicy, "voice_policy"),
        nullable=False,
        # Por omisión, la opción más restrictiva. Si alguien da de alta una
        # comunidad y olvida declarar su política, el resultado es una
        # restricción de más y no una de menos.
        default=VoicePolicy.FEMALE_ONLY,
        server_default=VoicePolicy.FEMALE_ONLY.value,
    )

    #: Idioma del corpus. La respuesta puede ir en otro —la persona usuaria
    #: elige— pero la recuperación siempre ocurre sobre este.
    base_language: Mapped[str] = mapped_column(String(8), nullable=False, default="es")

    #: Si se emite el mensaje de contención ante relatos personales. Se deja
    #: configurable por comunidad porque el equipo redacta ese mensaje con
    #: criterio distinto en cada una, pero nace activa en todas.
    safety_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #: Mensaje de contención propio de la comunidad. Si está vacío se usa el
    #: general. Lo redacta el equipo de investigación, no el código.
    safety_message_es: Mapped[str | None] = mapped_column(Text)
    safety_message_en: Mapped[str | None] = mapped_column(Text)

    theme = relationship("Theme", lazy="joined")

    @property
    def is_public(self) -> bool:
        """Si el público general puede conversar con esta narradora."""
        return self.activation is ActivationState.ACTIVE

    def accepts(self, *, is_staff: bool) -> bool:
        """Si quien pregunta puede conversar con esta narradora.

        `draft` existe precisamente para poder probar antes de abrir, así que
        una cuenta de administración entra; cualquier otra persona, no.
        """
        if self.activation is ActivationState.ACTIVE:
            return True
        if self.activation is ActivationState.DRAFT:
            return is_staff
        return False

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<PersonaConfig {self.theme_slug} {self.activation}>"
