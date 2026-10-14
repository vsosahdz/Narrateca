"""Entrega de archivos multimedia.

Los dos ámbitos se entregan de forma distinta a propósito:

- **`public/`**: servido como archivo estático. Es material de difusión general
  y la ruta directa es la más eficiente.
- **`sensitive/`**: servido por un endpoint que verifica que la pieza dueña del
  archivo esté publicada. Sin esa comprobación, el material de un testimonio
  retirado seguiría siendo accesible para quien conserve la dirección, que es
  precisamente lo que retirar una pieza debe impedir.

En producción este módulo se sustituye por Cloud Storage: el material general
detrás de CDN y el sensible mediante URL firmada de vigencia corta. La regla de
negocio —que retirar una pieza retire también su material— se conserva igual.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.core.storage import LocalStorage, Storage, get_storage
from app.modules.admin.dependencies import SESSION_KEY
from app.modules.content.models import ContentItem, PublicationStatus

router = APIRouter(prefix="/media", tags=["Sistema"], include_in_schema=False)

NOT_AVAILABLE = "El archivo solicitado no está disponible."


@router.get("/sensitive/{key:path}")
async def serve_sensitive_media(
    key: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    storage: Storage = Depends(get_storage),
) -> FileResponse:
    """Entrega material sensible solo si su pieza está publicada.

    Una sesión de administración activa puede verlo en cualquier estado, para
    poder revisar un borrador antes de publicarlo.
    """
    media_key = f"sensitive/{key}"

    result = await session.execute(select(ContentItem).where(ContentItem.media_key == media_key))
    item = result.unique().scalar_one_or_none()
    if item is None:
        raise NotFoundError(NOT_AVAILABLE)

    is_staff = bool(request.session.get(SESSION_KEY))
    if item.status is not PublicationStatus.PUBLISHED and not is_staff:
        # Mismo error que un archivo inexistente: distinguirlos permitiría
        # confirmar que una pieza retirada existió.
        raise NotFoundError(NOT_AVAILABLE)

    # Se usa el almacenamiento inyectado y no la configuración: leer la ruta de
    # `settings` haría que este endpoint ignorara cualquier sustitución del
    # almacén, empezando por el directorio temporal que usan las pruebas.
    if not isinstance(storage, LocalStorage):  # pragma: no cover
        raise NotFoundError(NOT_AVAILABLE)

    path = storage.path_for(media_key)
    if not path.is_file():
        raise NotFoundError(NOT_AVAILABLE)

    return FileResponse(path, media_type=item.media_mime or "application/octet-stream")
