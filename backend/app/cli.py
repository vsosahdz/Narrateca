"""Comandos de operación del backend.

    python -m app.cli crear-admin --email admin@tec.mx --nombre "Nombre"
    python -m app.cli preparar-archivo
    python -m app.cli escanear-archivo
    python -m app.cli importar-archivo --tema migrantes
    python -m app.cli auditar-consentimiento

Existe porque crear cuentas desde la API exige ya ser administrador, así que la
primera cuenta no puede crearse por esa vía. Este comando es la única puerta de
arranque, y por eso solo se ejecuta con acceso al servidor y a la base de datos.
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.admin.models import Account, Role
from app.modules.archive.service import ArchiveService
from app.modules.themes.models import Theme

MIN_PASSWORD_LENGTH = 12


async def crear_admin(email: str, full_name: str, password: str) -> int:
    email = email.strip().lower()

    async with SessionLocal() as session:
        existing = await session.execute(select(Account).where(Account.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Ya existe una cuenta con el correo {email}.", file=sys.stderr)
            return 1

        account = Account(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=Role.ADMIN,
        )
        session.add(account)
        await session.commit()

    print(f"Cuenta de administrador creada: {email}")
    return 0


async def crear_editor(email: str, full_name: str, password: str, theme_slugs: list[str]) -> int:
    email = email.strip().lower()

    async with SessionLocal() as session:
        existing = await session.execute(select(Account).where(Account.email == email))
        if existing.scalar_one_or_none() is not None:
            print(f"Ya existe una cuenta con el correo {email}.", file=sys.stderr)
            return 1

        result = await session.execute(select(Theme).where(Theme.slug.in_(theme_slugs)))
        themes = list(result.scalars().all())

        faltantes = set(theme_slugs) - {t.slug for t in themes}
        if faltantes:
            print(f"Temas inexistentes: {', '.join(sorted(faltantes))}", file=sys.stderr)
            return 1

        account = Account(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=Role.EDITOR,
        )
        account.themes = themes
        session.add(account)
        await session.commit()

    print(f"Cuenta editora creada: {email} → {', '.join(theme_slugs)}")
    return 0


async def preparar_archivo() -> int:
    """Crea la estructura de carpetas del archivo."""
    async with SessionLocal() as session:
        result = await session.execute(select(Theme.slug).order_by(Theme.position))
        slugs = [slug for (slug,) in result.all()]

        service = ArchiveService(session, Path(settings.archive_root))
        created = service.ensure_layout(slugs)

    root = Path(settings.archive_root).resolve()
    print(f"Raíz del archivo: {root}")
    if created:
        print(f"Carpetas creadas ({len(created)}):")
        for path in created:
            print(f"  {path}")
    else:
        print("La estructura ya existía. No se creó nada.")
    print(
        "\nColoca cada documento bajo <comunidad>/<tipo>/. "
        "El material NUNCA debe versionarse en el repositorio."
    )
    return 0


async def escanear_archivo(rehash_all: bool) -> int:
    """Escanea el archivo y reporta qué es nuevo, qué cambió y qué falta."""
    async with SessionLocal() as session:
        service = ArchiveService(session, Path(settings.archive_root))
        report = await service.scan(rehash_all=rehash_all)

    print(f"Raíz del archivo: {report.root}")
    print(f"Archivos recorridos: {report.scanned}  (hasheados: {report.hashed})")
    print(f"Sin cambios: {report.unchanged}")
    print()

    def _listar(titulo: str, rutas: list[str], limite: int = 20) -> None:
        if not rutas:
            return
        print(f"{titulo} ({len(rutas)}):")
        for ruta in rutas[:limite]:
            print(f"  {ruta}")
        if len(rutas) > limite:
            print(f"  … y {len(rutas) - limite} más")
        print()

    _listar("NUEVOS", report.new)
    _listar("MODIFICADOS desde la importación", report.modified)
    _listar("AUSENTES (estaban registrados y ya no aparecen)", report.missing)
    _listar("Carpeta de comunidad no reconocida", report.unknown_theme)
    _listar("Sin clasificar (tipo no deducible)", report.unclassified)

    if report.by_theme:
        print("Por comunidad:")
        for tema, cuenta in sorted(report.by_theme.items()):
            print(f"  {tema:24} {cuenta}")
        print()

    if report.by_type:
        print("Por tipo:")
        for tipo, cuenta in sorted(report.by_type.items()):
            print(f"  {tipo:24} {cuenta}")
        print()

    print(f"Requieren atención: {report.needs_attention}")
    return 0


async def importar_archivo(tema: str | None, consentimiento: str, limite: int) -> int:
    """Importa documentos pendientes al catálogo, en estado borrador."""
    from app.core.storage import get_storage
    from app.modules.archive.importer import ArchiveImporter
    from app.modules.content.models import ConsentScope

    async with SessionLocal() as session:
        importer = ArchiveImporter(session, Path(settings.archive_root), get_storage())
        report = await importer.import_documents(
            theme_slug=tema,
            consent_scope=ConsentScope(consentimiento),
            limit=limite,
        )

    print(f"Documentos procesados: {report.total}")
    print(f"  creados:   {len(report.created)}")
    print(f"  omitidos:  {len(report.skipped)}  (ya importados)")
    print(f"  fallidos:  {len(report.failed)}")
    print()

    if report.failed:
        print("FALLIDOS:")
        for ruta, causa in report.failed[:20]:
            print(f"  {ruta}\n    → {causa}")
        print()

    if report.awaiting_transcription:
        print(f"Pendientes de transcripción ({len(report.awaiting_transcription)}):")
        for ruta in report.awaiting_transcription[:20]:
            print(f"  {ruta}")
        print()

    if report.by_type:
        print("Creados por tipo:")
        for tipo, cuenta in sorted(report.by_type.items()):
            print(f"  {tipo:24} {cuenta}")
        print()

    print(
        "Todas las piezas quedaron en BORRADOR con consentimiento "
        f"«{consentimiento}». Revísalas en el panel antes de publicar."
    )
    return 0


async def auditar_consentimiento(estricto: bool) -> int:
    """Verifica que el índice del chatbot no contenga nada que no deba.

    Es la garantía central del proyecto convertida en comprobación ejecutable:
    ningún fragmento del corpus puede provenir de una pieza que no autorizó su
    uso con IA, ni de una pieza retirada del sitio.

    Con `--estricto` devuelve código de error si encuentra cualquier
    divergencia, para que la integración continua pueda hacerla cumplir.
    """
    from app.modules.rag.embeddings import get_embedding_model
    from app.modules.rag.indexer import ChunkIndexer

    async with SessionLocal() as session:
        resultado = await ChunkIndexer(session, get_embedding_model()).audit()

    violaciones = (
        resultado["chunks_de_piezas_no_publicadas"] + resultado["chunks_sin_consentimiento"]
    )
    pendientes = resultado["piezas_indexables_sin_indexar"]

    print("Auditoría del índice del chatbot\n")
    print(f"  piezas indexables:              {resultado['piezas_indexables']}")
    print(f"  piezas con fragmentos:          {resultado['piezas_con_fragmentos']}")
    print(f"  pendientes de indexar:          {pendientes}")
    print()
    print("  VIOLACIONES DE CONSENTIMIENTO")
    print(f"    fragmentos de piezas no publicadas:  {resultado['chunks_de_piezas_no_publicadas']}")
    print(f"    fragmentos sin consentimiento de IA: {resultado['chunks_sin_consentimiento']}")
    print()

    if violaciones:
        print(
            f"✗ El índice contiene {violaciones} fragmento(s) que no deberían estar ahí.\n"
            "  Reconstruye el índice para corregirlo:\n"
            "    python -m app.cli reconstruir-indice",
            file=sys.stderr,
        )
        return 1

    print("✓ Ningún fragmento del índice viola el consentimiento registrado.")

    if pendientes and estricto:
        print(
            f"\n! Hay {pendientes} pieza(s) indexable(s) sin fragmentos. "
            "No es una violación, pero el chatbot no las conoce.",
        )

    return 0


async def reconstruir_indice(tema: str | None) -> int:
    """Reconstruye el índice del chatbot desde la base de datos."""
    from app.modules.rag.embeddings import get_embedding_model
    from app.modules.rag.indexer import ChunkIndexer

    async with SessionLocal() as session:
        reporte = await ChunkIndexer(session, get_embedding_model()).rebuild(theme_slug=tema)

    print(f"Piezas indexadas:          {reporte.indexed_items}")
    print(f"Fragmentos creados:        {reporte.chunks_created}")
    print(f"Omitidas sin consentimiento: {reporte.skipped_no_consent}")
    print(f"Omitidas sin texto:        {reporte.skipped_no_text}")
    return 0


def _pedir_contrasena(provided: str | None) -> str:
    """Pide la contraseña de forma interactiva si no vino por argumento.

    Pasarla como argumento la deja en el historial del shell y en la lista de
    procesos, así que el modo interactivo es el recomendado.
    """
    password = provided or getpass.getpass("Contraseña: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    return password


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    admin = sub.add_parser("crear-admin", help="Crear la primera cuenta de administrador")
    admin.add_argument("--email", required=True)
    admin.add_argument("--nombre", required=True)
    admin.add_argument("--password", help="Se pide de forma interactiva si se omite")

    editor = sub.add_parser("crear-editor", help="Crear una cuenta editora")
    editor.add_argument("--email", required=True)
    editor.add_argument("--nombre", required=True)
    editor.add_argument("--temas", required=True, help="Slugs separados por coma")
    editor.add_argument("--password", help="Se pide de forma interactiva si se omite")

    sub.add_parser("preparar-archivo", help="Crear la estructura de carpetas del archivo")

    escanear = sub.add_parser(
        "escanear-archivo", help="Detectar documentos nuevos, modificados y ausentes"
    )
    escanear.add_argument(
        "--rehash",
        action="store_true",
        help="Recalcular el hash de todo, en vez de omitir lo que no cambió de tamaño ni fecha",
    )

    importar = sub.add_parser("importar-archivo", help="Importar documentos pendientes al catálogo")
    importar.add_argument("--tema", help="Limitar a una comunidad")
    importar.add_argument(
        "--consentimiento",
        default="no_ai",
        choices=["no_ai", "site_only", "public"],
        help="Alcance de consentimiento de las piezas creadas. Por defecto el más protector.",
    )
    importar.add_argument("--limite", type=int, default=500)

    auditar = sub.add_parser(
        "auditar-consentimiento",
        help="Verificar que el índice del chatbot respeta el consentimiento registrado",
    )
    auditar.add_argument(
        "--estricto",
        action="store_true",
        help="Reportar también las piezas indexables que aún no tienen fragmentos",
    )

    reconstruir = sub.add_parser(
        "reconstruir-indice", help="Reconstruir el índice del chatbot desde la base"
    )
    reconstruir.add_argument("--tema", help="Limitar a una comunidad")

    args = parser.parse_args()

    if args.comando == "auditar-consentimiento":
        return asyncio.run(auditar_consentimiento(args.estricto))
    if args.comando == "reconstruir-indice":
        return asyncio.run(reconstruir_indice(args.tema))
    if args.comando == "importar-archivo":
        return asyncio.run(importar_archivo(args.tema, args.consentimiento, args.limite))
    if args.comando == "preparar-archivo":
        return asyncio.run(preparar_archivo())
    if args.comando == "escanear-archivo":
        return asyncio.run(escanear_archivo(args.rehash))

    password = _pedir_contrasena(args.password)

    if args.comando == "crear-admin":
        return asyncio.run(crear_admin(args.email, args.nombre, password))

    temas = [slug.strip() for slug in args.temas.split(",") if slug.strip()]
    return asyncio.run(crear_editor(args.email, args.nombre, password, temas))


if __name__ == "__main__":
    raise SystemExit(main())
