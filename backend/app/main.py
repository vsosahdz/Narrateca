"""Punto de entrada de la API de NarraTECa."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
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


def status_for(exc: DomainError) -> int:
    """Código HTTP de un error de dominio, respetando la herencia.

    Se recorre la jerarquía en lugar de buscar el tipo exacto. Con búsqueda
    exacta, una subclase —por ejemplo `PersonaNotAvailableError`, que extiende
    `PermissionDeniedError`— no aparecía en el mapa y caía al 400 genérico. El
    síntoma es engañoso: la aplicación responde, pero con un código que dice
    «tu petición está mal formada» cuando lo que ocurre es que no tienes
    permiso.
    """
    for clase in type(exc).__mro__:
        if clase in ERROR_STATUS:
            return ERROR_STATUS[clase]
    return status.HTTP_400_BAD_REQUEST


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=status_for(exc), content={"detail": exc.message})


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


@app.get(
    "/health",
    tags=["Sistema"],
    summary="El proceso está vivo",
    description=(
        "Responde en cuanto el proceso atiende peticiones. **No comprueba las "
        "dependencias**: sirve para saber si hay que reiniciar el contenedor, no "
        "si puede atender tráfico. Para eso está `/ready`."
    ),
)
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get(
    "/ready",
    tags=["Sistema"],
    summary="El servicio puede atender tráfico",
    description=(
        "Verifica que la base de datos responde. Es el endpoint que debe usar la "
        "sonda de arranque: un proceso vivo que no alcanza su base devuelve 200 en "
        "`/health` y recibiría tráfico que solo puede fallar."
    ),
    responses={503: {"description": "Una dependencia no responde."}},
)
async def ready() -> JSONResponse:
    try:
        async with engine.connect() as conexion:
            await conexion.execute(text("SELECT 1"))
    except Exception as error:
        # El detalle va al registro, no a la respuesta: un mensaje de conexión
        # puede incluir el nombre del servidor y el usuario de la base.
        logging.getLogger(__name__).error("La base de datos no responde: %s", error)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "dependency": "database"},
        )

    return JSONResponse(content={"status": "ready", "environment": settings.environment})


app.include_router(api_router, prefix=settings.api_v1_prefix)
