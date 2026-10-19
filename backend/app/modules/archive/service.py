"""Reconciliación entre el archivo físico y el registro de ingesta."""

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.archive.models import ArchiveDocument, DocumentStatus
from app.modules.archive.scanner import ScannedFile, compute_hash, walk_archive
from app.modules.themes.models import Theme


@dataclass
class ScanReport:
    """Resultado de un escaneo, pensado para ser accionable.

    No basta con decir cuántos archivos hay: lo que el equipo necesita saber es
    qué apareció, qué cambió y qué desapareció desde la última vez.
    """

    root: str
    scanned: int = 0
    #: Documentos que no estaban en el registro.
    new: list[str] = field(default_factory=list)
    #: Documentos ya importados cuyo contenido cambió en disco.
    modified: list[str] = field(default_factory=list)
    #: Documentos registrados que ya no aparecen en el árbol.
    missing: list[str] = field(default_factory=list)
    #: Documentos sin cambios respecto al registro.
    unchanged: int = 0
    #: Rutas cuya primera carpeta no corresponde a ninguna comunidad.
    unknown_theme: list[str] = field(default_factory=list)
    #: Archivos cuyo tipo no se pudo deducir. No es un error: es trabajo
    #: pendiente de clasificación.
    unclassified: list[str] = field(default_factory=list)
    by_theme: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    hashed: int = 0

    @property
    def needs_attention(self) -> int:
        return len(self.new) + len(self.modified) + len(self.missing)


