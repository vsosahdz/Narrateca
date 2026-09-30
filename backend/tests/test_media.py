"""Pruebas de carga y entrega de material multimedia.

Cubren dos reglas de la spec `public-site` y una del catálogo:

- La sensibilidad decide el ámbito de almacenamiento desde el momento de subir.
- El material sensible de una pieza no publicada o retirada no es accesible.
- Solo se admiten tipos de archivo de una lista de permitidos.
"""

from typing import Any

import httpx
import pytest

from app.core.errors import ValidationError
from app.core.storage import LocalStorage, build_key, slugify

MEDIA = "/api/v1/admin/media"
CONTENT = "/api/v1/admin/content"

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def subir(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    data = {"theme_slug": "migrantes", "sensitivity": "normal"}
    data.update({k: v for k, v in overrides.items() if k != "file"})
    files = overrides.get("file", ("foto.png", PNG, "image/png"))

    response = await client.post(MEDIA, data=data, files={"file": files})
    assert response.status_code == 201, response.text
    return response.json()


# --- Ámbito de almacenamiento ----------------------------------------------


async def test_material_general_va_al_ambito_publico(client: httpx.AsyncClient) -> None:
    result = await subir(client, sensitivity="normal")
    assert result["scope"] == "public"
    assert result["media_key"].startswith("public/")


async def test_material_sensible_va_al_ambito_privado(client: httpx.AsyncClient) -> None:
    """La separación ocurre en la ruta, no solo en un campo de la base."""
    result = await subir(
        client,
        theme_slug="mujeres_violencia",
        sensitivity="high",
        file=("testimonio.mp4", b"\x00" * 64, "video/mp4"),
    )
    assert result["scope"] == "sensitive"
    assert result["media_key"].startswith("sensitive/")


async def test_la_ruta_incluye_el_tema(client: httpx.AsyncClient) -> None:
    result = await subir(client, theme_slug="lgbtq")
    assert "/lgbtq/" in result["media_key"]


async def test_dos_archivos_con_el_mismo_nombre_no_se_pisan(
    client: httpx.AsyncClient,
) -> None:
    """Sobrescribir sería una forma silenciosa de perder material del archivo."""
    primero = await subir(client)
    segundo = await subir(client)
    assert primero["media_key"] != segundo["media_key"]


async def test_tipo_de_archivo_no_admitido_se_rechaza(client: httpx.AsyncClient) -> None:
    response = await client.post(
        MEDIA,
        data={"theme_slug": "migrantes", "sensitivity": "normal"},
        files={"file": ("script.sh", b"#!/bin/sh", "application/x-sh")},
    )
    assert response.status_code == 422


async def test_subir_requiere_sesion(anon_client: httpx.AsyncClient) -> None:
    response = await anon_client.post(
        MEDIA,
        data={"theme_slug": "migrantes", "sensitivity": "normal"},
        files={"file": ("foto.png", PNG, "image/png")},
    )
    assert response.status_code == 401


# --- Entrega según estado de publicación -----------------------------------


async def _pieza_sensible(client: httpx.AsyncClient) -> tuple[str, str]:
    subida = await subir(
        client,
        theme_slug="mujeres_violencia",
        sensitivity="high",
        file=("t.mp4", b"\x00" * 64, "video/mp4"),
    )
    creada = await client.post(
        CONTENT,
        json={
            "theme_slug": "mujeres_violencia",
            "type": "video",
            "slug": "video-sensible",
            "title": "Video sensible",
            "attribution": "anonymous",
            "sensitivity": "high",
            "media_key": subida["media_key"],
            "media_mime": "video/mp4",
        },
    )
    assert creada.status_code == 201, creada.text
    return creada.json()["id"], f"/media/{subida['media_key']}"


async def test_material_sensible_de_un_borrador_no_es_accesible(
    client: httpx.AsyncClient, anon_client: httpx.AsyncClient
) -> None:
    _, url = await _pieza_sensible(client)
    assert (await anon_client.get(url)).status_code == 404


async def test_material_sensible_publicado_si_es_accesible(
    client: httpx.AsyncClient, anon_client: httpx.AsyncClient
) -> None:
    item_id, url = await _pieza_sensible(client)
    await client.post(f"{CONTENT}/{item_id}/publish")

    assert (await anon_client.get(url)).status_code == 200


async def test_retirar_una_pieza_retira_tambien_su_material(
    client: httpx.AsyncClient, anon_client: httpx.AsyncClient
) -> None:
    """Sin esto, el material de un testimonio retirado seguiría accesible para
    quien conserve la dirección, que es justo lo que retirar debe impedir."""
    item_id, url = await _pieza_sensible(client)
    await client.post(f"{CONTENT}/{item_id}/publish")
    assert (await anon_client.get(url)).status_code == 200

    await client.post(f"{CONTENT}/{item_id}/withdraw")

    assert (await anon_client.get(url)).status_code == 404


async def test_una_sesion_de_administracion_ve_el_borrador(
    client: httpx.AsyncClient,
) -> None:
    """Para poder revisar el material antes de publicarlo."""
    _, url = await _pieza_sensible(client)
    assert (await client.get(url)).status_code == 200


# --- Pistas de subtítulos ---------------------------------------------------


async def test_estado_de_pistas_de_una_pieza_recien_subida(
    client: httpx.AsyncClient,
) -> None:
    item_id, _ = await _pieza_sensible(client)

    pistas = (await client.get(f"{MEDIA}/subtitles/{item_id}")).json()

    assert {p["locale"] for p in pistas} == {"es", "en"}
    assert all(p["exists"] is False for p in pistas)


async def test_guardar_y_leer_una_pista(client: httpx.AsyncClient) -> None:
    item_id, _ = await _pieza_sensible(client)
    contenido = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nNo dormí en tres días.\n"

    guardado = await client.put(f"{MEDIA}/subtitles/{item_id}/es", json={"content": contenido})
    assert guardado.status_code == 204

    leido = await client.get(f"{MEDIA}/subtitles/{item_id}/es")
    assert leido.json()["content"] == contenido


async def test_la_correccion_manual_sustituye_a_la_automatica(
    client: httpx.AsyncClient,
) -> None:
    """La transcripción automática equivoca nombres propios y términos locales."""
    item_id, _ = await _pieza_sensible(client)
    automatica = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nLa Mira\n"
    corregida = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nLa migra\n"

    await client.put(f"{MEDIA}/subtitles/{item_id}/es", json={"content": automatica})
    await client.put(f"{MEDIA}/subtitles/{item_id}/es", json={"content": corregida})

    assert (await client.get(f"{MEDIA}/subtitles/{item_id}/es")).json()["content"] == corregida


async def test_pista_en_formato_invalido_se_rechaza(client: httpx.AsyncClient) -> None:
    item_id, _ = await _pieza_sensible(client)

    response = await client.put(
        f"{MEDIA}/subtitles/{item_id}/es", json={"content": "esto no es webvtt"}
    )
    assert response.status_code == 422


async def test_idioma_de_subtitulos_no_admitido(client: httpx.AsyncClient) -> None:
    item_id, _ = await _pieza_sensible(client)

    response = await client.put(f"{MEDIA}/subtitles/{item_id}/fr", json={"content": "WEBVTT\n"})
    assert response.status_code == 422


async def test_un_editor_no_edita_subtitulos_de_otro_tema(
    client: httpx.AsyncClient, editor_client
) -> None:
    item_id, _ = await _pieza_sensible(client)

    editor = await editor_client(["migrantes"])
    response = await editor.put(f"{MEDIA}/subtitles/{item_id}/es", json={"content": "WEBVTT\n"})
    assert response.status_code == 403


# --- Construcción de claves -------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Retrato en el Albergue", "retrato-en-el-albergue"),
        ("Niña con pañuelo", "nina-con-panuelo"),
        ("  ¿Qué pasó?  ", "que-paso"),
        ("", "archivo"),
        ("///", "archivo"),
    ],
)
def test_normalizacion_de_nombres(entrada: str, esperado: str) -> None:
    assert slugify(entrada) == esperado


def test_clave_con_tipo_no_admitido_falla() -> None:
    with pytest.raises(ValidationError):
        build_key(
            scope="public",
            theme_slug="migrantes",
            filename="x.exe",
            content_type="application/x-msdownload",
        )


async def test_una_clave_con_salto_de_directorio_se_rechaza(tmp_path) -> None:
    """Sin esta comprobación, una clave con `../` escribiría fuera del almacén."""
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValidationError):
        await storage.exists("../../etc/passwd")
