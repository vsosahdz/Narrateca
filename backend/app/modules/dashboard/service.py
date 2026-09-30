"""Agregaciones del panel de control.

Todo se calcula con consultas agregadas y no cargando el catálogo en memoria: el
panel debe seguir respondiendo cuando el archivo tenga miles de piezas.
"""

from datetime import UTC, datetime

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import AuditLogEntry
from app.modules.archive.models import ArchiveDocument, DocumentStatus
from app.modules.content.models import (
    VISUAL_TYPES,
    ConsentScope,
    ContentItem,
    PublicationStatus,
)
from app.modules.dashboard.schemas import (
    Alert,
    ArchiveHealth,
    AuditEntry,
    DashboardRead,
    PendingSection,
    ThemeCoverage,
    TypeCount,
)
from app.modules.themes.models import Theme

#: Secciones cuyo dato depende de capacidades que aún no existen. Se declaran
#: para que el panel diga «pendiente» en vez de dibujar ceros.
PENDING_SECTIONS = [
    PendingSection(
        key="personas",
        label="Estado de activación de las personas",
        reason="Requiere la configuración de personas del chatbot.",
    ),
    PendingSection(
        key="conversaciones",
        label="Volumen de conversaciones",
        reason="Requiere el chatbot y la persistencia de conversaciones.",
    ),
    PendingSection(
        key="sin_respuesta",
        label="Preguntas sin material relevante",
        reason="Requiere el registro de recuperación del chatbot.",
    ),
    PendingSection(
        key="fragmentos",
        label="Fragmentos más recuperados",
        reason="Requiere el índice vectorial.",
    ),
    PendingSection(
        key="contencion",
        label="Mensajes de contención",
        reason="Requiere el chatbot y la persistencia de conversaciones.",
    ),
]


