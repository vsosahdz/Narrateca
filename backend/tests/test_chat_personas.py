"""Pruebas de los escenarios de `chat-personas`.

El énfasis está donde lo pone la especificación: **anclaje, citación y
minimización de datos enviados**. Son las tres cosas que, si fallan, no
producen un error visible sino una respuesta plausible y falsa.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.llm import EchoLanguageModel
from app.modules.chat.models import ActivationState, PersonaConfig, VoicePolicy
from app.modules.chat.prompts import SIN_MATERIAL_EN, SIN_MATERIAL_ES
from app.modules.chat.safety import detect_personal_disclosure
from app.modules.chat.service import public_url
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

TEMA = "migrantes"


async def _activar(session: AsyncSession, slug: str, estado: ActivationState) -> PersonaConfig:
    persona = (
        await session.execute(select(PersonaConfig).where(PersonaConfig.theme_slug == slug))
    ).scalar_one()
    persona.activation = estado
    await session.flush()
    return persona


async def _sembrar_pieza(
    session: AsyncSession,
    *,
    slug: str,
    titulo: str,
    texto: str,
    tema: str = TEMA,
    consent: ConsentScope = ConsentScope.PUBLIC,
    estado: PublicationStatus = PublicationStatus.PUBLISHED,
) -> ContentItem:
    """Crea una pieza publicada y la indexa."""
    theme = (await session.execute(select(Theme).where(Theme.slug == tema))).scalar_one()

    item = ContentItem(
        theme_id=theme.id,
        type=ContentType.TESTIMONY,
        slug=slug,
        title=titulo,
        body=texto,
        status=estado,
        consent_scope=consent,
        sensitivity=Sensitivity.NORMAL,
    )
    session.add(item)
    await session.flush()

    await ChunkIndexer(session, get_embedding_model()).index_item(item.id)
    await session.flush()
    return item


# --- Configuración de persona ------------------------------------------------


async def test_hay_una_narradora_por_comunidad(anon_client: httpx.AsyncClient) -> None:
    response = await anon_client.get("/api/v1/chat/personas")
    assert response.status_code == 200

    slugs = {p["theme_slug"] for p in response.json()}
    assert slugs == {"migrantes", "lgbtq", "mujeres-discapacidad", "mujeres-violencia"}


async def test_el_selector_muestra_las_cuatro_aunque_no_esten_disponibles(
    anon_client: httpx.AsyncClient,
) -> None:
    """Escenario: selector con comunidades en estados distintos.

    Las no disponibles se muestran y se señalan, no se esconden: quien entra
    debe poder ver que esa comunidad existe y que llegará.
    """
    response = await anon_client.get("/api/v1/chat/personas")
    personas = response.json()

    assert len(personas) == 4
    assert all(p["activation"] == "draft" for p in personas), "las narradoras deben nacer cerradas"


@pytest.mark.parametrize(
    ("slug", "politica"),
    [
        ("mujeres-violencia", VoicePolicy.FEMALE_ONLY),
        ("mujeres-discapacidad", VoicePolicy.FEMALE_ONLY),
        ("migrantes", VoicePolicy.ANY),
        ("lgbtq", VoicePolicy.ANY),
    ],
)
async def test_politica_de_voz_registrada(
    anon_client: httpx.AsyncClient, slug: str, politica: VoicePolicy
) -> None:
    """La síntesis es de la fase 2; la decisión sobre qué voces, no.

    Voz femenina exclusiva en las dos iniciativas de mujeres. Es una decisión
    del equipo de investigación sobre cómo se representan esas voces.
    """
    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    persona = next(p for p in personas if p["theme_slug"] == slug)
    assert persona["voice_policy"] == politica.value


async def test_el_prompt_de_sistema_no_es_publico(anon_client: httpx.AsyncClient) -> None:
    """Exponerlo facilitaría eludirlo."""
    personas = (await anon_client.get("/api/v1/chat/personas")).json()
    for persona in personas:
        assert "system_prompt" not in persona


# --- Activación independiente ------------------------------------------------


async def test_una_comunidad_activa_acepta_conversacion(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["reply"]


async def test_una_comunidad_proximamente_no_conversa(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: intento de conversación con una comunidad en `coming_soon`."""
    await _activar(session, TEMA, ActivationState.COMING_SOON)

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"}
    )
    assert response.status_code == 403
    assert "próximamente" in response.json()["detail"].lower()


