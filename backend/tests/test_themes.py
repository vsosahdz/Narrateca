"""Pruebas del módulo de temas.

Cubren el requisito de `content-catalog` sobre que los temas sean datos: dar de
alta una comunidad nueva no debe requerir cambios de código.
"""

import re

import httpx
import pytest

THEME_SLUGS = {"migrantes", "lgbtq", "mujeres-discapacidad", "mujeres-violencia"}


async def test_health(client: httpx.AsyncClient) -> None:
    """`/health` responde con solo estar vivo el proceso."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_ready_confirma_la_base_de_datos(client: httpx.AsyncClient) -> None:
    """`/ready` responde 200 cuando la base contesta."""
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


async def test_ready_responde_503_con_la_base_caida(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Es la razón de existir del endpoint, así que se prueba el caso malo.

    Con la base inalcanzable, `/health` sigue devolviendo 200 —el proceso está
    vivo— y `/ready` devuelve 503. Si esta distinción se perdiera, Cloud Run
    enviaría tráfico a una instancia que solo puede fallar.
    """
    from app import main

    class MotorCaido:
        """`AsyncEngine.connect` es de solo lectura, así que se sustituye entero."""

        def connect(self) -> None:
            raise OSError("la base no responde")

    monkeypatch.setattr(main, "engine", MotorCaido())

    assert (await client.get("/health")).status_code == 200

    response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json()["dependency"] == "database"

    # El motivo real no viaja al cliente: un mensaje de conexión puede incluir
    # el servidor y el usuario de la base.
    assert "la base no responde" not in response.text


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
        # Un nombre de token, no un valor: minúsculas, dígitos y guion medio.
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", accent), (
            f"{theme['slug']} no guarda un nombre de token"
        )


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
        "slug": "personas-mayores",
        "name_es": "Personas mayores",
        "name_en": "Older adults",
        "accent_token": "personas-mayores",
        "position": 5,
    }

    created = await client.post("/api/v1/themes", json=payload)
    assert created.status_code == 201

    listed = await client.get("/api/v1/themes")
    assert "personas-mayores" in {theme["slug"] for theme in listed.json()}


async def test_slug_duplicado_devuelve_conflicto(client: httpx.AsyncClient) -> None:
    payload = {
        "slug": "migrantes",
        "name_es": "Duplicado",
        "name_en": "Duplicate",
        "accent_token": "migrantes",
    }

    response = await client.post("/api/v1/themes", json=payload)
    assert response.status_code == 409


@pytest.mark.parametrize(
    "slug",
    [
        "Con Mayúsculas",
        "con espacio",
        "",
        # El guion bajo se rechaza desde que los slugs de tema se unificaron con
        # los de contenido. Admitir las dos grafías habría dejado la
        # unificación en papel mojado: el próximo tema volvería a traer la otra.
        "con_guion_bajo",
        "-empieza-con-guion",
        "termina-con-guion-",
        "doble--guion",
    ],
)
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
