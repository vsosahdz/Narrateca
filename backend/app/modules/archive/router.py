"""Endpoints del registro de ingesta del archivo."""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.storage import Storage, get_storage
from app.modules.admin.dependencies import get_current_account, require_admin
from app.modules.admin.models import Account
from app.modules.archive.importer import ArchiveImporter, ImportReport
from app.modules.archive.models import DocumentStatus
from app.modules.archive.service import ArchiveService, ScanReport
from app.modules.content.models import Attribution, ConsentScope, ContentType, Sensitivity

router = APIRouter(prefix="/admin/archive", tags=["Ingesta"])


class ArchiveDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relative_path: str
    theme_slug: str
    detected_type: ContentType | None
    content_hash: str | None
    size_bytes: int
    modified_at: datetime | None
    status: DocumentStatus
    content_item_id: uuid.UUID | None
    error: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    imported_at: datetime | None


class ScanReportRead(BaseModel):
    root: str
    scanned: int
    new: list[str]
    modified: list[str]
    missing: list[str]
    unchanged: int
    unknown_theme: list[str]
    unclassified: list[str]
    by_theme: dict[str, int]
    by_type: dict[str, int]
    hashed: int
    needs_attention: int

    @classmethod
    def from_report(cls, report: ScanReport) -> "ScanReportRead":
        return cls(**vars(report), needs_attention=report.needs_attention)


class ImportRequest(BaseModel):
    """Parámetros de una importación.

    El alcance de consentimiento se declara aquí y no se infiere del material.
    Su valor por defecto es el más protector: una pieza importada no alimenta al
    chatbot hasta que alguien lo autorice explícitamente.
    """

    theme_slug: str | None = None
    consent_scope: ConsentScope = ConsentScope.NO_AI
    attribution: Attribution = Attribution.ANONYMOUS
    sensitivity: Sensitivity = Sensitivity.NORMAL
    document_ids: list[uuid.UUID] | None = None
    limit: int = 500


class ImportReportRead(BaseModel):
    created: list[str]
    skipped: list[str]
    failed: list[tuple[str, str]]
    awaiting_transcription: list[str]
    by_theme: dict[str, int]
    by_type: dict[str, int]
    total: int

    @classmethod
    def from_report(cls, report: ImportReport) -> "ImportReportRead":
        return cls(**vars(report), total=report.total)


def get_service(session: AsyncSession = Depends(get_session)) -> ArchiveService:
    return ArchiveService(session, Path(settings.archive_root))


def get_importer(
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
    account: Account = Depends(require_admin),
) -> ArchiveImporter:
    return ArchiveImporter(session, Path(settings.archive_root), storage, actor=account)


@router.post(
    "/scan",
    response_model=ScanReportRead,
    summary="Escanear el archivo y actualizar el registro de ingesta",
    description=(
        "Recorre la carpeta del archivo, detecta qué documentos son nuevos, cuáles "
        "cambiaron desde la última vez y cuáles desaparecieron. **No importa nada al "
        "catálogo**: la importación es una decisión aparte, porque cada pieza necesita "
        "que alguien defina su alcance de consentimiento antes de entrar.\n\n"
        "No modifica el material original bajo ninguna circunstancia."
    ),
)
async def scan_archive(
    rehash_all: bool = Query(
        default=False,
        description=(
            "Recalcula el hash de todos los documentos en lugar de omitir aquellos "
            "cuyo tamaño y fecha de modificación no cambiaron. Más lento y más seguro."
        ),
    ),
    _: Account = Depends(require_admin),
    service: ArchiveService = Depends(get_service),
) -> ScanReportRead:
    return ScanReportRead.from_report(await service.scan(rehash_all=rehash_all))


@router.get(
    "/documents",
    response_model=list[ArchiveDocumentRead],
    summary="Listar documentos del registro de ingesta",
    description=(
        "Permite ver qué está detectado pero sin importar, qué se importó y qué "
        "cambió o desapareció."
    ),
)
async def list_documents(
    theme: str | None = Query(default=None),
    status: DocumentStatus | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _: Account = Depends(get_current_account),
    service: ArchiveService = Depends(get_service),
) -> list[ArchiveDocumentRead]:
    documents = await service.list_documents(
        theme_slug=theme, status=status, limit=limit, offset=offset
    )
    return [ArchiveDocumentRead.model_validate(d) for d in documents]


@router.get(
    "/summary",
    response_model=dict[str, int],
    summary="Conteo de documentos por estado",
)
async def summary(
    _: Account = Depends(get_current_account),
    service: ArchiveService = Depends(get_service),
) -> dict[str, int]:
    return await service.summary()


@router.post(
    "/import",
    response_model=ImportReportRead,
    summary="Importar documentos detectados al catálogo",
    description=(
        "Convierte documentos pendientes en piezas de contenido en estado borrador, "
        "conservando la ruta de origen como procedencia.\n\n"
        "Es idempotente: ejecutarlo dos veces no crea duplicados. Un documento que "
        "falla se marca con su causa y no interrumpe el resto del lote. El material "
        "original nunca se mueve ni se modifica: el almacenamiento recibe una copia."
    ),
)
async def import_documents(
    payload: ImportRequest,
    importer: ArchiveImporter = Depends(get_importer),
) -> ImportReportRead:
    report = await importer.import_documents(
        theme_slug=payload.theme_slug,
        consent_scope=payload.consent_scope,
        attribution=payload.attribution,
        sensitivity=payload.sensitivity,
        document_ids=payload.document_ids,
        limit=payload.limit,
    )
    return ImportReportRead.from_report(report)