async def test_una_narradora_en_borrador_solo_habla_con_administracion(
    anon_client: httpx.AsyncClient, client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: persona en borrador.

    Es el motivo de que `draft` exista: poder revisar el comportamiento antes
    de abrirlo al público.
    """
    await _activar(session, TEMA, ActivationState.DRAFT)
    await _sembrar_pieza(
        session,
        slug="la-espera",
        titulo="La espera",
        texto="La espera duró cuatro meses en un albergue de la frontera.",
    )

    sin_sesion = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cuánto duró la espera?"}
    )
    assert sin_sesion.status_code == 403

    con_sesion = await client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cuánto duró la espera?"}
    )
    assert con_sesion.status_code == 200, con_sesion.text


async def test_el_estado_de_una_comunidad_no_afecta_a_las_demas(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, "migrantes", ActivationState.ACTIVE)
    await _activar(session, "lgbtq", ActivationState.COMING_SOON)

    personas = {p["theme_slug"]: p for p in (await anon_client.get("/api/v1/chat/personas")).json()}
    assert personas["migrantes"]["activation"] == "active"
    assert personas["lgbtq"]["activation"] == "coming_soon"
    assert personas["mujeres-violencia"]["activation"] == "draft"


# --- Anclaje -----------------------------------------------------------------


async def test_sin_material_no_se_consulta_al_modelo(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: pregunta sin material disponible.

    Lo que se verifica no es solo que la respuesta sea la correcta, sino que
    **el modelo no llegó a ser consultado**. Si no hay fragmentos, cualquier
    cosa que el modelo escribiera estaría inventada, así que no se le pregunta.
    """
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}",
        json={"message": "¿Cuál es la receta del mole poblano?"},
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["reply"] == SIN_MATERIAL_ES
    assert cuerpo["citations"] == []
    assert cuerpo["no_material_reason"]
    assert language_model.llamadas == [], "no debió consultarse al modelo"


async def test_corpus_vacio_declara_ausencia_de_material(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    await _activar(session, "lgbtq", ActivationState.ACTIVE)

    response = await anon_client.post(
        "/api/v1/chat/lgbtq", json={"message": "¿Cómo fue encontrar comunidad?"}
    )

    assert response.status_code == 200
    assert response.json()["reply"] == SIN_MATERIAL_ES
    assert language_model.llamadas == []


async def test_el_prompt_prohibe_inventar_y_pedir_biografia(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Las reglas de anclaje se añaden siempre, no dependen del prompt editable."""
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    await anon_client.post(f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"})

    assert language_model.llamadas, "debió consultarse al modelo"
    sistema = next(m.content for m in language_model.llamadas[0] if m.role == "system")

    assert "primera persona del plural" in sistema
    assert "no aparezca en los fragmentos" in sistema
    assert "no a una persona individual" in sistema
    assert "No des consejo clínico, legal ni terapéutico" in sistema


async def test_el_prompt_de_anclaje_sobrevive_a_un_prompt_editable_vacio(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Vaciar el prompt desde el panel quita el tono, no el anclaje."""
    persona = await _activar(session, TEMA, ActivationState.ACTIVE)
    persona.system_prompt = ""
    await session.flush()

    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    await anon_client.post(f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"})

    sistema = next(m.content for m in language_model.llamadas[0] if m.role == "system")
    assert "no aparezca en los fragmentos" in sistema


# --- Citación ----------------------------------------------------------------


async def test_la_respuesta_cita_con_enlace_a_la_pieza(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: respuesta con citas."""
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"}
    )

    citas = response.json()["citations"]
    assert citas, "una respuesta apoyada en el archivo debe citar"

    cita = citas[0]
    assert cita["text"]
    assert cita["item_title"] == "La primera noche"
    assert cita["url"] == "/es/migrantes/la-primera-noche"


async def test_los_enlaces_citados_apuntan_a_piezas_publicadas(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: validez de los enlaces citados.

    Se comprueba siguiendo el enlace contra la API pública, que es lo que hay
    detrás de esa ruta en el sitio.
    """
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )

    respuesta = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"}
    )
    cita = respuesta.json()["citations"][0]

    # Que el endpoint público la devuelva ya prueba que está publicada: el
    # catálogo público no sirve borradores ni piezas retiradas, y su esquema no
    # tiene siquiera un campo `status` que consultar.
    pieza = await anon_client.get(f"/api/v1/content/{cita['theme_slug']}/{cita['item_slug']}")
    assert pieza.status_code == 200, pieza.text
    assert pieza.json()["slug"] == cita["item_slug"]


def test_la_direccion_publica_la_construye_el_servidor() -> None:
    """El modelo nunca escribe direcciones.

    Una dirección inventada que parece válida es peor que ninguna: invita a
    seguirla y acaba en un 404 con apariencia de fuente.
    """
    assert public_url("migrantes", "la-primera-noche", "es") == "/es/migrantes/la-primera-noche"
    assert public_url("migrantes", "la-primera-noche", "en") == "/en/migrantes/la-primera-noche"


# --- Minimización de datos enviados ------------------------------------------


async def test_solo_se_envia_lo_recuperado(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: contenido enviado en una consulta.

    El corpus completo no sale nunca. Se siembra una pieza que no tiene nada
    que ver con la pregunta y se comprueba que su texto no viajó.
    """
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )
    await _sembrar_pieza(
        session,
        slug="el-taller-de-costura",
        titulo="El taller de costura",
        texto="En el taller de costura aprendimos a manejar la máquina industrial.",
    )

    await anon_client.post(f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"})

    enviado = "\n".join(m.content for m in language_model.llamadas[0])
    assert "central de autobuses" in enviado
    assert "máquina industrial" not in enviado, "viajó una pieza que no se recuperó"


async def test_una_pieza_sin_consentimiento_de_ia_nunca_viaja(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: contenido excluido nunca transmitido.

    Es la garantía central del proyecto. La pieza se siembra con el texto que
    responde exactamente a la pregunta, para que solo pueda quedar fuera por su
    consentimiento y no por no ser relevante.
    """
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="el-cruce",
        titulo="El cruce",
        texto="El cruce del río ocurrió de madrugada, con el agua hasta el pecho.",
        consent=ConsentScope.NO_AI,
    )

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue el cruce del río?"}
    )

    assert response.json()["reply"] == SIN_MATERIAL_ES
    assert language_model.llamadas == []


async def test_una_pieza_solo_para_el_sitio_tampoco_viaja(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """`site_only` autoriza publicar, no alimentar al chatbot."""
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="el-cruce",
        titulo="El cruce",
        texto="El cruce del río ocurrió de madrugada, con el agua hasta el pecho.",
        consent=ConsentScope.SITE_ONLY,
    )

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue el cruce del río?"}
    )
    assert response.json()["reply"] == SIN_MATERIAL_ES
    assert language_model.llamadas == []


