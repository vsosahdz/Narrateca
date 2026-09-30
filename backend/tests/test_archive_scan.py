"""Pruebas del registro de ingesta del archivo.

Lo que se verifica es la pregunta que el equipo hará cada vez que agregue
material: **qué es nuevo, qué cambió y qué desapareció** desde la última vez.
"""

import os
import time
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.archive.models import ArchiveDocument, DocumentStatus
from app.modules.archive.scanner import classify, is_ignored, walk_archive
from app.modules.archive.service import ArchiveService
from app.modules.content.models import ContentType


@pytest.fixture
def archive_root(tmp_path: Path) -> Path:
    for theme in ("migrantes", "lgbtq", "mujeres_discapacidad", "mujeres_violencia"):
        for folder in ("testimonios", "entrevistas", "fotografias", "videos"):
            (tmp_path / theme / folder).mkdir(parents=True, exist_ok=True)
    return tmp_path


def write(root: Path, relative: str, content: str = "contenido") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --- Clasificación por ruta -------------------------------------------------


@pytest.mark.parametrize(
    ("ruta", "tema", "tipo"),
    [
        ("migrantes/testimonios/a.txt", "migrantes", ContentType.TESTIMONY),
        ("lgbtq/entrevistas/b.mp3", "lgbtq", ContentType.INTERVIEW),
        ("migrantes/fotografias/c.jpg", "migrantes", ContentType.PHOTO),
        # Alias: el material existente no siempre usa el nombre canónico.
        ("migrantes/fotos/d.jpg", "migrantes", ContentType.PHOTO),
        ("migrantes/transcripciones/e.docx", "migrantes", ContentType.TESTIMONY),
        # Sin carpeta de tipo, se deduce de la extensión.
        ("migrantes/f.mp4", "migrantes", ContentType.VIDEO),
    ],
)
def test_clasificacion_por_ruta(ruta: str, tema: str, tipo: ContentType) -> None:
    assert classify(Path(ruta)) == (tema, tipo)


def test_la_carpeta_manda_sobre_la_extension() -> None:
    """Quien organizó el archivo sabe más que la extensión del archivo."""
    _, tipo = classify(Path("migrantes/entrevistas/transcripcion.txt"))
    assert tipo is ContentType.INTERVIEW


def test_tipo_no_deducible_queda_sin_clasificar() -> None:
    _, tipo = classify(Path("migrantes/otros/hoja.xyz"))
    assert tipo is None


@pytest.mark.parametrize("nombre", [".DS_Store", "Thumbs.db", "~$borrador.docx", "._oculto"])
def test_archivos_de_sistema_se_ignoran(nombre: str) -> None:
    assert is_ignored(Path(nombre))


def test_archivos_sueltos_en_la_raiz_se_omiten(archive_root: Path) -> None:
    """Sin carpeta de comunidad no hay forma de saber a quién pertenecen."""
    write(archive_root, "suelto.txt")
    write(archive_root, "migrantes/testimonios/valido.txt")

    rutas = [found.relative_path for found in walk_archive(archive_root)]
    assert rutas == ["migrantes/testimonios/valido.txt"]


# --- Ciclo de escaneo -------------------------------------------------------


async def test_primer_escaneo_registra_todo_como_nuevo(
    session: AsyncSession, archive_root: Path
) -> None:
    write(archive_root, "migrantes/testimonios/a.txt")
    write(archive_root, "lgbtq/entrevistas/b.txt")

    report = await ArchiveService(session, archive_root).scan()

    assert report.scanned == 2
    assert len(report.new) == 2
    assert report.unchanged == 0


async def test_segundo_escaneo_no_vuelve_a_hashear(
    session: AsyncSession, archive_root: Path
) -> None:
    """El atajo por tamaño y fecha es lo que hace viable escanear horas de video."""
    write(archive_root, "migrantes/testimonios/a.txt")
    service = ArchiveService(session, archive_root)
    await service.scan()

    report = await service.scan()

    assert report.unchanged == 1
    assert report.new == []
    assert report.hashed == 0


async def test_detecta_un_documento_nuevo(session: AsyncSession, archive_root: Path) -> None:
    write(archive_root, "migrantes/testimonios/a.txt")
    service = ArchiveService(session, archive_root)
    await service.scan()

    write(archive_root, "migrantes/testimonios/b.txt")
    report = await service.scan()

    assert report.new == ["migrantes/testimonios/b.txt"]
    assert report.unchanged == 1


async def test_detecta_un_documento_modificado(session: AsyncSession, archive_root: Path) -> None:
    path = write(archive_root, "migrantes/testimonios/a.txt", "versión uno")
    service = ArchiveService(session, archive_root)
    await service.scan()

    time.sleep(1.1)  # el atajo compara segundos enteros de mtime
    path.write_text("versión dos", encoding="utf-8")
    report = await service.scan()

    assert report.modified == ["migrantes/testimonios/a.txt"]
    assert report.hashed == 1


async def test_tocar_un_archivo_sin_cambiarlo_no_lo_marca_modificado(
    session: AsyncSession, archive_root: Path
) -> None:
    """Cambiar la fecha sin cambiar el contenido no es una modificación.

    Copiar el archivo a otro disco actualiza la fecha de todo. Sin comparar el
    hash, el equipo recibiría cientos de falsos positivos.
    """
    path = write(archive_root, "migrantes/testimonios/a.txt", "igual")
    service = ArchiveService(session, archive_root)
    await service.scan()

    future = time.time() + 5
    os.utime(path, (future, future))
    report = await service.scan()

    assert report.modified == []
    assert report.unchanged == 1
    assert report.hashed == 1  # sí se releyó, pero el contenido resultó idéntico


