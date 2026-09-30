"""Pruebas de la sección de noticias.

Cubren los escenarios de la spec `news`. Las noticias no son una entidad aparte
sino una vista sobre el catálogo, así que lo que se verifica aquí es que esa
vista distinga correctamente el origen de cada pieza y respete las reglas de
publicación del catálogo.
"""

from typing import Any

import httpx

ADMIN = "/api/v1/admin/content"
NEWS = "/api/v1/news"


async def crear_y_publicar(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "theme_slug": "migrantes",
        "type": "news_post",
        "slug": "nota",
        "title": "Nota",
        "summary": "Resumen.",
        "attribution": "named",
        "person_name": "Equipo",
    }
    base.update(overrides)

    created = await client.post(ADMIN, json=base)
    assert created.status_code == 201, created.text
    published = await client.post(f"{ADMIN}/{created.json()['id']}/publish")
    assert published.status_code == 200, published.text
    return published.json()


async def test_la_seccion_reune_notas_propias_y_enlaces_curados(
    client: httpx.AsyncClient,
) -> None:
    await crear_y_publicar(client, slug="nota-propia", type="news_post")
    await crear_y_publicar(
        client,
        slug="enlace-curado",
        type="curated_link",
        external_url="https://ejemplo.mx/nota",
        source_name="La Jornada",
    )

    noticias = (await client.get(NEWS, params={"theme": "migrantes"})).json()

    assert {n["kind"] for n in noticias} == {"own", "curated"}


async def test_distingue_el_origen_de_cada_pieza(client: httpx.AsyncClient) -> None:
    """Escenario: quien lee debe poder distinguir nota propia de medio externo."""
    await crear_y_publicar(client, slug="propia", type="news_post")
    await crear_y_publicar(
        client,
        slug="externa",
        type="curated_link",
        external_url="https://ejemplo.mx/nota",
        source_name="El Norte",
    )

    noticias = {n["slug"]: n for n in (await client.get(NEWS)).json()}

    assert noticias["propia"]["kind"] == "own"
    assert noticias["propia"]["source_name"] is None
    assert noticias["propia"]["external_url"] is None

    assert noticias["externa"]["kind"] == "curated"
    assert noticias["externa"]["source_name"] == "El Norte"
    assert noticias["externa"]["external_url"] == "https://ejemplo.mx/nota"


async def test_no_se_republica_el_cuerpo_del_articulo_externo(
    client: httpx.AsyncClient,
) -> None:
    """El sistema guarda un resumen propio, no el artículo del medio."""
    noticia = (await client.get(NEWS)).json()
    assert all("body" not in n for n in noticia)


async def test_orden_de_la_mas_reciente_a_la_mas_antigua(client: httpx.AsyncClient) -> None:
    await crear_y_publicar(client, slug="primera")
    await crear_y_publicar(client, slug="segunda")

    noticias = (await client.get(NEWS, params={"theme": "migrantes"})).json()
    fechas = [n["published_at"] for n in noticias]

    assert fechas == sorted(fechas, reverse=True)


async def test_las_noticias_se_filtran_por_tema(client: httpx.AsyncClient) -> None:
    await crear_y_publicar(client, slug="de-migrantes", theme_slug="migrantes")
    await crear_y_publicar(client, slug="de-lgbtq", theme_slug="lgbtq")

    noticias = (await client.get(NEWS, params={"theme": "lgbtq"})).json()

    assert {n["slug"] for n in noticias} == {"de-lgbtq"}


async def test_tema_sin_noticias_devuelve_lista_vacia(client: httpx.AsyncClient) -> None:
    """La página temática omite la sección cuando esto ocurre."""
    noticias = (await client.get(NEWS, params={"theme": "mujeres_violencia"})).json()
    assert noticias == []


async def test_un_borrador_no_aparece_en_la_seccion(client: httpx.AsyncClient) -> None:
    await client.post(
        ADMIN,
        json={
            "theme_slug": "migrantes",
            "type": "news_post",
            "slug": "borrador",
            "title": "Borrador",
            "summary": "Sin publicar.",
            "attribution": "anonymous",
        },
    )

    noticias = (await client.get(NEWS, params={"theme": "migrantes"})).json()
    assert all(n["slug"] != "borrador" for n in noticias)


async def test_el_testimonio_no_entra_en_la_seccion_de_noticias(
    client: httpx.AsyncClient,
) -> None:
    await crear_y_publicar(client, slug="un-testimonio", type="testimony")

    noticias = (await client.get(NEWS, params={"theme": "migrantes"})).json()
    assert all(n["slug"] != "un-testimonio" for n in noticias)


async def test_toda_noticia_registra_al_editor_que_la_creo(
    client: httpx.AsyncClient,
) -> None:
    """Escenario: no hay agregación automática, toda pieza tiene autoría."""
    noticia = await crear_y_publicar(client, slug="con-autoria")

    auditoria = (
        await client.get("/api/v1/admin/audit", params={"entity_id": noticia["id"]})
    ).json()

    assert any(e["action"] == "create" for e in auditoria)
    assert all(e["account_email"] for e in auditoria)