async def test_el_corpus_de_otra_comunidad_no_se_mezcla(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: personas independientes por tema."""
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )
    await _sembrar_pieza(
        session,
        slug="la-primera-marcha",
        titulo="La primera marcha",
        texto="La primera marcha la recordamos con una mezcla de miedo y alegría.",
        tema="lgbtq",
    )

    await anon_client.post(f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"})

    enviado = "\n".join(m.content for m in language_model.llamadas[0])
    assert "miedo y alegría" not in enviado, "se filtró el corpus de otra comunidad"


async def test_no_se_envia_nada_mas_que_sistema_e_historial(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    await anon_client.post(f"/api/v1/chat/{TEMA}", json={"message": "¿Cómo fue la primera noche?"})

    roles = [m.role for m in language_model.llamadas[0]]
    assert roles == ["system", "user"]


# --- Idioma ------------------------------------------------------------------


async def test_pregunta_en_ingles_responde_en_ingles(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: pregunta en inglés. El corpus sigue siendo el español."""
    await _activar(session, TEMA, ActivationState.ACTIVE)

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}", json={"message": "What was the first night like?"}
    )

    cuerpo = response.json()
    assert cuerpo["language"] == "en"
    assert cuerpo["reply"] == SIN_MATERIAL_EN


async def test_el_idioma_puede_forzarse(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, TEMA, ActivationState.ACTIVE)

    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}",
        json={"message": "¿Cómo fue la primera noche?", "language": "en"},
    )
    assert response.json()["language"] == "en"


