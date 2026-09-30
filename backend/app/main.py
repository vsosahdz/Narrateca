"""Punto de entrada de la API de NarraTECa."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import (
    ConflictError,
    ConsentViolationError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.openapi import API_TITLE, API_VERSION, configure_openapi
from app.modules.admin.dependencies import NotAuthenticatedError
from app.modules.admin.service import AuthenticationError
from app.modules.media.serving import router as media_serving_router

# Traducción de errores de dominio a códigos HTTP. Vive aquí, en la frontera del
# transporte, para que los servicios no conozcan HTTP.

# Starlette renombró esta constante. Se resuelve por nombre y no con un `getattr`
# con valor por defecto, porque ese valor por defecto se evalúa de inmediato y
# dispararía el aviso de obsolescencia justo lo que se intenta evitar.
UNPROCESSABLE: int = (
    status.HTTP_422_UNPROCESSABLE_CONTENT
    if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT")
    else status.HTTP_422_UNPROCESSABLE_ENTITY
)

ERROR_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: UNPROCESSABLE,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    ConsentViolationError: UNPROCESSABLE,
    # 401 y no 403: "no has iniciado sesión" y "no tienes permiso" son
    # situaciones distintas y el cliente reacciona distinto ante cada una.
    NotAuthenticatedError: status.HTTP_401_UNAUTHORIZED,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

configure_openapi(app)

# Sesión en cookie firmada y `httponly`. Un token guardado en JavaScript sería
# extraíble por cualquier script inyectado; una cookie `httponly` no lo es.
#
# En producción, el sitio y la API deben servirse bajo el mismo dominio (por
# ejemplo `/` y `/api`). Si quedaran en dominios distintos, la cookie pasaría a
# ser de terceros y requeriría `samesite=none`, que es notablemente más débil.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="narrateca_session",
    max_age=settings.session_max_age_seconds,
    same_site=settings.session_cookie_samesite,
    https_only=settings.is_production,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    code = ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=code, content={"detail": exc.message})


# Entrega de media en desarrollo local. El material sensible NO se sirve como
# archivo estático: pasa por un endpoint que verifica que su pieza esté
# publicada (ver `app.modules.media.serving`). En producción esto lo sustituye
# Cloud Storage, con CDN para lo general y URL firmada para lo sensible.
app.include_router(media_serving_router)

if settings.storage_backend == "local":
    import logging
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    # El almacenamiento local es una comodidad de desarrollo, no una función del
    # servicio. Si el directorio no puede crearse —por ejemplo en un contenedor
    # donde el proceso no es propietario de su directorio de trabajo— la API
    # debe seguir arrancando: dejar caída toda la plataforma por una carpeta de
    # archivos estáticos sería desproporcionado.
    _public_media = Path(settings.storage_local_root).resolve() / "public"
    try:
        _public_media.mkdir(parents=True, exist_ok=True)
        app.mount("/media/public", StaticFiles(directory=_public_media), name="media-public")
    except OSError as error:
        logging.getLogger(__name__).warning(
            "No se pudo preparar el almacenamiento local en %s (%s). "
            "La entrega de media estática queda deshabilitada.",
            _public_media,
            error,
        )


@app.get("/health", tags=["Sistema"], summary="Verificar estado del servicio")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


app.include_router(api_router, prefix=settings.api_v1_prefix)