class ArchiveService:
    def __init__(self, session: AsyncSession, root: Path) -> None:
        self.session = session
        self.root = Path(root)

    # --- Consulta -----------------------------------------------------------

    async def list_documents(
        self,
        *,
        theme_slug: str | None = None,
        status: DocumentStatus | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ArchiveDocument]:
        stmt = select(ArchiveDocument).order_by(ArchiveDocument.relative_path)
        if theme_slug:
            stmt = stmt.where(ArchiveDocument.theme_slug == theme_slug)
        if status:
            stmt = stmt.where(ArchiveDocument.status == status)
        result = await self.session.execute(stmt.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def get(self, document_id: uuid.UUID) -> ArchiveDocument:
        document = await self.session.get(ArchiveDocument, document_id)
        if document is None:
            raise NotFoundError("El documento solicitado no existe en el registro.")
        return document

    async def summary(self) -> dict[str, int]:
        """Conteo por estado, para el panel de control."""
        documents = await self.list_documents(limit=100_000)
        return dict(Counter(document.status.value for document in documents))

    # --- Escaneo ------------------------------------------------------------

    async def scan(self, *, rehash_all: bool = False) -> ScanReport:
        """Recorre el archivo y actualiza el registro.

        No importa nada al catálogo: solo determina qué hay, qué es nuevo y qué
        cambió. La importación es una decisión aparte, porque cada pieza
        necesita que alguien defina su consentimiento antes de entrar.
        """
        report = ScanReport(root=str(self.root))

        known_themes = {slug for (slug,) in (await self.session.execute(select(Theme.slug))).all()}

        existing = {
            document.relative_path: document
            for document in await self.list_documents(limit=1_000_000)
        }
        seen: set[str] = set()
        now = datetime.now(UTC)

        for found in walk_archive(self.root):
            report.scanned += 1
            seen.add(found.relative_path)

            report.by_theme[found.theme_slug] = report.by_theme.get(found.theme_slug, 0) + 1
            type_label = found.detected_type.value if found.detected_type else "sin clasificar"
            report.by_type[type_label] = report.by_type.get(type_label, 0) + 1

            if found.theme_slug not in known_themes:
                report.unknown_theme.append(found.relative_path)
            if found.detected_type is None:
                report.unclassified.append(found.relative_path)

            document = existing.get(found.relative_path)
            if document is None:
                self._register_new(found, now, report)
            else:
                self._reconcile(document, found, now, report, rehash_all=rehash_all)

        # Lo que estaba registrado y ya no aparece.
        for path, document in existing.items():
            if path in seen or document.status is DocumentStatus.MISSING:
                continue
            document.status = DocumentStatus.MISSING
            report.missing.append(path)

        await self.session.commit()
        return report

    def _register_new(self, found: ScannedFile, now: datetime, report: ScanReport) -> None:
        document = ArchiveDocument(
            relative_path=found.relative_path,
            theme_slug=found.theme_slug,
            detected_type=found.detected_type,
            content_hash=compute_hash(found.absolute_path),
            size_bytes=found.size_bytes,
            modified_at=found.modified_at,
            status=DocumentStatus.DISCOVERED,
            first_seen_at=now,
            last_seen_at=now,
        )
        self.session.add(document)
        report.new.append(found.relative_path)
        report.hashed += 1

    def _reconcile(
        self,
        document: ArchiveDocument,
        found: ScannedFile,
        now: datetime,
        report: ScanReport,
        *,
        rehash_all: bool,
    ) -> None:
        document.last_seen_at = now

        # Si el tamaño y la fecha de modificación coinciden, se da por
        # inalterado sin volver a leer el archivo. Con horas de video, esa
        # decisión es la diferencia entre un escaneo de segundos y uno de
        # muchos minutos.
        same_stat = (
            document.size_bytes == found.size_bytes
            and document.modified_at is not None
            and int(document.modified_at.timestamp()) == int(found.modified_at.timestamp())
        )
        if same_stat and not rehash_all:
            report.unchanged += 1
            if document.status is DocumentStatus.MISSING:
                # Reapareció: vuelve a estar pendiente de decisión.
                document.status = DocumentStatus.DISCOVERED
            return

        new_hash = compute_hash(found.absolute_path)
        report.hashed += 1

        document.size_bytes = found.size_bytes
        document.modified_at = found.modified_at
        document.detected_type = found.detected_type or document.detected_type

        if document.content_hash == new_hash:
            # Solo cambió la fecha: el contenido es el mismo.
            report.unchanged += 1
            return

        document.content_hash = new_hash

        if document.status is DocumentStatus.IMPORTED:
            # Ya existe una pieza en el catálogo construida a partir de una
            # versión anterior de este archivo. Se marca para que alguien decida
            # si la pieza debe actualizarse.
            document.status = DocumentStatus.MODIFIED
            report.modified.append(found.relative_path)
        else:
            document.status = DocumentStatus.DISCOVERED
            if found.relative_path not in report.new:
                report.modified.append(found.relative_path)

    # --- Estructura de carpetas ---------------------------------------------

    def ensure_layout(self, theme_slugs: list[str]) -> list[str]:
        """Crea la estructura de carpetas del archivo si no existe.

        Devuelve las rutas creadas. Es idempotente: ejecutarlo dos veces no
        altera nada de lo que ya exista.
        """
        from app.modules.archive.scanner import CANONICAL_FOLDERS

        created: list[str] = []
        for slug in theme_slugs:
            # Si ya existe la carpeta con la grafía antigua —guion bajo, como se
            # llamaban los slugs antes— se respeta y se trabaja dentro. Crear
            # `mujeres-discapacidad/` al lado de `mujeres_discapacidad/` dejaría
            # dos árboles para la misma comunidad y material repartido entre los
            # dos sin que nadie sepa cuál es el bueno.
            heredada = self.root / slug.replace("-", "_")
            carpeta_tema = heredada if heredada.is_dir() else self.root / slug

            for folder in sorted(CANONICAL_FOLDERS.values()):
                path = carpeta_tema / folder
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    # Marcador para que la carpeta vacía sobreviva a un copiado
                    # y para que quien abra el archivo vea la estructura.
                    (path / ".gitkeep").touch()
                    created.append(str(path.relative_to(self.root)))
        return created