async def test_detecta_un_documento_ausente(session: AsyncSession, archive_root: Path) -> None:
    path = write(archive_root, "migrantes/testimonios/a.txt")
    service = ArchiveService(session, archive_root)
    await service.scan()

    path.unlink()
    report = await service.scan()

    assert report.missing == ["migrantes/testimonios/a.txt"]


async def test_un_documento_que_reaparece_vuelve_a_estar_pendiente(
    session: AsyncSession, archive_root: Path
) -> None:
    path = write(archive_root, "migrantes/testimonios/a.txt", "contenido")
    service = ArchiveService(session, archive_root)
    await service.scan()
    path.unlink()
    await service.scan()

    write(archive_root, "migrantes/testimonios/a.txt", "contenido")
    await service.scan()

    documentos = await service.list_documents()
    assert documentos[0].status is DocumentStatus.DISCOVERED


async def test_reporta_carpetas_de_comunidad_no_reconocidas(
    session: AsyncSession, archive_root: Path
) -> None:
    """Es un error de organización que el equipo debe ver, no algo que adivinar."""
    write(archive_root, "comunidad_inexistente/testimonios/a.txt")

    report = await ArchiveService(session, archive_root).scan()

    assert report.unknown_theme == ["comunidad_inexistente/testimonios/a.txt"]


async def test_reporta_documentos_sin_clasificar(session: AsyncSession, archive_root: Path) -> None:
    write(archive_root, "migrantes/otros/desconocido.xyz")

    report = await ArchiveService(session, archive_root).scan()

    assert report.unclassified == ["migrantes/otros/desconocido.xyz"]


async def test_el_escaneo_no_modifica_el_material(
    session: AsyncSession, archive_root: Path
) -> None:
    """Requisito de la spec `archive-import`: el archivo es irreemplazable."""
    path = write(archive_root, "migrantes/testimonios/a.txt", "intacto")
    antes = (path.read_bytes(), path.stat().st_mtime)

    await ArchiveService(session, archive_root).scan()

    assert (path.read_bytes(), path.stat().st_mtime) == antes


async def test_conteos_por_comunidad_y_por_tipo(session: AsyncSession, archive_root: Path) -> None:
    write(archive_root, "migrantes/testimonios/a.txt")
    write(archive_root, "migrantes/testimonios/b.txt")
    write(archive_root, "lgbtq/entrevistas/c.txt")

    report = await ArchiveService(session, archive_root).scan()

    assert report.by_theme == {"migrantes": 2, "lgbtq": 1}
    assert report.by_type == {"testimony": 2, "interview": 1}


async def test_resumen_por_estado(session: AsyncSession, archive_root: Path) -> None:
    write(archive_root, "migrantes/testimonios/a.txt")
    service = ArchiveService(session, archive_root)
    await service.scan()

    assert await service.summary() == {"discovered": 1}


async def test_el_hash_identifica_material_duplicado(
    session: AsyncSession, archive_root: Path
) -> None:
    """Dos rutas con el mismo contenido comparten hash: así se detecta un
    duplicado antes de importarlo dos veces."""
    write(archive_root, "migrantes/testimonios/a.txt", "mismo contenido")
    write(archive_root, "migrantes/entrevistas/copia.txt", "mismo contenido")

    service = ArchiveService(session, archive_root)
    await service.scan()

    documentos = await service.list_documents()
    hashes = {d.content_hash for d in documentos}
    assert len(documentos) == 2
    assert len(hashes) == 1


async def test_la_estructura_de_carpetas_es_idempotente(
    session: AsyncSession, tmp_path: Path
) -> None:
    service = ArchiveService(session, tmp_path)

    primera = service.ensure_layout(["migrantes", "lgbtq"])
    segunda = service.ensure_layout(["migrantes", "lgbtq"])

    assert len(primera) == 12  # 6 tipos × 2 comunidades
    assert segunda == []


async def test_una_carpeta_por_tipo_sin_alias(session: AsyncSession, tmp_path: Path) -> None:
    """Crear `fotos` y `fotografias` a la vez confundiría al equipo sobre dónde
    debe dejar el material."""
    ArchiveService(session, tmp_path).ensure_layout(["migrantes"])

    carpetas = {p.name for p in (tmp_path / "migrantes").iterdir() if p.is_dir()}
    assert "fotografias" in carpetas
    assert "fotos" not in carpetas


async def test_el_registro_es_independiente_del_catalogo(
    session: AsyncSession, archive_root: Path
) -> None:
    """Un documento detectado y sin importar debe ser visible, no invisible."""
    write(archive_root, "migrantes/testimonios/a.txt")
    service = ArchiveService(session, archive_root)
    await service.scan()

    documento = (await service.list_documents())[0]
    assert documento.content_item_id is None
    assert documento.status is DocumentStatus.DISCOVERED
    assert documento.needs_attention is True


async def test_un_documento_importado_que_cambia_pide_revision(
    session: AsyncSession, archive_root: Path
) -> None:
    """La pieza del catálogo se construyó con una versión anterior del archivo."""
    path = write(archive_root, "migrantes/testimonios/a.txt", "uno")
    service = ArchiveService(session, archive_root)
    await service.scan()

    documento = (await service.list_documents())[0]
    documento.status = DocumentStatus.IMPORTED
    await session.flush()

    time.sleep(1.1)
    path.write_text("dos", encoding="utf-8")
    report = await service.scan()

    assert report.modified == ["migrantes/testimonios/a.txt"]
    refrescado = await session.get(ArchiveDocument, documento.id)
    assert refrescado is not None
    assert refrescado.status is DocumentStatus.MODIFIED
