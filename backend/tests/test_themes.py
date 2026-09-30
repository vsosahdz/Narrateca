"""Pruebas del módulo de temas.

Cubren el requisito de `content-catalog` sobre que los temas sean datos: dar de
alta una comunidad nueva no debe requerir cambios de código.
"""

import httpx
import pytest

THEME_SLUGS = {"migrantes", "lgbtq", "mujeres_discapacidad", "mujeres_violencia"}


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_las_cuatro_comunidades_estan_sembradas(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/themes")
    assert response.status_code == 200

    slugs = {theme["slug"] for theme in response.json()}
    assert slugs == THEME_SLUGS


async def test_cada_tema_tiene_nombre_en_ambos_idiomas(client: httpx.AsyncClient) -> None:
    """La interfaz es bilingüe, así que el nombre del tema debe existir en ambos."""
    response = await client.get("/api/v1/themes")

    for theme in response.json():
        assert theme["name_es"], f"{theme['slug']} sin nombre en español"
        assert theme["name_en"], f"{theme['slug']} sin nombre en inglés"


async def test_el_acento_es_un_token_no_un_color(client: httpx.AsyncClient) -> None:
    """La paleta vive en el código del frontend (spec `design-tokens`).

    La base de datos guarda el *nombre* del token de acento, nunca un color
    literal: si guardara un color, sustituir la paleta dejaría de ser editar dos
    archivos y pasaría a ser una migración de datos.
    """
    response = await client.get("/api/v1/themes")

    for theme in response.json():
        accent = theme["accent_token"]
        assert not accent.startswith("#"), f"{theme['slug']} guarda un color literal"
        assert accent.isidentifier() or "_" in accent


async def test_detalle_por_slug(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/themes/migrantes")
    assert response.status_code == 200
    assert response.json()["name_es"] == "Migrantes"


async def test_tema_inexistente_devuelve_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/themes/no-existe")
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_alta_de_una_quinta_comunidad_sin_cambios_de_codigo(
    client: httpx.AsyncClient,
) -> None:
    """Escenario de `content-catalog`: alta de una comunidad nueva."""
    payload = {
        "slug": "personas_mayores",
        "name_es": "Personas mayores",
        "name_en": "Older adults",
        "accent_token": "personas_mayores",
        "position": 5,
    }

    created = await client.post("/api/v1/themes", json=payload)
    assert created.status_code == 201

    listed = await client.get("/api/v1/themes")
    assert "personas_mayores" in {theme["slug"] for theme in listed.json()}


async def test_slug_duplicado_devuelve_conflicto(client: httpx.AsyncClient) -> None:
    payload = {
        "slug": "migrantes",
        "name_es": "Duplicado",
        "name_en": "Duplicate",
        "accent_token": "migrantes",
    }

    response = await client.post("/api/v1/themes", json=payload)
    assert response.status_code == 409


@pytest.mark.parametrize("slug", ["Con Mayúsculas", "con-guiones", "con espacio", ""])
async def test_slug_invalido_es_rechazado(client: httpx.AsyncClient, slug: str) -> None:
    """El slug se usa en rutas y como partición del índice vectorial."""
    response = await client.post(
        "/api/v1/themes",
        json={
            "slug": slug,
            "name_es": "X",
            "name_en": "X",
            "accent_token": "x",
        },
    )
    assert response.status_code == 422
