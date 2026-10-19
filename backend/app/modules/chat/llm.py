"""Acceso al modelo de lenguaje.

La especificación `chat-personas` exige que el proveedor sea intercambiable:
cambiar de servicio, o mover la inferencia a infraestructura propia, no debe
tocar la recuperación, la citación ni la persistencia.

Eso aquí significa una cosa concreta: **este módulo no sabe nada de NarraTECa**.
No conoce temas, ni fragmentos, ni citas, ni consentimiento. Recibe mensajes y
devuelve texto. Toda la lógica del proyecto vive del otro lado de esta
frontera, en `service.py`, que es quien decide qué se envía.

Esa separación también es la que hace verificable el requisito de minimización:
si lo único que cruza es una lista de mensajes ya construida, auditar qué se
envía al proveedor es auditar quién llama a `generate`.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class Message:
    """Un turno de la conversación, en el vocabulario del proveedor."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerationError(Exception):
    """El proveedor no pudo responder.

    Se distingue de un fallo de programación a propósito: que el servicio de
    inferencia esté caído o tarde demasiado es una condición esperada, y la
    conversación debe degradar con un mensaje legible en lugar de un error 500.
    """

    message: str
    cause: str | None = None

    def __str__(self) -> str:  # pragma: no cover - representación
        return self.message


class LanguageModel(ABC):
    """Interfaz del proveedor.

    Solo transmisión progresiva. No hay un método que devuelva la respuesta
    completa de una vez porque la especificación exige que el texto llegue
    incremental, y tener dos caminos invita a que uno de los dos se quede sin
    mantener. Quien necesite el texto entero acumula lo que llega.
    """

    @abstractmethod
    def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """Produce la respuesta en trozos, en orden."""
        raise NotImplementedError

    async def generate(self, messages: list[Message]) -> str:
        """Acumula la transmisión. Comodidad para pruebas y para tareas por lotes."""
        partes: list[str] = []
        async for trozo in self.stream(messages):
            partes.append(trozo)
        return "".join(partes)


class EchoLanguageModel(LanguageModel):
    """Proveedor de desarrollo y pruebas. No sale de la máquina.

    Devuelve algo derivado de lo que recibe, de forma determinista, para poder
    verificar el armado del prompt, la citación y la transmisión progresiva sin
    depender de un servicio externo ni de que un modelo responda igual dos
    veces.
    """

    def __init__(self, respuesta: str | None = None) -> None:
        self.respuesta = respuesta
        #: Lo que se le pidió, en orden. Las pruebas de minimización de datos
        #: miran aquí para comprobar qué salió del sistema.
        self.llamadas: list[list[Message]] = []

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        self.llamadas.append(list(messages))

        if self.respuesta is not None:
            texto = self.respuesta
        else:
            ultimo = next(
                (m.content for m in reversed(messages) if m.role == "user"),
                "",
            )
            texto = f"[eco] {ultimo}"

        # Se emite por palabras para que el consumidor ejercite de verdad el
        # camino incremental y no reciba todo en un solo trozo.
        for palabra in texto.split(" "):
            yield palabra + " "


class OllamaLanguageModel(LanguageModel):
    """Adaptador para la API de Ollama, local o en su nube.

    El punto de conexión es configurable, así que la misma clase sirve para una
    instancia en la máquina del equipo y para el servicio gestionado. Eso es
    deliberado: si más adelante se decide repatriar la inferencia, cambia una
    variable de entorno y no el código.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        cuerpo = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            # Temperatura baja: la narradora debe ceñirse a los fragmentos
            # recuperados. Lo que aquí se premia es la fidelidad al material,
            # no la variedad de la redacción.
            "options": {"temperature": 0.3},
        }

        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout_seconds) as cliente,
                cliente.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=cuerpo,
                    headers=self._headers(),
                ) as respuesta,
            ):
                if respuesta.status_code >= 400:
                    await respuesta.aread()
                    raise GenerationError(
                        "El servicio de lenguaje rechazó la solicitud.",
                        cause=f"HTTP {respuesta.status_code}",
                    )

                async for linea in respuesta.aiter_lines():
                    if not linea.strip():
                        continue
                    try:
                        dato = json.loads(linea)
                    except json.JSONDecodeError:
                        # Una línea ilegible no debe tumbar la conversación
                        # entera: se descarta y se sigue leyendo.
                        continue

                    trozo = dato.get("message", {}).get("content", "")
                    if trozo:
                        yield trozo
                    if dato.get("done"):
                        break
        except httpx.TimeoutException as error:
            raise GenerationError(
                "El servicio de lenguaje tardó demasiado en responder.",
                cause=str(error),
            ) from error
        except httpx.HTTPError as error:
            raise GenerationError(
                "No se pudo contactar con el servicio de lenguaje.",
                cause=str(error),
            ) from error


def build_language_model() -> LanguageModel:
    """Construye el proveedor que indique la configuración.

    El nombre del proveedor y su punto de conexión son configuración, no
    código: es lo que permite cambiar de servicio sin desplegar.
    """
    if settings.llm_provider == "ollama":
        return OllamaLanguageModel(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    # `echo` es el valor por defecto a propósito: un entorno recién levantado no
    # habla con ningún servicio externo mientras nadie lo configure.
    return EchoLanguageModel()


#: Instancia compartida. Se construye una sola vez porque el adaptador no
#: guarda estado entre llamadas.
_modelo: LanguageModel | None = None


def get_language_model() -> LanguageModel:
    """Dependencia de FastAPI. Las pruebas la sustituyen por un doble."""
    global _modelo
    if _modelo is None:
        _modelo = build_language_model()
    return _modelo


def reset_language_model() -> None:
    """Olvida la instancia cacheada. Para pruebas y para recargar configuración."""
    global _modelo
    _modelo = None
