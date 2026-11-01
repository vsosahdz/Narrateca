"""Pruebas de la recepción y de los marcadores de cita.

La recepción es la quinta voz de la página del chatbot y la única que no es
una voz: enumera comunidades con material y encamina, sin llamar al modelo.
Lo que se verifica aquí, sobre todo, es que **no redacta** —porque eso es lo
que la hace incapaz de inventar.
"""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.llm import EchoLanguageModel
from app.modules.chat.models import ActivationState, PersonaConfig
from app.modules.chat.prompts import cited_markers, sanitize_markers
from app.modules.chat.reception import derive_suggestions
from app.modules.content.models import (
    ConsentScope,
    ContentItem,
    ContentType,
    PublicationStatus,
    Sensitivity,
)
from app.modules.rag.embeddings import get_embedding_model
from app.modules.rag.indexer import ChunkIndexer
from app.modules.themes.models import Theme


async def _activar(session: AsyncSession, slug: str, estado: ActivationState) -> PersonaConfig:
    persona = (
        await session.execute(select(PersonaConfig).where(PersonaConfig.theme_slug == slug))
    ).scalar_one()
    persona.activation = estado
    await session.flush()
    return persona


async def _sembrar(
    session: AsyncSession,
    *,
    tema: str,
    slug: str,
    titulo: str,
    texto: str,
    consent: ConsentScope = ConsentScope.PUBLIC,
) -> ContentItem:
    theme = (await session.execute(select(Theme).where(Theme.slug == tema))).scalar_one()
    item = ContentItem(
        theme_id=theme.id,
        type=ContentType.TESTIMONY,
        slug=slug,
        title=titulo,
        body=texto,
        status=PublicationStatus.PUBLISHED,
        consent_scope=consent,
        sensitivity=Sensitivity.NORMAL,
    )
    session.add(item)
    await session.flush()
    await ChunkIndexer(session, get_embedding_model()).index_item(item.id)
    await session.flush()
    return item


# --- Recepción ---------------------------------------------------------------


async def test_la_recepcion_no_consulta_al_modelo(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Es lo que la hace incapaz de inventar: no redacta."""
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    response = await anon_client.post(
        "/api/v1/chat/orientacion", json={"question": "¿Cómo fue la primera noche?"}
    )

    assert response.status_code == 200
    assert language_model.llamadas == []


async def test_la_recepcion_no_devuelve_texto_redactado(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """El esquema no tiene un campo de respuesta. Es una garantía estructural."""
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/orientacion", json={"question": "¿Cómo fue la primera noche?"}
        )
    ).json()

    assert set(cuerpo) == {"communities"}


async def test_encamina_a_la_comunidad_con_material(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _activar(session, "lgbtq", ActivationState.ACTIVE)

    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )
    await _sembrar(
        session,
        tema="lgbtq",
        slug="la-primera-marcha",
        titulo="La primera marcha",
        texto="La primera marcha la recordamos con miedo y con alegría.",
    )

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/orientacion", json={"question": "¿Cómo fue la marcha?"}
        )
    ).json()

    slugs = [c["theme_slug"] for c in cuerpo["communities"]]
    assert "lgbtq" in slugs
    assert cuerpo["communities"][0]["best_item_title"] == "La primera marcha"


async def test_no_encamina_a_una_comunidad_cerrada(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Mandar a alguien a una puerta cerrada es peor que no mencionarla."""
    await _activar(session, "migrantes", ActivationState.COMING_SOON)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/orientacion", json={"question": "¿Cómo fue la primera noche?"}
        )
    ).json()

    assert cuerpo["communities"] == []


async def test_no_encamina_hacia_material_sin_consentimiento_de_ia(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="el-cruce",
        titulo="El cruce",
        texto="El cruce del río ocurrió de madrugada.",
        consent=ConsentScope.NO_AI,
    )

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/orientacion", json={"question": "¿Cómo fue el cruce del río?"}
        )
    ).json()
    assert cuerpo["communities"] == []


async def test_sin_material_no_encamina_a_ninguna_parte(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/orientacion",
            json={"question": "¿Cuál es la receta del mole poblano?"},
        )
    ).json()
    assert cuerpo["communities"] == []


# --- Preguntas sugeridas ------------------------------------------------------