def _count_when(condition) -> Select:  # type: ignore[type-arg]
    """Cuenta condicional, para resolver todo el desglose en una sola consulta."""
    return func.count(case((condition, 1)))


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build(self) -> DashboardRead:
        themes = await self._theme_coverage()
        types = await self._type_counts()
        archive = await self._archive_health()
        activity = await self._recent_activity()

        total_items = sum(t.total for t in themes)
        total_published = sum(t.published for t in themes)
        total_indexable = sum(t.indexable for t in themes)

        return DashboardRead(
            generated_at=datetime.now(UTC),
            themes=themes,
            types=types,
            total_items=total_items,
            total_published=total_published,
            total_indexable=total_indexable,
            archive=archive,
            recent_activity=activity,
            alerts=self._alerts(themes, archive),
            pending_sections=PENDING_SECTIONS,
        )

    # --- Salud del archivo --------------------------------------------------

    async def _theme_coverage(self) -> list[ThemeCoverage]:
        """Desglose por comunidad, en una consulta agregada."""
        visual = ContentItem.type.in_(list(VISUAL_TYPES))
        sin_alt = func.coalesce(func.trim(ContentItem.alt_text), "") == ""

        stmt = (
            select(
                Theme.slug,
                Theme.name_es,
                func.count(ContentItem.id).label("total"),
                _count_when(ContentItem.status == PublicationStatus.DRAFT).label("draft"),
                _count_when(ContentItem.status == PublicationStatus.PUBLISHED).label("published"),
                _count_when(ContentItem.status == PublicationStatus.WITHDRAWN).label("withdrawn"),
                _count_when(
                    (ContentItem.status == PublicationStatus.PUBLISHED)
                    & (ContentItem.consent_scope == ConsentScope.PUBLIC)
                ).label("indexable"),
                _count_when(ContentItem.consent_scope == ConsentScope.NO_AI).label("no_ai"),
                _count_when(ContentItem.consent_scope == ConsentScope.SITE_ONLY).label("site_only"),
                # Piezas visuales que no pueden publicarse hasta que alguien
                # escriba su texto alternativo. Es trabajo concreto pendiente.
                _count_when(
                    visual & sin_alt & (ContentItem.status != PublicationStatus.PUBLISHED)
                ).label("sin_alt"),
            )
            .select_from(Theme)
            .outerjoin(ContentItem, ContentItem.theme_id == Theme.id)
            .group_by(Theme.slug, Theme.name_es, Theme.position)
            .order_by(Theme.position)
        )

        rows = (await self.session.execute(stmt)).all()
        return [
            ThemeCoverage(
                theme_slug=row.slug,
                theme_name=row.name_es,
                total=row.total,
                draft=row.draft,
                published=row.published,
                withdrawn=row.withdrawn,
                indexable=row.indexable,
                excluded_no_ai=row.no_ai,
                excluded_site_only=row.site_only,
                blocked_missing_alt_text=row.sin_alt,
            )
            for row in rows
        ]

    async def _type_counts(self) -> list[TypeCount]:
        stmt = (
            select(ContentItem.type, func.count(ContentItem.id))
            .group_by(ContentItem.type)
            .order_by(func.count(ContentItem.id).desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [TypeCount(type=tipo.value, count=cuenta) for tipo, cuenta in rows]

    # --- Ingesta ------------------------------------------------------------

    async def _archive_health(self) -> ArchiveHealth:
        stmt = select(ArchiveDocument.status, func.count(ArchiveDocument.id)).group_by(
            ArchiveDocument.status
        )
        by_status = {
            estado.value: cuenta for estado, cuenta in (await self.session.execute(stmt)).all()
        }

        atencion = {
            DocumentStatus.DISCOVERED,
            DocumentStatus.MODIFIED,
            DocumentStatus.MISSING,
            DocumentStatus.FAILED,
        }

        last_scan = (
            await self.session.execute(select(func.max(ArchiveDocument.last_seen_at)))
        ).scalar_one_or_none()

        return ArchiveHealth(
            by_status=by_status,
            needs_attention=sum(by_status.get(e.value, 0) for e in atencion),
            pending_import=by_status.get(DocumentStatus.DISCOVERED.value, 0),
            failed=by_status.get(DocumentStatus.FAILED.value, 0),
            last_scan_at=last_scan,
        )

    # --- Actividad ----------------------------------------------------------

    async def _recent_activity(self, limit: int = 15) -> list[AuditEntry]:
        stmt = select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit)
        entries = (await self.session.execute(stmt)).scalars().all()
        return [
            AuditEntry(
                account_email=e.account_email,
                action=e.action,
                entity_type=e.entity_type,
                created_at=e.created_at,
            )
            for e in entries
        ]

    # --- Avisos -------------------------------------------------------------

    def _alerts(self, themes: list[ThemeCoverage], archive: ArchiveHealth) -> list[Alert]:
        """Divergencias que alguien debe resolver.

        El panel existe para que estas no pasen inadvertidas. Se ordenan de más
        a menos urgente.
        """
        alerts: list[Alert] = []

        bloqueadas = sum(t.blocked_missing_alt_text for t in themes)
        if bloqueadas:
            alerts.append(
                Alert(
                    level="blocking",
                    message=(
                        "piezas visuales no pueden publicarse hasta que alguien "
                        "escriba su texto alternativo"
                    ),
                    count=bloqueadas,
                )
            )

        if archive.failed:
            alerts.append(
                Alert(
                    level="warning",
                    message="documentos del archivo fallaron al importarse",
                    count=archive.failed,
                )
            )

        modificados = archive.by_status.get(DocumentStatus.MODIFIED.value, 0)
        if modificados:
            alerts.append(
                Alert(
                    level="warning",
                    message=(
                        "documentos cambiaron en disco después de importarse: "
                        "la pieza del catálogo puede estar desactualizada"
                    ),
                    count=modificados,
                )
            )

        ausentes = archive.by_status.get(DocumentStatus.MISSING.value, 0)
        if ausentes:
            alerts.append(
                Alert(
                    level="warning",
                    message="documentos registrados ya no aparecen en el archivo",
                    count=ausentes,
                )
            )

        if archive.pending_import:
            alerts.append(
                Alert(
                    level="info",
                    message="documentos detectados esperan importación",
                    count=archive.pending_import,
                )
            )

        vacios = [t for t in themes if t.published == 0]
        if vacios:
            alerts.append(
                Alert(
                    level="info",
                    message=(
                        "comunidades sin contenido publicado: "
                        + ", ".join(t.theme_name for t in vacios)
                    ),
                    count=len(vacios),
                )
            )

        return alerts
