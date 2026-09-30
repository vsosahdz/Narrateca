"""Personalización de la documentación OpenAPI / Swagger.

La documentación es un entregable del proyecto, no un efecto secundario: agrupa
los endpoints por dominio y explica las restricciones que no son evidentes desde
la firma de cada función.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

API_TITLE = "NarraTECa API"
API_VERSION = "1.0.0"

API_DESCRIPTION = """
API de **NarraTECa**, plataforma digital de archivo testimonial sobre cuatro
comunidades: migrantes, comunidad LGBTQ+, mujeres con discapacidad, y mujeres y
violencia de género.

### Principios que gobiernan esta API

- **El consentimiento es un dato, no un acuerdo verbal.** Cada pieza de contenido
  lleva un `consent_scope`. Publicar en el sitio y alimentar al chatbot son
  permisos distintos: una pieza marcada como `no_ai` se publica pero nunca entra
  al índice vectorial.
- **El chatbot está anclado al archivo.** Toda afirmación proviene de un fragmento
  recuperado y se entrega citada, con enlace a su pieza original.
- **Minimización de datos.** Los embeddings y la transcripción se calculan en
  infraestructura propia. Hacia el proveedor de modelo de lenguaje solo viajan la
  consulta y los fragmentos recuperados para esa consulta.
- **Los temas son datos.** Las cuatro comunidades son registros, no valores
  codificados en la aplicación.
"""

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Temas",
        "description": (
            "Comunidades de la plataforma. Son datos: dar de alta una nueva no requiere código."
        ),
    },
    {
        "name": "Contenido",
        "description": (
            "Catálogo compartido de fotografías, testimonios, videos, entrevistas y "
            "contenido geográfico."
        ),
    },
    {
        "name": "Noticias",
        "description": "Notas redactadas por el equipo y enlaces curados a medios externos.",
    },
    {
        "name": "Equipo",
        "description": "Integrantes del equipo de investigación.",
    },
    {
        "name": "Chatbot",
        "description": (
            "Conversación anclada con la voz de cada comunidad, con citas trazables al archivo."
        ),
    },
    {
        "name": "Administración",
        "description": (
            "Autenticación, gestión de contenido y panel de control. Requiere sesión con rol."
        ),
    },
    {
        "name": "Ingesta",
        "description": (
            "Importación del archivo, transcripción e indexación en el corpus del chatbot."
        ),
    },
    {
        "name": "Sistema",
        "description": "Verificación de estado del servicio.",
    },
]


def configure_openapi(app: FastAPI) -> None:
    """Instala un generador de esquema OpenAPI con metadatos del proyecto."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=API_TITLE,
            version=API_VERSION,
            description=API_DESCRIPTION,
            routes=app.routes,
            tags=TAGS_METADATA,
        )
        schema["info"]["contact"] = {"name": "Equipo de investigación NarraTECa"}
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
