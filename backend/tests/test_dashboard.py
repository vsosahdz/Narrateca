"""Pruebas del panel de control.

Lo que se verifica es que el panel diga la verdad: que distinga publicar de
alimentar al chatbot, que haga visible el trabajo pendiente, y que no invente
ceros para lo que todavía no puede medirse.
"""

from typing import Any

import httpx
import pytest

DASHBOARD = "/api/v1/admin/dashboard"
CONTENT = "/api/v1/admin/content"


async def crear(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "theme_slug": "migrantes",
        "type": "testimony",
        "slug": "pieza",
        "title": "Pieza",
        "attribution": "anonymous",
    }
    base.update(overrides)
    response = await client.post(CONTENT, json=base)
    assert response.status_code == 201, response.text
    return response.json()


def tema(data: dict[str, Any], slug: str) -> dict[str, Any]:
    return next(t for t in data["themes"] if t["theme_slug"] == slug)


# --- Acceso -----------------------------------------------------------------


async def test_requiere_sesion(anon_client: httpx.AsyncClient) -> None:
    assert (await anon_client.get(DASHBOARD)).status_code == 401


async def test_un_editor_no_accede(editor_client) -> None:
    """El panel muestra el archivo completo: es información de administración."""
    client = await editor_client(["migrantes"])
    assert (await client.get(DASHBOARD)).status_code == 403


# --- Cobertura --------------------------------------------------------------


async def test_incluye_las_cuatro_comunidades_aunque_esten_vacias(
    client: httpx.AsyncClient,
) -> None:
    """Una comunidad sin contenido debe verse como vacía, no desaparecer."""
    data = (await client.get(DASHBOARD)).json()

    assert {t["theme_slug"] for t in data["themes"]} == {
        "migrantes",
        "lgbtq",
        "mujeres_discapacidad",
        "mujeres_violencia",
    }
    assert all(t["total"] == 0 for t in data["themes"])


async def test_distingue_publicar_de_alimentar_al_chatbot(
    client: httpx.AsyncClient,
) -> None:
    """Es la distinción central del proyecto y el panel debe hacerla evidente."""
    publicada_sin_ia = await crear(client, slug="a", consent_scope="no_ai")
    publicada_con_ia = await crear(client, slug="b", consent_scope="public")
    await client.post(f"{CONTENT}/{publicada_sin_ia['id']}/publish")
    await client.post(f"{CONTENT}/{publicada_con_ia['id']}/publish")

    data = (await client.get(DASHBOARD)).json()
    migrantes = tema(data, "migrantes")

    assert migrantes["published"] == 2
    assert migrantes["indexable"] == 1
    assert migrantes["excluded_no_ai"] == 1


async def test_una_pieza_sin_publicar_no_cuenta_como_indexable(
    client: httpx.AsyncClient,
) -> None:
    """Consentimiento amplio no basta: hace falta estar publicada."""
    await crear(client, slug="borrador", consent_scope="public")

    data = (await client.get(DASHBOARD)).json()

    assert tema(data, "migrantes")["draft"] == 1
    assert tema(data, "migrantes")["indexable"] == 0


async def test_retirar_una_pieza_la_saca_del_corpus(client: httpx.AsyncClient) -> None:
    pieza = await crear(client, slug="a", consent_scope="public")
    await client.post(f"{CONTENT}/{pieza['id']}/publish")
    await client.post(f"{CONTENT}/{pieza['id']}/withdraw")

    data = (await client.get(DASHBOARD)).json()
    migrantes = tema(data, "migrantes")

    assert migrantes["withdrawn"] == 1
    assert migrantes["indexable"] == 0


async def test_los_totales_suman_las_comunidades(client: httpx.AsyncClient) -> None:
    a = await crear(client, slug="a", theme_slug="migrantes", consent_scope="public")
    b = await crear(client, slug="b", theme_slug="lgbtq", consent_scope="public")
    await client.post(f"{CONTENT}/{a['id']}/publish")
    await client.post(f"{CONTENT}/{b['id']}/publish")

    data = (await client.get(DASHBOARD)).json()

    assert data["total_items"] == 2
    assert data["total_published"] == 2
    assert data["total_indexable"] == 2


# --- Trabajo pendiente ------------------------------------------------------


async def test_visibiliza_las_piezas_bloqueadas_por_falta_de_texto_alternativo(
    client: httpx.AsyncClient,
) -> None:
    """Es trabajo concreto que impide publicar, y debe verse sin buscarlo."""
    await crear(client, slug="foto", type="photo", alt_text=None)

    data = (await client.get(DASHBOARD)).json()

    assert tema(data, "migrantes")["blocked_missing_alt_text"] == 1
    assert any(a["level"] == "blocking" for a in data["alerts"])


async def test_una_foto_con_texto_alternativo_no_aparece_como_bloqueada(
    client: httpx.AsyncClient,
) -> None:
    await crear(client, slug="foto", type="photo", alt_text="Mujer junto a una ventana")

    data = (await client.get(DASHBOARD)).json()

    assert tema(data, "migrantes")["blocked_missing_alt_text"] == 0


async def test_avisa_de_comunidades_sin_contenido_publicado(
    client: httpx.AsyncClient,
) -> None:
    data = (await client.get(DASHBOARD)).json()

    aviso = next(a for a in data["alerts"] if "comunidades sin contenido" in a["message"])
    assert aviso["count"] == 4


async def test_desglose_por_tipo(client: httpx.AsyncClient) -> None:
    await crear(client, slug="a", type="testimony")
    await crear(client, slug="b", type="testimony")
    await crear(client, slug="c", type="interview")

    data = (await client.get(DASHBOARD)).json()
    tipos = {t["type"]: t["count"] for t in data["types"]}

    assert tipos == {"testimony": 2, "interview": 1}


# --- Actividad --------------------------------------------------------------


async def test_muestra_la_actividad_reciente(client: httpx.AsyncClient) -> None:
    pieza = await crear(client, slug="a")
    await client.post(f"{CONTENT}/{pieza['id']}/publish")

    data = (await client.get(DASHBOARD)).json()
    acciones = {e["action"] for e in data["recent_activity"]}

    assert {"create", "publish"} <= acciones
    assert all(e["account_email"] for e in data["recent_activity"])


# --- Honestidad sobre lo que no se puede medir ------------------------------


@pytest.mark.parametrize(
    "seccion", ["personas", "conversaciones", "sin_respuesta", "fragmentos", "contencion"]
)
async def test_declara_las_secciones_sin_datos(client: httpx.AsyncClient, seccion: str) -> None:
    """Reportar cero haría creer que nadie usa el chatbot; lo que ocurre es que
    todavía no existe. La diferencia importa para quien lee el panel."""
    data = (await client.get(DASHBOARD)).json()

    pendientes = {p["key"]: p for p in data["pending_sections"]}
    assert seccion in pendientes
    assert pendientes[seccion]["reason"]


async def test_ninguna_seccion_pendiente_reporta_cero(client: httpx.AsyncClient) -> None:
    """El panel no debe contener un conteo para algo que no puede medir."""
    data = (await client.get(DASHBOARD)).json()

    claves = set(data.keys())
    assert "conversations" not in claves
    assert "total_conversations" not in claves
