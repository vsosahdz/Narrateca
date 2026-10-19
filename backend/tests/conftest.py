"""Arnés de pruebas del backend.

Estrategia: una base de datos de pruebas real, migrada con Alembic, y una
transacción por prueba que se revierte al terminar.

Dos decisiones que vale la pena explicar:

1. **Base real, no SQLite.** El proyecto depende de pgvector y de tipos propios
   de PostgreSQL. Probar contra SQLite daría verde y produciría un sistema que
   falla en producción.

2. **Migraciones, no `create_all`.** Las cuatro comunidades se siembran en una
   migración, y varias reglas del proyecto viven en restricciones de esquema.
   Migrar en las pruebas verifica de paso que las migraciones funcionan.
"""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from urllib.parse import urlparse, urlunparse

import asyncpg
import httpx
import pytest
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import settings
from app.core.database import get_session
from app.core.security import hash_password
from app.core.storage import LocalStorage, get_storage
from app.main import app
from app.modules.admin.models import Account, Role
from app.modules.chat.llm import EchoLanguageModel, get_language_model
from app.modules.content.indexing import (
    NullIndexSynchronizer,
    get_index_synchronizer,
)
from app.modules.themes.models import Theme

TEST_DB_SUFFIX = "_test"


def _test_database_url() -> str:
    """Deriva la URL de pruebas de la de desarrollo, con sufijo `_test`."""
    parsed = urlparse(str(settings.database_url))
    database = parsed.path.lstrip("/")
    if database.endswith(TEST_DB_SUFFIX):
        return str(settings.database_url)
    return urlunparse(parsed._replace(path=f"/{database}{TEST_DB_SUFFIX}"))


TEST_DATABASE_URL = _test_database_url()


async def _recreate_database(url: str) -> None:
    """Crea la base de pruebas desde cero, conectándose a `postgres`."""
    parsed = urlparse(url)
    target = parsed.path.lstrip("/")
    # asyncpg no entiende el prefijo de dialecto de SQLAlchemy.
    admin_dsn = urlunparse(parsed._replace(scheme="postgresql", path="/postgres")).replace(
        "postgresql+asyncpg", "postgresql"
    )

    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            f'DROP DATABASE IF EXISTS "{target}" WITH (FORCE)'  # noqa: S608 - nombre derivado de configuración
        )
        await conn.execute(f'CREATE DATABASE "{target}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def prepared_database() -> Generator[str, None, None]:
    """Recrea y migra la base de pruebas una vez por ejecución."""
    asyncio.run(_recreate_database(TEST_DATABASE_URL))

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")

    yield TEST_DATABASE_URL


@pytest.fixture
async def session(prepared_database: str) -> AsyncGenerator[AsyncSession, None]:
    """Sesión envuelta en una transacción que se revierte al terminar.

    Cada prueba ve la base recién migrada, sin residuos de las anteriores, y sin
    pagar el costo de volver a migrar.
    """
    engine = create_async_engine(prepared_database, poolclass=None)
    connection = await engine.connect()
    transaction = await connection.begin()

    maker = async_sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)
    db_session = maker()

    try:
        yield db_session
    finally:
        await db_session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
def storage(tmp_path_factory: pytest.TempPathFactory) -> LocalStorage:
    """Almacenamiento en un directorio temporal.

    Las pruebas no deben escribir en el almacén de desarrollo: dejarían archivos
    sueltos que luego confunden al revisar qué material existe de verdad.
    """
    return LocalStorage(tmp_path_factory.mktemp("media"))


@pytest.fixture
def language_model() -> EchoLanguageModel:
    """Proveedor de lenguaje falso, que registra lo que se le pide.

    Ninguna prueba habla con un servicio externo. Además de ser más rápido, es
    la única forma de verificar el requisito de minimización: las pruebas
    inspeccionan `language_model.llamadas` para comprobar qué salió del sistema
    y qué no.
    """
    return EchoLanguageModel()


@pytest.fixture
def indexer() -> NullIndexSynchronizer:
    """Sincronizador de índice espía.

    Permite verificar la regla más delicada del catálogo: que retirar una pieza o
    revocar su consentimiento elimine sus fragmentos del índice del chatbot en la
    misma operación.
    """
    return NullIndexSynchronizer()


TEST_PASSWORD = "contrasena-de-prueba-larga"


async def _make_account(
    session: AsyncSession,
    *,
    email: str,
    role: Role,
    theme_slugs: list[str] | None = None,
) -> Account:
    account = Account(
        email=email,
        full_name=f"Cuenta {role.value}",
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
    )
    if theme_slugs:
        result = await session.execute(select(Theme).where(Theme.slug.in_(theme_slugs)))
        account.themes = list(result.scalars().all())
    session.add(account)
    await session.flush()
    return account


@pytest.fixture
async def app_clients(
    session: AsyncSession,
    indexer: NullIndexSynchronizer,
    storage: LocalStorage,
    language_model: EchoLanguageModel,
) -> AsyncGenerator[Callable[[], AbstractAsyncContextManager[httpx.AsyncClient]], None]:
    """Fábrica de clientes HTTP independientes contra la aplicación.

    Cada cliente tiene su **propio** frasco de cookies. Compartir uno solo entre
    la fixture anónima y la autenticada hacía que una prueba que usara ambas
    viera la misma sesión en las dos, y por tanto que una comprobación de acceso
    sin sesión pasara sin comprobar nada.

    Las sustituciones de dependencias son globales de la aplicación, así que
    todos los clientes comparten la sesión transaccional, el índice espía y el
    almacenamiento temporal.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_index_synchronizer] = lambda: indexer
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_language_model] = lambda: language_model

    stack = AsyncExitStack()

    def make() -> AbstractAsyncContextManager[httpx.AsyncClient]:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    async def create() -> httpx.AsyncClient:
        return await stack.enter_async_context(make())

    try:
        yield create
    finally:
        await stack.aclose()
        app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(app_clients) -> httpx.AsyncClient:
    """Cliente sin sesión iniciada."""
    return await app_clients()


@pytest.fixture
async def admin_account(session: AsyncSession) -> Account:
    return await _make_account(session, email="admin@tec.mx", role=Role.ADMIN)


async def _login(client: httpx.AsyncClient, email: str) -> httpx.AsyncClient:
    response = await client.post(
        "/api/v1/admin/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
async def client(app_clients, admin_account: Account) -> httpx.AsyncClient:
    """Cliente autenticado como administrador, con su propia sesión.

    Es el cliente por defecto porque la mayoría de las pruebas ejercen el panel.
    Para probar el acceso sin sesión, usar `anon_client`; para la autorización
    por tema, `editor_client`.
    """
    return await _login(await app_clients(), admin_account.email)


@pytest.fixture
async def editor_client(
    app_clients, session: AsyncSession
) -> Callable[[list[str]], Awaitable[httpx.AsyncClient]]:
    """Fábrica de clientes autenticados como editor de ciertos temas."""

    async def make(theme_slugs: list[str]) -> httpx.AsyncClient:
        account = await _make_account(
            session,
            email=f"editor-{'-'.join(theme_slugs) or 'sin-temas'}@tec.mx",
            role=Role.EDITOR,
            theme_slugs=theme_slugs,
        )
        return await _login(await app_clients(), account.email)

    return make
