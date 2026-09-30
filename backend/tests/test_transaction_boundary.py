"""El límite de la transacción pertenece al caso de uso, no al transporte.

Regresión de un defecto real: el `commit()` vivía en el desmontaje de la
dependencia de sesión, que no está garantizado a completarse antes de que la
respuesta llegue al cliente. El resultado era que quien recibía un 201 y
consultaba de inmediato podía no ver lo que acababa de crear — se reprodujo en
aproximadamente 1 de cada 40 escrituras seguidas de una lectura inmediata.

En el panel eso se habría manifestado como "lo guardé y no aparece", de forma
intermitente y por tanto casi imposible de diagnosticar desde un reporte.

Estas pruebas fijan la invariante que lo evita: al terminar un método de
servicio que modifica datos, la sesión no debe conservar trabajo pendiente.
"""

import inspect

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.modules.admin.models import Account
from app.modules.admin.service import AccountService
from app.modules.content.schemas import ContentCreate
from app.modules.content.service import ContentService
from app.modules.team.schemas import TeamMemberCreate
from app.modules.team.service import TeamService
from app.modules.themes.schemas import ThemeCreate
from app.modules.themes.service import ThemeService


def test_la_dependencia_de_sesion_no_confirma() -> None:
    """La dependencia de transporte no debe cerrar la transacción.

    Si alguien vuelve a poner el `commit()` aquí, el defecto regresa sin que
    ninguna otra prueba lo note.
    """
    source = inspect.getsource(database.get_session)
    assert "commit()" not in source, (
        "get_session no debe confirmar: el desmontaje de la dependencia puede "
        "ejecutarse después de enviar la respuesta. El commit va en el servicio."
    )


async def test_crear_contenido_no_deja_trabajo_pendiente(
    session: AsyncSession, admin_account: Account
) -> None:
    service = ContentService(session, actor=admin_account)

    await service.create(
        ContentCreate(
            theme_slug="migrantes",
            type="testimony",
            slug="limite-de-transaccion",
            title="Límite de transacción",
        )
    )

    assert not session.new, "Quedaron objetos sin escribir al terminar el caso de uso."
    assert not session.dirty, "Quedaron cambios sin confirmar al terminar el caso de uso."


async def test_publicar_no_deja_trabajo_pendiente(
    session: AsyncSession, admin_account: Account
) -> None:
    service = ContentService(session, actor=admin_account)
    item = await service.create(
        ContentCreate(
            theme_slug="migrantes",
            type="testimony",
            slug="publicar-limite",
            title="Publicar",
        )
    )

    await service.publish(item.id)

    assert not session.new
    assert not session.dirty


async def test_alta_de_tema_no_deja_trabajo_pendiente(session: AsyncSession) -> None:
    service = ThemeService(session)

    await service.create(
        ThemeCreate(
            slug="prueba_limite",
            name_es="Prueba",
            name_en="Test",
            accent_token="prueba_limite",
        )
    )

    assert not session.new
    assert not session.dirty


async def test_alta_de_integrante_no_deja_trabajo_pendiente(session: AsyncSession) -> None:
    service = TeamService(session)

    await service.create(TeamMemberCreate(full_name="Integrante", bio="Biografía."))

    assert not session.new
    assert not session.dirty


@pytest.mark.parametrize(
    ("service_cls", "methods"),
    [
        (ContentService, ["create", "update", "publish", "withdraw", "delete"]),
        (ThemeService, ["create", "update", "delete"]),
        (TeamService, ["create", "update", "delete"]),
        (AccountService, ["create", "update", "delete", "change_password"]),
    ],
)
def test_todo_metodo_que_modifica_confirma(service_cls: type, methods: list[str]) -> None:
    """Cada método de servicio que escribe debe cerrar su propia transacción."""
    for method_name in methods:
        source = inspect.getsource(getattr(service_cls, method_name))
        assert "self.session.commit()" in source, (
            f"{service_cls.__name__}.{method_name} modifica datos y no confirma. "
            "Sin el commit explícito, lo escrito puede no ser visible para la "
            "siguiente petición del cliente."
        )
