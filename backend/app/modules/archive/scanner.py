"""Recorrido del archivo físico.

Convención de carpetas:

    archivo/
    ├── <tema>/
    │   ├── <tipo>/          opcional; si falta, el tipo se deduce del formato
    │   │   └── documento.ext
    │   └── documento.ext

La primera carpeta es el tema y debe coincidir con el `slug` de una comunidad.
La segunda, si existe y es un tipo reconocido, fija el tipo de contenido.

El escaneo **no modifica nada** del material original: solo lee. Esa es una
restricción de la spec `archive-import`, y también sentido común: el archivo es
irreemplazable.
"""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.modules.content.models import ContentType

#: Carpeta que se crea para cada tipo de contenido. Es la estructura que el
#: equipo ve al abrir el archivo, así que hay exactamente una por tipo.
CANONICAL_FOLDERS: dict[ContentType, str] = {
    ContentType.TESTIMONY: "testimonios",
    ContentType.INTERVIEW: "entrevistas",
    ContentType.VIDEO: "videos",
    ContentType.PHOTO: "fotografias",
    ContentType.NEWS_POST: "noticias",
    ContentType.GEO_ITEM: "mapas",
}

#: Carpetas de segundo nivel reconocidas al clasificar. Incluye alias, porque el
#: material que ya existe no siempre usa el nombre canónico y renombrar carpetas
#: del archivo original no es algo que deba hacer el escáner.
TYPE_FOLDERS: dict[str, ContentType] = {
    **{folder: content_type for content_type, folder in CANONICAL_FOLDERS.items()},
    "fotos": ContentType.PHOTO,
    "imagenes": ContentType.PHOTO,
    "audios": ContentType.INTERVIEW,
    "transcripciones": ContentType.TESTIMONY,
}

#: Deducción por extensión, cuando la carpeta no lo dice.
EXTENSION_TYPES: dict[str, ContentType] = {
    ".jpg": ContentType.PHOTO,
    ".jpeg": ContentType.PHOTO,
    ".png": ContentType.PHOTO,
    ".webp": ContentType.PHOTO,
    ".avif": ContentType.PHOTO,
    ".mp4": ContentType.VIDEO,
    ".mov": ContentType.VIDEO,
    ".webm": ContentType.VIDEO,
    ".mp3": ContentType.INTERVIEW,
    ".wav": ContentType.INTERVIEW,
    ".m4a": ContentType.INTERVIEW,
    ".txt": ContentType.TESTIMONY,
    ".md": ContentType.TESTIMONY,
    ".docx": ContentType.TESTIMONY,
    ".pdf": ContentType.TESTIMONY,
}

#: Archivos que nunca son material del archivo.
IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"}
IGNORED_PREFIXES = ("~$", "._")

HASH_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class ScannedFile:
    """Un archivo encontrado en el árbol, sin comparar aún con el registro."""

    relative_path: str
    theme_slug: str
    detected_type: ContentType | None
    size_bytes: int
    modified_at: datetime
    absolute_path: Path


def is_ignored(path: Path) -> bool:
    if path.name in IGNORED_NAMES:
        return True
    return path.name.startswith(IGNORED_PREFIXES)


def normalize_theme_folder(folder: str) -> str:
    """Convierte el nombre de una carpeta de comunidad en el slug del tema.

    Los slugs de tema usan guion medio (`mujeres-discapacidad`). Las carpetas
    del archivo que ya existen en disco usan guion bajo, porque así se llamaban
    los slugs antes. Se aceptan ambas grafías a propósito: renombrar carpetas
    que contienen material bajo acuerdo de confidencialidad es una operación
    que debe decidir el equipo, no imponer un cambio de convención interna.
    """
    return folder.strip().lower().replace("_", "-")


def classify(relative: Path) -> tuple[str, ContentType | None]:
    """Deduce tema y tipo a partir de la ruta relativa."""
    parts = relative.parts
    theme_slug = normalize_theme_folder(parts[0]) if parts else ""

    if len(parts) > 2:
        folder = parts[1].lower()
        if folder in TYPE_FOLDERS:
            return theme_slug, TYPE_FOLDERS[folder]

    return theme_slug, EXTENSION_TYPES.get(relative.suffix.lower())


def walk_archive(root: Path) -> Iterator[ScannedFile]:
    """Recorre el árbol del archivo y produce un registro por archivo.

    Se omiten los archivos sueltos en la raíz: sin carpeta de tema no hay forma
    de saber a qué comunidad pertenecen, y adivinarlo sería peor que reportarlo.
    """
    root = root.resolve()
    if not root.is_dir():
        return

    for path in sorted(root.rglob("*")):
        if not path.is_file() or is_ignored(path):
            continue

        relative = path.relative_to(root)
        if len(relative.parts) < 2:
            continue

        theme_slug, detected_type = classify(relative)
        stat = path.stat()

        yield ScannedFile(
            relative_path=relative.as_posix(),
            theme_slug=theme_slug,
            detected_type=detected_type,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            absolute_path=path,
        )


def slug_from_path(path: Path) -> str:
    """Identificador para la dirección pública, a partir del nombre del archivo.

    Reutiliza la normalización del almacenamiento para que un mismo nombre
    produzca siempre el mismo identificador, sin acentos ni espacios.
    """
    from app.core.storage import slugify

    return slugify(path.stem)


def compute_hash(path: Path) -> str:
    """SHA-256 del contenido, leído por bloques.

    Se lee por bloques y no de una vez porque el archivo contiene horas de video:
    cargar un archivo completo en memoria para calcular su hash agotaría la
    memoria del proceso.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
