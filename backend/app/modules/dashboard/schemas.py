"""Esquemas del panel de control.

Un principio recorre este archivo: **lo que no se puede medir todavía se declara
como no disponible, no como cero**. Un panel que muestra «0 conversaciones»
cuando el chatbot aún no existe hace creer que nadie lo usa, en vez de que aún no
hay nada que contar.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ThemeCoverage(BaseModel):
    """Estado del contenido de una comunidad.

    Separa tres cosas que suelen confundirse: cuánto hay, cuánto está publicado
    y cuánto alimenta al chatbot. Son tres números distintos y la diferencia
    entre ellos es donde vive el consentimiento.
    """

    theme_slug: str
    theme_name: str

    total: int
    draft: int
    published: int
    withdrawn: int

    #: Publicadas Y con consentimiento para uso con IA. Es el techo del corpus.
    indexable: int
    #: Excluidas del chatbot por decisión de consentimiento, no por olvido.
    excluded_no_ai: int
    excluded_site_only: int

    #: Piezas visuales publicables bloqueadas por falta de texto alternativo.
    blocked_missing_alt_text: int


class TypeCount(BaseModel):
    type: str
    count: int


class ArchiveHealth(BaseModel):
    """Situación del archivo físico frente al catálogo."""

    #: Conteo por situación: detectado, importado, modificado, ausente, fallido.
    by_status: dict[str, int]
    #: Documentos que requieren una decisión del equipo.
    needs_attention: int
    #: Documentos detectados y todavía sin importar.
    pending_import: int
    #: Documentos cuya importación falló.
    failed: int
    last_scan_at: datetime | None


class AuditEntry(BaseModel):
    account_email: str
    action: str
    entity_type: str
    created_at: datetime


class Alert(BaseModel):
    """Aviso accionable del panel.

    No son errores del sistema: son divergencias que alguien debe resolver, y el
    panel existe justamente para que no pasen inadvertidas.
    """

    #: `info`, `warning` o `blocking`.
    level: str
    message: str
    count: int


class PendingSection(BaseModel):
    """Sección del panel cuyos datos aún no existen.

    Se declara explícitamente en la respuesta para que la interfaz pueda decir
    «pendiente» en lugar de dibujar una gráfica vacía.
    """

    key: str
    label: str
    reason: str


class DashboardRead(BaseModel):
    generated_at: datetime

    # --- Salud del archivo --------------------------------------------------
    themes: list[ThemeCoverage]
    types: list[TypeCount]
    total_items: int
    total_published: int
    total_indexable: int

    # --- Ingesta ------------------------------------------------------------
    archive: ArchiveHealth

    # --- Actividad ----------------------------------------------------------
    recent_activity: list[AuditEntry]

    # --- Avisos -------------------------------------------------------------
    alerts: list[Alert] = Field(default_factory=list)

    # --- Lo que aún no se puede medir --------------------------------------
    pending_sections: list[PendingSection] = Field(default_factory=list)
