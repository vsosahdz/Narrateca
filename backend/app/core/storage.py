"""Almacenamiento de archivos multimedia.

El material se separa en dos ámbitos desde el momento de guardarlo:

- `sensitive`: testimonios y material de sensibilidad alta. En producción va a un
  bucket privado al que solo se accede por URL firmada. Nunca se publica en un
  servicio de terceros.
- `public`: material de difusión general.

La separación ocurre en la ruta del archivo y no solo en un campo de la base,
para que una configuración mal puesta de permisos no exponga material sensible
por estar mezclado con el resto.
"""

import mimetypes
import re
import unicodedata
import uuid
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import BinaryIO, Literal

from app.core.config import settings
from app.core.errors import ValidationError

Scope = Literal["sensitive", "public"]

#: Tipos aceptados. Es una lista de permitidos y no de prohibidos: cualquier
#: formato no contemplado se rechaza en lugar de almacenarse a ciegas.
ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/mp4": ".m4a",
    "application/pdf": ".pdf",
    "text/vtt": ".vtt",
}

MAX_FILENAME_LENGTH = 80


def slugify(value: str) -> str:
    """Normaliza un nombre de archivo a algo seguro para una ruta y una URL."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return (cleaned or "archivo")[:MAX_FILENAME_LENGTH]


def build_key(*, scope: Scope, theme_slug: str, filename: str, content_type: str) -> str:
    """Construye la ruta de almacenamiento de un archivo.

    Incluye un identificador aleatorio para que subir dos archivos con el mismo
    nombre no sobrescriba el primero, que es una forma silenciosa de perder
    material del archivo.
    """
    extension = ALLOWED_MIME_TYPES.get(content_type)
    if extension is None:
        raise ValidationError(
            f"Tipo de archivo no admitido: {content_type}. "
            f"Admitidos: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
        )

    stem = slugify(Path(filename).stem)
    today = date.today()
    unique = uuid.uuid4().hex[:8]

    return f"{scope}/{theme_slug}/{today:%Y/%m}/{stem}-{unique}{extension}"


class Storage(ABC):
    """Puerto de almacenamiento.

    La implementación de Cloud Storage se conecta al montar la infraestructura;
    hasta entonces, el almacenamiento local permite desarrollar y probar todo el
    flujo de carga sin depender de credenciales de nube.
    """

    @abstractmethod
    async def save(self, key: str, stream: BinaryIO) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def read_text(self, key: str) -> str: ...

    @abstractmethod
    async def save_text(self, key: str, content: str) -> None: ...


class LocalStorage(Storage):
    """Almacenamiento en disco, para desarrollo y pruebas."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def path_for(self, key: str) -> Path:
        """Ruta en disco de una clave, verificada contra saltos de directorio.

        Es pública porque la entrega de material en desarrollo necesita un
        `Path` real para poder responder peticiones por rango, que es lo que
        permite avanzar y retroceder dentro de un video.
        """
        # Se resuelve y se verifica que quede dentro de la raíz: sin esto, una
        # clave con `../` permitiría escribir o leer fuera del almacén.
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValidationError("Ruta de almacenamiento inválida.")
        return candidate

    #: Alias interno conservado para legibilidad en los métodos siguientes.
    _path = path_for

    async def save(self, key: str, stream: BinaryIO) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as destination:
            while chunk := stream.read(1024 * 1024):
                destination.write(chunk)

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    async def read_text(self, key: str) -> str:
        path = self._path(key)
        if not path.is_file():
            raise ValidationError("El archivo solicitado no existe.")
        return path.read_text(encoding="utf-8")

    async def save_text(self, key: str, content: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def guess_content_type(filename: str, declared: str | None) -> str:
    """Determina el tipo de contenido, prefiriendo el declarado si es admitido."""
    if declared in ALLOWED_MIME_TYPES:
        return declared
    guessed, _ = mimetypes.guess_type(filename)
    if guessed in ALLOWED_MIME_TYPES:
        return guessed
    raise ValidationError(f"No se pudo determinar un tipo de archivo admitido para «{filename}».")


_storage: Storage | None = None


def get_storage() -> Storage:
    """Dependencia de FastAPI que entrega el almacenamiento configurado."""
    global _storage
    if _storage is None:
        if settings.storage_backend == "local":
            _storage = LocalStorage(settings.storage_local_root)
        else:  # pragma: no cover - se implementa al montar la infraestructura
            raise NotImplementedError(
                "El almacenamiento en Cloud Storage se conecta con la infraestructura."
            )
    return _storage
