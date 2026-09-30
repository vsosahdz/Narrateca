"""Pruebas de autenticación, roles y autorización por tema.

Cubren los escenarios de la spec `admin-cms`. El énfasis está en lo que un
descuido aquí costaría: que un editor toque el contenido de una comunidad que no
le corresponde, o que la sección de administración quede accesible sin sesión.
"""

from typing import Any

import httpx
import pytest
from conftest import TEST_PASSWORD
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import Account

LOGIN = "/api/v1/admin/login"
ADMIN_CONTENT = "/api/v1/admin/content"
ACCOUNTS = "/api/v1/admin/accounts"


def content_payload(theme: str = "migrantes", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "theme_slug": theme,
        "type": "testimony",
        "slug": "una-pieza",
        "title": "Una pieza",
        "attribution": "anonymous",
    }
    base.update(overrides)
    return base


# --- Inicio de sesión -------------------------------------------------------


async def test_inicio_de_sesion_valido(
    anon_client: httpx.AsyncClient, admin_account: Account
) -> None:
    response = await anon_client.post(
        LOGIN, json={"email": admin_account.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_contrasena_incorrecta_es_rechazada(
    anon_client: httpx.AsyncClient, admin_account: Account
) -> None:
    response = await anon_client.post(
        LOGIN, json={"email": admin_account.email, "password": "incorrecta-pero-larga"}
    )
    assert response.status_code == 401


async def test_no_revela_si_el_correo_existe(
    anon_client: httpx.AsyncClient, admin_account: Account
) -> None:
    """Escenario: el error no debe permitir averiguar qué correos tienen cuenta."""
    existente = await anon_client.post(
        LOGIN, json={"email": admin_account.email, "password": "incorrecta-pero-larga"}
    )
    inexistente = await anon_client.post(
        LOGIN, json={"email": "nadie@tec.mx", "password": "incorrecta-pero-larga"}
    )

    assert existente.status_code == inexistente.status_code == 401
    assert existente.json() == inexistente.json()


async def test_la_contrasena_solo_se_guarda_como_hash(
    session: AsyncSession, admin_account: Account
) -> None:
    """Escenario: inspeccionar el registro no debe revelar la contraseña."""
    result = await session.execute(select(Account).where(Account.id == admin_account.id))
    stored = result.scalar_one()

    assert TEST_PASSWORD not in stored.password_hash
    assert stored.password_hash.startswith("$argon2id$")


async def test_la_respuesta_nunca_incluye_el_hash(
    anon_client: httpx.AsyncClient, admin_account: Account
) -> None:
    response = await anon_client.post(
        LOGIN, json={"email": admin_account.email, "password": TEST_PASSWORD}
    )
    assert "password_hash" not in response.json()
    assert "password" not in response.json()


async def test_cerrar_sesion_revoca_el_acceso(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/admin/me")).status_code == 200

    await client.post("/api/v1/admin/logout")

    assert (await client.get("/api/v1/admin/me")).status_code == 401


# --- Protección de la sección de administración -----------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", ADMIN_CONTENT),
        ("post", ADMIN_CONTENT),
        ("get", ACCOUNTS),
        ("post", ACCOUNTS),
        ("get", "/api/v1/admin/me"),
        ("get", "/api/v1/admin/audit"),
    ],
)
async def test_sin_sesion_se_deniega_el_acceso(
    anon_client: httpx.AsyncClient, method: str, path: str
) -> None:
    """Escenario: sin sesión no se expone contenido no publicado ni cuentas."""
    response = await getattr(anon_client, method)(
        path, **({"json": {}} if method == "post" else {})
    )
    assert response.status_code == 401


async def test_el_sitio_publico_no_requiere_sesion(anon_client: httpx.AsyncClient) -> None:
    """La protección cubre administración, no el sitio."""
    assert (await anon_client.get("/api/v1/content")).status_code == 200
    assert (await anon_client.get("/api/v1/themes")).status_code == 200


# --- Autorización por tema --------------------------------------------------


async def test_editor_opera_en_su_tema_asignado(editor_client) -> None:
    """Escenario: un editor de migrantes edita una pieza de migrantes."""
    client = await editor_client(["migrantes"])

    response = await client.post(ADMIN_CONTENT, json=content_payload("migrantes"))
    assert response.status_code == 201


async def test_editor_no_opera_fuera_de_su_tema(editor_client) -> None:
    """Escenario: un editor de migrantes intenta tocar mujeres y violencia."""
    client = await editor_client(["migrantes"])

    response = await client.post(ADMIN_CONTENT, json=content_payload("mujeres_violencia"))
    assert response.status_code == 403


async def test_editor_no_publica_contenido_de_otro_tema(
    client: httpx.AsyncClient, editor_client
) -> None:
    """La restricción cubre publicar, no solo crear."""
    creada = await client.post(ADMIN_CONTENT, json=content_payload("lgbtq"))
    item_id = creada.json()["id"]

    editor = await editor_client(["migrantes"])
    response = await editor.post(f"{ADMIN_CONTENT}/{item_id}/publish")
    assert response.status_code == 403


async def test_editor_no_cambia_el_consentimiento_de_otro_tema(
    client: httpx.AsyncClient, editor_client
) -> None:
    """La operación más delicada del catálogo también está restringida."""
    creada = await client.post(ADMIN_CONTENT, json=content_payload("lgbtq"))
    item_id = creada.json()["id"]

    editor = await editor_client(["migrantes"])
    response = await editor.put(f"{ADMIN_CONTENT}/{item_id}/consent", params={"scope": "public"})
    assert response.status_code == 403


async def test_editor_con_varios_temas(editor_client) -> None:
    client = await editor_client(["migrantes", "lgbtq"])

    assert (
        await client.post(ADMIN_CONTENT, json=content_payload("migrantes", slug="a"))
    ).status_code == 201
    assert (
        await client.post(ADMIN_CONTENT, json=content_payload("lgbtq", slug="b"))
    ).status_code == 201
    assert (
        await client.post(ADMIN_CONTENT, json=content_payload("mujeres_discapacidad", slug="c"))
    ).status_code == 403


@pytest.mark.parametrize(
    "theme", ["migrantes", "lgbtq", "mujeres_discapacidad", "mujeres_violencia"]
)
async def test_administrador_opera_en_cualquier_tema(client: httpx.AsyncClient, theme: str) -> None:
    """Escenario: el rol admin alcanza a las cuatro comunidades."""
    response = await client.post(
        ADMIN_CONTENT, json=content_payload(theme, slug=theme.replace("_", "-"))
    )
    assert response.status_code == 201


# --- Gestión de cuentas -----------------------------------------------------


async def test_editor_no_gestiona_cuentas(editor_client) -> None:
    """Escenario: un editor intenta crear cuentas."""
    client = await editor_client(["migrantes"])

    response = await client.post(
        ACCOUNTS,
        json={
            "email": "nueva@tec.mx",
            "full_name": "Nueva",
            "password": "contrasena-larga-valida",
            "role": "editor",
        },
    )
    assert response.status_code == 403
    assert (await client.get(ACCOUNTS)).status_code == 403


async def test_administrador_crea_una_cuenta_editora(client: httpx.AsyncClient) -> None:
    response = await client.post(
        ACCOUNTS,
        json={
            "email": "Nueva@TEC.mx",
            "full_name": "Nueva Editora",
            "password": "contrasena-larga-valida",
            "role": "editor",
            "theme_slugs": ["migrantes"],
        },
    )
    assert response.status_code == 201
    creada = response.json()
    # El correo se normaliza para que iniciar sesión no dependa de cómo se escribió.
    assert creada["email"] == "nueva@tec.mx"
    assert [t["slug"] for t in creada["themes"]] == ["migrantes"]


async def test_contrasena_corta_es_rechazada(client: httpx.AsyncClient) -> None:
    response = await client.post(
        ACCOUNTS,
        json={
            "email": "corta@tec.mx",
            "full_name": "Corta",
            "password": "corta",
            "role": "editor",
        },
    )
    assert response.status_code == 422


async def test_una_cuenta_no_puede_inhabilitarse_a_si_misma(
    client: httpx.AsyncClient, admin_account: Account
) -> None:
    """Es la forma más común de quedarse sin acceso al panel."""
    response = await client.patch(f"{ACCOUNTS}/{admin_account.id}", json={"is_active": False})
    assert response.status_code == 422


async def test_una_cuenta_no_puede_degradarse_a_si_misma(
    client: httpx.AsyncClient, admin_account: Account
) -> None:
    response = await client.patch(f"{ACCOUNTS}/{admin_account.id}", json={"role": "editor"})
    assert response.status_code == 422


async def test_inhabilitar_una_cuenta_corta_su_sesion_de_inmediato(
    client: httpx.AsyncClient, session: AsyncSession, editor_client
) -> None:
    """La cuenta se recarga en cada petición, no se confía en la cookie."""
    editor = await editor_client(["migrantes"])
    assert (await editor.get("/api/v1/admin/me")).status_code == 200

    result = await session.execute(select(Account).where(Account.email.like("editor-%")))
    account = result.scalars().first()
    assert account is not None
    account.is_active = False
    await session.flush()

    assert (await editor.get("/api/v1/admin/me")).status_code == 401


# --- Auditoría --------------------------------------------------------------


async def test_se_registra_quien_publico_y_cuando(client: httpx.AsyncClient) -> None:
    """Escenario: trazabilidad de una acción administrativa."""
    creada = await client.post(ADMIN_CONTENT, json=content_payload())
    item_id = creada.json()["id"]
    await client.post(f"{ADMIN_CONTENT}/{item_id}/publish")

    entradas = (await client.get("/api/v1/admin/audit", params={"entity_id": item_id})).json()

    acciones = {e["action"] for e in entradas}
    assert {"create", "publish"} <= acciones
    assert all(e["account_email"] == "admin@tec.mx" for e in entradas)
    assert all(e["created_at"] for e in entradas)


async def test_el_cambio_de_consentimiento_guarda_valor_anterior_y_nuevo(
    client: httpx.AsyncClient,
) -> None:
    """Es justo lo que se querrá auditar si alguien pregunta por una pieza."""
    creada = await client.post(ADMIN_CONTENT, json=content_payload())
    item_id = creada.json()["id"]

    await client.put(f"{ADMIN_CONTENT}/{item_id}/consent", params={"scope": "public"})

    entradas = (await client.get("/api/v1/admin/audit", params={"entity_id": item_id})).json()
    consentimiento = next(e for e in entradas if e["action"] == "set_consent_scope")

    assert consentimiento["details"] == {"from": "no_ai", "to": "public"}
