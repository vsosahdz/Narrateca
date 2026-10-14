"""Importación de documentos del archivo al catálogo de contenido.

Convierte documentos detectados en piezas de contenido, preservando la
procedencia. Tres propiedades sostienen el proceso:

1. **Idempotencia.** Ejecutarlo dos veces no crea duplicados: la ruta relativa
   del documento queda como `source_ref` de la pieza, y ese campo es único.
2. **Aislamiento de fallos.** Un documento ilegible no interrumpe el lote: se
   marca como fallido con su causa y el resto continúa.
3. **Consentimiento explícito.** Quien importa debe declarar el alcance. El
   valor por defecto es `no_ai`, el más protector, y nunca se infiere.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import ALLOWED_MIME_TYPES, Storage, build_key, guess_content_type
from app.modules.admin.models import Account
from app.modules.archive.extraction import (
    ExtractionError,
    can_extract,
    derive_title,
    extract_text,
    needs_transcription,
)
from app.modules.archive.models import ArchiveDocument, DocumentStatus
from app.modules.archive.scanner import slug_from_path
from app.modules.content.models import (
    Attribution,
    ConsentScope,
    ContentItem,
    ContentType,
    PublicationStatus,
    Sensitivity,
)
from app.modules.themes.models import Theme


@dataclass
class ImportReport:
    """Resultado de una importación, desglosado para poder actuar sobre él."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    #: Documentos importados cuyo texto llegará por transcripción.
    awaiting_transcription: list[str] = field(default_factory=list)
    by_theme: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped) + len(self.failed)


class ArchiveImporter:
    def __init__(
        self,
        session: AsyncSession,
        root: Path,
        storage: Storage,
        actor: Account | None = None,
    ) -> None:
        self.session = session
        self.root = Path(root)
        self.storage = storage
        self.actor = actor

    async def import_documents(
        self,
        *,
        theme_slug: str | None = None,
        consent_scope: ConsentScope = ConsentScope.NO_AI,
        attribution: Attribution = Attribution.ANONYMOUS,
        sensitivity: Sensitivity = Sensitivity.NORMAL,
        document_ids: Sequence[uuid.UUID] | None = None,
        limit: int = 500,
    ) -> ImportReport:
        """Importa documentos pendientes y devuelve el reporte del lote."""
        report = ImportReport()

        stmt = select(ArchiveDocument).where(
            ArchiveDocument.status.in_(
                [DocumentStatus.DISCOVERED, DocumentStatus.FAILED]
            )
        )
        if theme_slug:
            stmt = stmt.where(ArchiveDocument.theme_slug == theme_slug)
        if document_ids is not None:
            stmt = stmt.where(ArchiveDocument.id.in_(list(document_ids)))

        result = await self.session.execute(stmt.order_by(ArchiveDocument.relative_path).limit(limit))
        documents = list(result.scalars().all())

        themes = {
            theme.slug: theme
            for theme in (await self.session.execute(select(Theme))).scalars().all()
        }

        for document in documents:
            try:
                await self._import_one(
                    document,
                    themes,
                    report,
                    consent_scope=consent_scope,
                    attribution=attribution,
                    sensitivity=sensitivity,
                )
            except Exception as error:  # noqa: BLE001 - se registra y se continúa
                # Un documento que falla no debe detener el lote: en un archivo
                # de cientos de piezas, eso obligaría a reiniciar desde cero.
                document.status = DocumentStatus.FAILED
                document.error = str(error)[:2000]
                report.failed.append((document.relative_path, str(error)))

        await self.session.commit()
        return report

    async def _import_one(
        self,
        document: ArchiveDocument,
        themes: dict[str, Theme],
        report: ImportReport,
        *,
        consent_scope: ConsentScope,
        attribution: Attribution,
        sensitivity: Sensitivity,
    ) -> None:
        theme = themes.get(document.theme_slug)
        if theme is None:
            raise ValueError(
                f"La carpeta «{document.theme_slug}» no corresponde a ninguna comunidad."
            )

        # Idempotencia: si ya existe una pieza con esta procedencia, no se crea
        # otra. Solo se repara el vínculo, que puede haberse perdido si alguien
        # importó por otra vía.
        existing = await self.session.execute(
            select(ContentItem).where(ContentItem.source_ref == document.relative_path)
        )
        already = existing.unique().scalar_one_or_none()
        if already is not None:
            document.content_item_id = already.id
            document.status = DocumentStatus.IMPORTED
            document.error = None
            report.skipped.append(document.relative_path)
            return

        absolute = self.root / document.relative_path
        if not absolute.is_file():
            raise FileNotFoundError("El documento ya no existe en el archivo.")

        content_type = document.detected_type or ContentType.TESTIMONY
        body: str | None = None
        media_key: str | None = None
        media_mime: str | None = None

        if can_extract(absolute):
            try:
                body = extract_text(absolute)
            except ExtractionError as error:
                raise ValueError(str(error)) from error

        if not can_extract(absolute) or needs_transcription(absolute):
            media_key, media_mime = await self._store_media(
                absolute, document.theme_slug, sensitivity
            )
            if needs_transcription(absolute):
                report.awaiting_transcription.append(document.relative_path)

        slug = await self._unique_slug(theme.id, absolute)

        item = ContentItem(
            theme_id=theme.id,
            type=content_type,
            slug=slug,
            title=derive_title(absolute),
            body=body,
            status=PublicationStatus.DRAFT,
            consent_scope=consent_scope,
            attribution=attribution,
            sensitivity=sensitivity,
            media_key=media_key,
            media_mime=media_mime,
            source_ref=document.relative_path,
            imported_at=datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()

        document.content_item_id = item.id
        document.status = DocumentStatus.IMPORTED
        document.imported_at = item.imported_at
        document.error = None

        report.created.append(document.relative_path)
        report.by_theme[theme.slug] = report.by_theme.get(theme.slug, 0) + 1
        report.by_type[content_type.value] = report.by_type.get(content_type.value, 0) + 1

    async def _store_media(
        self, absolute: Path, theme_slug: str, sensitivity: Sensitivity
    ) -> tuple[str | None, str | None]:
        """Copia el archivo al almacenamiento, sin tocar el original.

        El material original permanece intacto en el archivo: el almacenamiento
        recibe una copia. Mover el original haría irreversible la importación.
        """
        try:
            mime = guess_content_type(absolute.name, None)
        except Exception:
            # Formato fuera de la lista de admitidos: la pieza se crea sin
            # media y el equipo decide qué hacer con el documento.
            return None, None

        if mime not in ALLOWED_MIME_TYPES:
            return None, None

        scope = "sensitive" if sensitivity is Sensitivity.HIGH else "public"
        key = build_key(
            scope=scope, theme_slug=theme_slug, filename=absolute.name, content_type=mime
        )
        with absolute.open("rb") as handle:
            await self.storage.save(key, handle)
        return key, mime

    async def _unique_slug(self, theme_id: uuid.UUID, absolute: Path) -> str:
        """Identificador único dentro del tema.

        Dos archivos con el mismo nombre en carpetas distintas producirían el
        mismo slug; se desambigua con un sufijo en vez de fallar, porque en un
        archivo real los nombres repetidos son la norma.
        """
        base = slug_from_path(absolute)
        candidate = base
        suffix = 2

        while True:
            found = await self.session.execute(
                select(ContentItem.id).where(
                    ContentItem.theme_id == theme_id, ContentItem.slug == candidate
                )
            )
            if found.scalar_one_or_none() is None:
                return candidate
            candidate = f"{base}-{suffix}"
            suffix += 1
