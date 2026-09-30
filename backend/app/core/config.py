"""Configuración de la aplicación.

Toda la configuración proviene de variables de entorno. Ningún secreto vive en el
código. Ver `.env.example` para el conjunto completo de variables reconocidas.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicación ---------------------------------------------------------
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Base de datos ------------------------------------------------------
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://narrateca:narrateca@localhost:5433/narrateca",
        description="Cadena de conexión a PostgreSQL con extensión pgvector.",
    )
    database_echo: bool = False

    # --- Seguridad ----------------------------------------------------------
    secret_key: str = Field(
        default="cambiar-en-produccion",
        description="Clave de firma de sesiones. Debe sustituirse fuera de desarrollo.",
    )
    session_max_age_seconds: int = 60 * 60 * 8
    #: Política SameSite de la cookie de sesión. "lax" exige que el sitio y la
    #: API compartan dominio, que es la arquitectura recomendada.
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # --- Archivo físico -----------------------------------------------------
    #: Raíz común del material del archivo, organizada en subcarpetas por
    #: comunidad. Vive fuera del repositorio: el acuerdo de confidencialidad
    #: prohíbe versionar el material.
    archive_root: str = "./archivo"

    # --- Almacenamiento de media -------------------------------------------
    storage_backend: Literal["local", "gcs"] = "local"
    storage_local_root: str = "./var/media"
    storage_gcs_bucket_sensitive: str = ""
    storage_gcs_bucket_public: str = ""

    # --- Modelo de lenguaje -------------------------------------------------
    # El proveedor vive detrás de una interfaz. Cambiar de Ollama Cloud a Ollama
    # local o a otro proveedor es una variable de entorno, no un refactor.
    # Ver design.md, decisión 3.
    llm_provider: Literal["ollama", "echo"] = "echo"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_model: str = "llama3.1:70b"
    llm_timeout_seconds: int = 120

    # --- Embeddings (siempre locales) --------------------------------------
    # Ver design.md, decisión 2: el corpus completo nunca sale hacia un tercero.
    #
    # Se eligió un modelo pequeño (~470 MB, 384 dimensiones) porque debe estar
    # cargado para embeber cada consulta, y Cloud Run corre con
    # `min_instances = 0`: un modelo de varios gigabytes haría que la primera
    # pregunta tras un periodo sin tráfico esperara a que se cargue.
    #
    # `deterministic` usa un modelo simulado: permite desarrollar y probar la
    # mecánica del índice sin descargar nada. No sirve para evaluar la calidad
    # de la recuperación.
    embeddings_provider: Literal["onnx", "deterministic"] = "onnx"
    embeddings_model: str = "intfloat/multilingual-e5-small"
    embeddings_dimensions: int = 384

    # --- RAG ----------------------------------------------------------------
    rag_top_k: int = 6
    rag_min_relevance: float = 0.35
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120

    # --- Conversaciones -----------------------------------------------------
    transcript_retention_days: int = 0  # 0 = sin caducidad automática

    # --- CORS ---------------------------------------------------------------
    # `NoDecode` desactiva el intento de pydantic-settings de interpretar el
    # valor como JSON, para poder escribirlo como lista separada por comas en el
    # archivo de entorno, que es como se configura en Cloud Run.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
