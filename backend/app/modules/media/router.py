"""Carga de archivos multimedia y pistas de subtítulos.

Dos reglas viven aquí:

1. **La sensibilidad decide dónde se guarda.** El material de sensibilidad alta
   va a un ámbito privado desde el momento de subirlo, no después.
2. **Las pistas de subtítulos son editables.** La transcripción automática
   equivoca nombres propios y términos locales, y un subtítulo incorrecto en un
   testimonio no es un detalle cosmético.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError, ValidationError
from app.core.storage import Storage, build_key, get_storage, guess_content_type
from app.modules.admin.dependencies import get_current_account
from app.modules.admin.models import Account
from app.modules.content.models import Sensitivity
from app.modules.content.service import ContentService

router = APIRouter(prefix="/admin/media", tags=["Administración"])

#: Idiomas de subtítulos que el proyecto entrega para todo el audiovisual:
#: español por accesibilidad, inglés por traducción.
SUBTITLE_LOCALES = ("es", "en")


class UploadResult(BaseModel):
    media_key: str
    media_mime: str
    scope: str


class SubtitleTrack(BaseModel):
    locale: str
    key: str
    exists: bool


class SubtitleContent(BaseModel):
    content: str = Field(description="Contenido de la pista en formato WebVTT.")


def _subtitle_key(media_key: str, locale: str) -> str:
    """Clave de la pista de subtítulos asociada a un archivo de media.

    Convención compartida con el frontend: junto al archivo, con el idioma en el
    nombre. `entrevistas/ent-014.mp4` → `entrevistas/ent-014.es.vtt`.
    """
    stem = media_key.rsplit(".", 1)[0]
    return f"{stem}.{locale}.vtt"


@router.post(
    "",
    response_model=UploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Subir un archivo multimedia",
    description=(
        "El archivo se almacena en el ámbito que corresponde a su sensibilidad. "
        "El material de sensibilidad alta va a almacenamiento privado y nunca se "
        "publica en un servicio de terceros. Devuelve la clave que debe guardarse "
        "en el campo `media_key` de la pieza."
    ),
)
async def upload_media(
    theme_slug: str = Form(...),
    sensitivity: Sensitivity = Form(default=Sensitivity.NORMAL),
    file: UploadFile = File(...),
    _: Account = Depends(get_current_account),
    storage: Storage = Depends(get_storage),
) -> UploadResult:
    if not file.filename:
        raise ValidationError("El archivo no tiene nombre.")

    content_type = guess_content_type(file.filename, file.content_type)
    scope = "sensitive" if sensitivity is Sensitivity.HIGH else "public"

    key = build_key(
        scope=scope,
        theme_slug=theme_slug,
        filename=file.filename,
        content_type=content_type,
    )
    await storage.save(key, file.file)

    return UploadResult(media_key=key, media_mime=content_type, scope=scope)


@router.get(
    "/subtitles/{item_id}",
    response_model=list[SubtitleTrack],
    summary="Estado de las pistas de subtítulos de una pieza",
    description=(
        "Indica, para español e inglés, si la pista existe. Ambas son obligatorias "
        "para publicar material audiovisual."
    ),
)
async def subtitle_status(
    item_id: uuid.UUID,
    account: Account = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
) -> list[SubtitleTrack]:
    item = await ContentService(session, actor=account).get_by_id(item_id)
    if not item.media_key:
        raise NotFoundError("La pieza no tiene archivo multimedia asociado.")

    tracks = []
    for locale in SUBTITLE_LOCALES:
        key = _subtitle_key(item.media_key, locale)
        tracks.append(SubtitleTrack(locale=locale, key=key, exists=await storage.exists(key)))
    return tracks


@router.get(
    "/subtitles/{item_id}/{locale}",
    response_model=SubtitleContent,
    summary="Leer una pista de subtítulos",
)
async def read_subtitle(
    item_id: uuid.UUID,
    locale: str,
    account: Account = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
) -> SubtitleContent:
    if locale not in SUBTITLE_LOCALES:
        raise ValidationError(f"Idioma no admitido: {locale}.")

    item = await ContentService(session, actor=account).get_by_id(item_id)
    if not item.media_key:
        raise NotFoundError("La pieza no tiene archivo multimedia asociado.")

    return SubtitleContent(content=await storage.read_text(_subtitle_key(item.media_key, locale)))


@router.put(
    "/subtitles/{item_id}/{locale}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Guardar una pista de subtítulos",
    description=(
        "Sustituye la pista generada automáticamente por la versión corregida. La "
        "transcripción automática equivoca nombres propios y términos locales, y en "
        "un testimonio eso no es un detalle cosmético."
    ),
)
async def write_subtitle(
    item_id: uuid.UUID,
    locale: str,
    payload: SubtitleContent,
    account: Account = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
) -> None:
    if locale not in SUBTITLE_LOCALES:
        raise ValidationError(f"Idioma no admitido: {locale}.")
    if not payload.content.lstrip().startswith("WEBVTT"):
        raise ValidationError("La pista debe estar en formato WebVTT y comenzar con «WEBVTT».")

    service = ContentService(session, actor=account)
    item = await service.get_by_id(item_id)
    service.assert_can_edit(item.theme_id)

    if not item.media_key:
        raise NotFoundError("La pieza no tiene archivo multimedia asociado.")

    await storage.save_text(_subtitle_key(item.media_key, locale), payload.content)