async def test_en_ingles_se_pide_la_cita_en_espanol_con_traduccion(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: cita en respuesta en inglés.

    El corpus está en español. Una cita traducida sin señalar que lo está
    pondría palabras en inglés en boca de quien habló en español.
    """
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    await anon_client.post(
        f"/api/v1/chat/{TEMA}",
        json={"message": "¿Cómo fue la primera noche?", "language": "en"},
    )

    sistema = next(m.content for m in language_model.llamadas[0] if m.role == "system")
    assert "marked as a\ntranslation" in sistema or "marked as a translation" in sistema


# --- Contención --------------------------------------------------------------


@pytest.mark.parametrize(
    "mensaje",
    [
        "mi pareja me pega y no sé qué hacer",
        "tengo miedo de volver a mi casa",
        "a mí me pasó algo parecido",
        "estoy en peligro",
    ],
)
def test_se_detecta_un_relato_personal(mensaje: str) -> None:
    assert detect_personal_disclosure(mensaje).triggered


@pytest.mark.parametrize(
    "mensaje",
    [
        "¿Qué cuentan los testimonios sobre la violencia en el tránsito?",
        "¿Cómo documentaron las mujeres esa violencia?",
        "¿Hay entrevistas sobre el miedo en el camino?",
    ],
)
def test_una_pregunta_sobre_el_archivo_no_dispara_contencion(mensaje: str) -> None:
    """Distinguir la pregunta del relato importa.

    Tratar una consulta de investigación como una revelación personal dejaría
    el chatbot inservible para quien estudia el archivo.
    """
    assert not detect_personal_disclosure(mensaje).triggered


async def test_un_relato_personal_recibe_contencion_sin_consultar_al_modelo(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """Escenario: relato de una experiencia personal de violencia.

    El corte ocurre **antes** de recuperar y antes del modelo: si alguien está
    contando lo que le pasa, no hay nada que buscar en el archivo.
    """
    await _activar(session, "mujeres-violencia", ActivationState.ACTIVE)

    response = await anon_client.post(
        "/api/v1/chat/mujeres-violencia",
        json={"message": "mi pareja me pega y no sé qué hacer"},
    )

    cuerpo = response.json()
    assert cuerpo["contained"] is True
    assert "sistema automatizado" in cuerpo["reply"]
    assert cuerpo["citations"] == []
    assert language_model.llamadas == []


async def test_la_contencion_no_aconseja(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """No hay consejo clínico, legal ni terapéutico. Tampoco diagnóstico."""
    await _activar(session, "mujeres-violencia", ActivationState.ACTIVE)

    response = await anon_client.post(
        "/api/v1/chat/mujeres-violencia",
        json={"message": "¿qué debo hacer si mi pareja me amenaza?"},
    )

    texto = response.json()["reply"].lower()
    assert response.json()["contained"] is True
    for prohibido in ("deberías", "te recomiendo", "denuncia", "acude a", "llama al"):
        assert prohibido not in texto, f"la contención no debe aconsejar: «{prohibido}»"


async def test_el_mensaje_de_contencion_es_configurable_por_comunidad(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Lo redacta el equipo de investigación, no el código (tarea 11.13)."""
    persona = await _activar(session, "mujeres-violencia", ActivationState.ACTIVE)
    persona.safety_message_es = "Mensaje propio del equipo."
    await session.flush()

    response = await anon_client.post(
        "/api/v1/chat/mujeres-violencia",
        json={"message": "estoy en peligro"},
    )
    assert response.json()["reply"] == "Mensaje propio del equipo."


# --- Transmisión progresiva --------------------------------------------------


async def test_la_respuesta_llega_por_partes(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    """Escenario: recepción progresiva."""
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses, sin saber qué seguía.",
    )

    async with anon_client.stream(
        "POST",
        f"/api/v1/chat/{TEMA}/stream",
        json={"message": "¿Cómo fue la primera noche?"},
    ) as respuesta:
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("text/event-stream")

        eventos = [linea async for linea in respuesta.aiter_lines() if linea.startswith("event:")]

    tipos = [e.removeprefix("event: ").strip() for e in eventos]
    assert tipos[0] == "meta"
    assert tipos.count("delta") > 1, "la respuesta debe llegar en más de un trozo"
    assert "citations" in tipos
    assert tipos[-1] == "done"


async def test_la_transmision_tambien_corta_sin_material(
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    language_model: EchoLanguageModel,
) -> None:
    """El camino con transmisión toma las mismas decisiones que el otro."""
    await _activar(session, TEMA, ActivationState.ACTIVE)

    async with anon_client.stream(
        "POST",
        f"/api/v1/chat/{TEMA}/stream",
        json={"message": "¿Cuál es la receta del mole poblano?"},
    ) as respuesta:
        cuerpo = "".join([linea async for linea in respuesta.aiter_lines()])

    assert "no cuento con material" in cuerpo.lower()
    assert language_model.llamadas == []


# --- Conversación ------------------------------------------------------------


async def test_la_conversacion_conserva_su_identificador(
    anon_client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _activar(session, TEMA, ActivationState.ACTIVE)
    await _sembrar_pieza(
        session,
        slug="la-primera-noche",
        titulo="La primera noche",
        texto="La primera noche dormimos en la central de autobuses.",
    )

    conversacion = uuid.uuid4()
    response = await anon_client.post(
        f"/api/v1/chat/{TEMA}",
        json={"message": "¿Cómo fue la primera noche?", "conversation_id": str(conversacion)},
    )
    assert response.json()["conversation_id"] == str(conversacion)


async def test_una_comunidad_inexistente_devuelve_404(anon_client: httpx.AsyncClient) -> None:
    response = await anon_client.post("/api/v1/chat/no-existe", json={"message": "hola"})
    assert response.status_code == 404