async def test_el_selector_ofrece_preguntas_con_material_detras(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Evitan que el primer encuentro sea «no cuento con material»."""
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    migrantes = next(p for p in personas if p["theme_slug"] == "migrantes")

    assert migrantes["suggested_questions"]
    assert any("La primera noche" in q for q in migrantes["suggested_questions"])


async def test_las_preguntas_del_equipo_mandan_sobre_las_derivadas(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    persona = (
        await session.execute(select(PersonaConfig).where(PersonaConfig.theme_slug == "migrantes"))
    ).scalar_one()
    persona.suggested_questions = ["¿Qué recuerdan del camino?"]
    await session.flush()

    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    migrantes = next(p for p in personas if p["theme_slug"] == "migrantes")
    assert migrantes["suggested_questions"] == ["¿Qué recuerdan del camino?"]


async def test_no_se_sugiere_una_pregunta_sobre_material_excluido(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Sugerirla llevaría derecho a «no cuento con material»."""
    await _sembrar(
        session,
        tema="lgbtq",
        slug="el-cruce",
        titulo="Una pieza sin consentimiento de IA",
        texto="Texto que no puede alimentar al chatbot.",
        consent=ConsentScope.NO_AI,
    )

    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    lgbtq = next(p for p in personas if p["theme_slug"] == "lgbtq")
    assert not any("sin consentimiento" in q for q in lgbtq["suggested_questions"])


def test_las_preguntas_derivadas_salen_de_los_titulos() -> None:
    preguntas = derive_suggestions(["La primera noche", "El taller de costura"])
    assert len(preguntas) == 2
    assert "«La primera noche»" in preguntas[0]


def test_un_titulo_que_empieza_por_sobre_no_duplica_la_preposicion() -> None:
    (pregunta,) = derive_suggestions(["Sobre el diagnóstico tardío"])
    assert pregunta == "¿Qué cuenta el archivo sobre «el diagnóstico tardío»?"


async def test_el_selector_trae_el_nombre_de_la_comunidad(
    anon_client: httpx.AsyncClient,
) -> None:
    """Para que no haya que cruzar con el listado de temas solo por un título."""
    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    migrantes = next(p for p in personas if p["theme_slug"] == "migrantes")
    assert migrantes["name_es"] == "Migrantes"
    assert migrantes["name_en"] == "Migrants"


# --- Marcadores de cita -------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "total", "esperado"),
    [
        ("La espera duró meses [2].", 4, "La espera duró meses [2]."),
        # El modelo inventa un marcador que no existe: se borra y la frase queda.
        ("El cruce fue de madrugada [7].", 4, "El cruce fue de madrugada."),
        ("Sin marcadores.", 3, "Sin marcadores."),
        ("Cero no es válido [0].", 2, "Cero no es válido."),
    ],
)
def test_los_marcadores_invalidos_se_descartan(texto: str, total: int, esperado: str) -> None:
    """Un marcador inventado sería un enlace que no lleva a ninguna parte.

    Se borra el marcador y se conserva la frase: puede ser correcta aunque la
    referencia esté mal puesta, y borrarla entera sería castigar de más.
    """
    assert sanitize_markers(texto, total) == esperado


def test_se_sabe_que_fragmentos_quedaron_referenciados() -> None:
    texto = "Dormimos en la central [1], sin saber qué seguía [3]."
    assert cited_markers(texto, 4) == {1, 3}


async def test_las_citas_distinguen_las_referenciadas(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Un fragmento recuperado que el modelo no usó no sostiene ninguna
    afirmación, y presentarlo igual que los usados engañaría sobre qué apoya qué.
    """
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )

    language_model.respuesta = "Dormimos en la central de autobuses [1]."

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/migrantes", json={"message": "¿Cómo fue la primera noche?"}
        )
    ).json()

    assert cuerpo["citations"][0]["cited"] is True


async def test_un_marcador_inventado_no_llega_a_la_respuesta(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    language_model.respuesta = "Dormimos en la central [1] y cruzamos el río [9]."

    cuerpo = (
        await anon_client.post(
            "/api/v1/chat/migrantes", json={"message": "¿Cómo fue la primera noche?"}
        )
    ).json()

    assert "[9]" not in cuerpo["reply"]
    assert "[1]" in cuerpo["reply"]


async def test_el_prompt_pide_los_marcadores(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _sembrar(
        session,
        tema="migrantes",
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    await anon_client.post(
        "/api/v1/chat/migrantes", json={"message": "¿Cómo fue la primera noche?"}
    )

    sistema = next(m.content for m in language_model.llamadas[0] if m.role == "system")
    assert "número entre corchetes" in sistema
    assert "no inventes ninguno" in sistema
