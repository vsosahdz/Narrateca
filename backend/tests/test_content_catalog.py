"""Pruebas del catálogo de contenido.

Cubren los escenarios de la spec `content-catalog`, con énfasis en los dos que
sostienen el resto del proyecto: el alcance de consentimiento y la atribución.
"""

from typing import Any

import httpx
import pytest

from app.modules.content.indexing import NullIndexSynchronizer

ADMIN = "/api/v1/admin/content"
PUBLIC = "/api/v1/content"


def payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "theme_slug": "migrantes",
        "type": "testimony",
        "slug": "primera-noche",
        "title": "La primera noche",
        "body": "No dormí en tres días.",
        "attribution": "anonymous",
    }
    base.update(overrides)
    return base


async def crear(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post(ADMIN, json=payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# --- Modelo compartido ------------------------------------------------------


@pytest.mark.parametrize(
    "content_type", ["photo", "testimony", "video", "interview", "news_post", "geo_item"]
)
async def test_cualquier_tipo_en_cualquier_tema(
    client: httpx.AsyncClient, content_type: str
) -> None:
    """Un solo ContentItem sirve a los cuatro temas y a todos los tipos."""
    for index, theme in enumerate(
        ["migrantes", "lgbtq", "mujeres_discapacidad", "mujeres_violencia"]
    ):
        item = await crear(
            client,
            theme_slug=theme,
            type=content_type,
            slug=f"{content_type.replace('_', '-')}-{index}",
            alt_text="Descripción" if content_type == "photo" else None,
        )
        assert item["theme_slug"] == theme
        assert item["type"] == content_type


async def test_tipo_no_soportado_es_rechazado(client: httpx.AsyncClient) -> None:
    response = await client.post(ADMIN, json=payload(type="podcast"))
    assert response.status_code == 422


async def test_slug_duplicado_en_el_mismo_tema_es_conflicto(
    client: httpx.AsyncClient,
) -> None:
    await crear(client)
    response = await client.post(ADMIN, json=payload())
    assert response.status_code == 409


async def test_el_mismo_slug_en_otro_tema_si_se_permite(client: httpx.AsyncClient) -> None:
    """La dirección pública es /<tema>/<slug>, así que el slug es único por tema."""
    await crear(client)
    item = await crear(client, theme_slug="lgbtq")
    assert item["slug"] == "primera-noche"


# --- Consentimiento ---------------------------------------------------------


async def test_valor_por_defecto_conservador(client: httpx.AsyncClient) -> None:
    """Escenario: crear sin especificar consent_scope asigna no_ai."""
    item = await crear(client)
    assert item["consent_scope"] == "no_ai"
    assert item["is_indexable"] is False


async def test_pieza_publicable_pero_excluida_del_chatbot(
    client: httpx.AsyncClient, indexer: NullIndexSynchronizer
) -> None:
    """Escenario clave: se publica en el sitio y nunca entra al índice."""
    item = await crear(client, consent_scope="no_ai")

    published = await client.post(f"{ADMIN}/{item['id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["is_indexable"] is False

    # Visible al público…
    public = await client.get(f"{PUBLIC}/migrantes/primera-noche")
    assert public.status_code == 200

    # …y sin un solo fragmento indexado.
    assert indexer.indexed == []


async def test_pieza_con_consentimiento_amplio_si_se_indexa(
    client: httpx.AsyncClient, indexer: NullIndexSynchronizer
) -> None:
    item = await crear(client, consent_scope="public")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    assert item["id"] in [str(i) for i in indexer.indexed]


async def test_revocar_consentimiento_elimina_del_indice(
    client: httpx.AsyncClient, indexer: NullIndexSynchronizer
) -> None:
    """Escenario: cambiar a no_ai una pieza indexada la retira del índice…"""
    item = await crear(client, consent_scope="public")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    response = await client.put(f"{ADMIN}/{item['id']}/consent", params={"scope": "no_ai"})
    assert response.status_code == 200
    assert response.json()["is_indexable"] is False
    assert item["id"] in [str(i) for i in indexer.removed]

    # …y la pieza permanece visible en el sitio público.
    public = await client.get(f"{PUBLIC}/migrantes/primera-noche")
    assert public.status_code == 200


async def test_retirar_una_pieza_la_saca_del_indice_y_del_sitio(
    client: httpx.AsyncClient, indexer: NullIndexSynchronizer
) -> None:
    item = await crear(client, consent_scope="public")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    await client.post(f"{ADMIN}/{item['id']}/withdraw")

    assert item["id"] in [str(i) for i in indexer.removed]
    public = await client.get(f"{PUBLIC}/migrantes/primera-noche")
    assert public.status_code == 404


async def test_el_consentimiento_no_se_expone_al_publico(client: httpx.AsyncClient) -> None:
    item = await crear(client, consent_scope="public")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    public = (await client.get(f"{PUBLIC}/migrantes/primera-noche")).json()
    assert "consent_scope" not in public


# --- Atribución -------------------------------------------------------------


async def test_testimonio_anonimo_no_expone_nombre(client: httpx.AsyncClient) -> None:
    """Escenario: una pieza anónima nunca revela el nombre real."""
    item = await crear(client, attribution="anonymous", person_name="Nombre Real")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    public = (await client.get(f"{PUBLIC}/migrantes/primera-noche")).json()

    assert public["display_name"] is None
    assert "person_name" not in public
    assert "Nombre Real" not in str(public)


async def test_seudonimo_muestra_seudonimo_no_nombre_real(
    client: httpx.AsyncClient,
) -> None:
    item = await crear(
        client,
        attribution="pseudonym",
        pseudonym="Ana",
        person_name="Nombre Real",
    )
    await client.post(f"{ADMIN}/{item['id']}/publish")

    public = (await client.get(f"{PUBLIC}/migrantes/primera-noche")).json()

    assert public["display_name"] == "Ana"
    assert "Nombre Real" not in str(public)


async def test_atribucion_con_nombre_si_muestra_el_nombre(client: httpx.AsyncClient) -> None:
    item = await crear(client, attribution="named", person_name="María López")
    await client.post(f"{ADMIN}/{item['id']}/publish")

    public = (await client.get(f"{PUBLIC}/migrantes/primera-noche")).json()
    assert public["display_name"] == "María López"


async def test_atribucion_con_nombre_sin_nombre_es_invalida(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(ADMIN, json=payload(attribution="named"))
    assert response.status_code == 422


async def test_el_nombre_real_si_es_visible_en_administracion(
    client: httpx.AsyncClient,
) -> None:
    """El equipo necesita el dato para gestionar; el público, nunca."""
    await crear(client, attribution="anonymous", person_name="Nombre Real")

    admin = (await client.get(ADMIN)).json()
    assert admin[0]["person_name"] == "Nombre Real"


# --- Texto alternativo ------------------------------------------------------


async def test_publicar_fotografia_sin_texto_alternativo_falla(
    client: httpx.AsyncClient,
) -> None:
    """Escenario: el contenido visual requiere alt_text para publicarse."""
    item = await crear(client, type="photo", slug="retrato", alt_text=None)

    response = await client.post(f"{ADMIN}/{item['id']}/publish")
    assert response.status_code == 422
    assert "alt_text" in response.json()["detail"]


async def test_borrador_sin_texto_alternativo_si_se_guarda(
    client: httpx.AsyncClient,
) -> None:
    """Escenario: un borrador incompleto es un estado de trabajo legítimo."""
    item = await crear(client, type="photo", slug="retrato", alt_text=None)
    assert item["status"] == "draft"


async def test_texto_alternativo_en_blanco_no_cuenta(client: httpx.AsyncClient) -> None:
    item = await crear(client, type="photo", slug="retrato", alt_text="   ")
    response = await client.post(f"{ADMIN}/{item['id']}/publish")
    assert response.status_code == 422


async def test_fotografia_con_texto_alternativo_se_publica(
    client: httpx.AsyncClient,
) -> None:
    item = await crear(
        client, type="photo", slug="retrato", alt_text="Mujer de perfil junto a una ventana"
    )
    response = await client.post(f"{ADMIN}/{item['id']}/publish")
    assert response.status_code == 200


# --- Estados de publicación -------------------------------------------------


async def test_borrador_invisible_al_publico(client: httpx.AsyncClient) -> None:
    await crear(client)

    listado = (await client.get(PUBLIC, params={"theme": "migrantes"})).json()
    assert listado == []

    detalle = await client.get(f"{PUBLIC}/migrantes/primera-noche")
    assert detalle.status_code == 404


async def test_filtrado_por_tema_y_tipo(client: httpx.AsyncClient) -> None:
    a = await crear(client, slug="uno", type="testimony", consent_scope="site_only")
    b = await crear(client, slug="dos", type="interview", theme_slug="lgbtq")
    await client.post(f"{ADMIN}/{a['id']}/publish")
    await client.post(f"{ADMIN}/{b['id']}/publish")

    solo_migrantes = (await client.get(PUBLIC, params={"theme": "migrantes"})).json()
    assert {i["slug"] for i in solo_migrantes} == {"uno"}

    solo_entrevistas = (await client.get(PUBLIC, params={"type": "interview"})).json()
    assert {i["slug"] for i in solo_entrevistas} == {"dos"}


# --- Enlaces curados --------------------------------------------------------


async def test_enlace_curado_sin_resumen_no_se_publica(client: httpx.AsyncClient) -> None:
    item = await crear(
        client,
        type="curated_link",
        slug="nota-externa",
        external_url="https://ejemplo.mx/nota",
        summary=None,
    )
    response = await client.post(f"{ADMIN}/{item['id']}/publish")
    assert response.status_code == 422
    assert "resumen" in response.json()["detail"].lower()


# --- Procedencia ------------------------------------------------------------


async def test_procedencia_se_conserva(client: httpx.AsyncClient) -> None:
    item = await crear(client, source_ref="/archivo/migrantes/ent-014.docx")
    assert item["source_ref"] == "/archivo/migrantes/ent-014.docx"


async def test_no_se_importa_dos_veces_el_mismo_origen(client: httpx.AsyncClient) -> None:
    """Sostiene la idempotencia de la importación del grupo 5."""
    await crear(client, source_ref="/archivo/ent-014.docx")

    response = await client.post(
        ADMIN, json=payload(slug="otro", source_ref="/archivo/ent-014.docx")
    )
    assert response.status_code == 409
