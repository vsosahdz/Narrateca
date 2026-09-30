"""Generación de representaciones vectoriales.

**Siempre en infraestructura propia.** Enviar el corpus a un servicio de
embeddings externo anularía por completo la restricción de confidencialidad,
por más cuidado que se tenga con el proveedor de generación de texto: el corpus
es todo el archivo, mientras que hacia el modelo de lenguaje solo viajan los
fragmentos recuperados de cada consulta (ver `design.md`, decisión 2).

Se ejecuta con ONNX Runtime y no con PyTorch. Mismo modelo y mismos vectores,
pero la imagen del contenedor baja de unos 2,5 GB a unos 400 MB y el arranque en
frío se acorta. Eso importa porque Cloud Run corre con `min_instances = 0`: sin
esa diferencia, la primera pregunta después de un periodo sin tráfico esperaría
a que se cargue el modelo, y en un sitio de tráfico intermitente esa es la
mayoría de las primeras preguntas.
"""

import hashlib
import threading
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.core.config import settings

#: El modelo distingue lo que se indexa de lo que se pregunta. Omitir estos
#: prefijos degrada la recuperación de forma silenciosa: sigue devolviendo
#: resultados, solo que peores.
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "

MAX_TOKENS = 512


class EmbeddingModel(ABC):
    """Puerto de embeddings."""

    #: Dimensión de los vectores. Cambiarla exige reindexar todo el corpus.
    dimensions: int

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Vectores de fragmentos del archivo, para indexar."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Vector de una consulta de la persona usuaria."""


def _normalize(matrix: np.ndarray) -> np.ndarray:
    """Normaliza a longitud 1 para que el producto punto sea la similitud coseno."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


class OnnxEmbeddingModel(EmbeddingModel):
    """Modelo multilingüe ejecutado localmente con ONNX Runtime.

    Multilingüe a propósito: el archivo está en español y el chatbot responde
    también en inglés, así que una pregunta en inglés debe recuperar fragmentos
    en español sin traducir la consulta.
    """

    dimensions = 384

    def __init__(self, model_id: str, batch_size: int = 16) -> None:
        self.model_id = model_id
        self.batch_size = batch_size
        self._lock = threading.Lock()
        self._session = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        # Carga perezosa y una sola vez: el modelo pesa cientos de megabytes y
        # no debe cargarse al importar el módulo, porque entonces lo pagarían
        # también los procesos que nunca tocan el chatbot (migraciones, CLI).
        if self._session is not None:
            return
        with self._lock:
            if self._session is not None:
                return

            import onnxruntime as ort
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer

            model_path = hf_hub_download(self.model_id, "onnx/model.onnx")
            tokenizer_path = hf_hub_download(self.model_id, "tokenizer.json")

            tokenizer = Tokenizer.from_file(tokenizer_path)
            tokenizer.enable_truncation(max_length=MAX_TOKENS)
            tokenizer.enable_padding()

            options = ort.SessionOptions()
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            # Un solo hilo por sesión: el servidor ya atiende varias peticiones
            # en paralelo, y dejar que cada una abra su propio grupo de hilos
            # produce contención en lugar de velocidad.
            options.intra_op_num_threads = 1

            self._tokenizer = tokenizer
            self._session = ort.InferenceSession(
                model_path, options, providers=["CPUExecutionProvider"]
            )

    def _encode(self, texts: list[str]) -> np.ndarray:
        self._ensure_loaded()
        assert self._tokenizer is not None and self._session is not None

        salida: list[np.ndarray] = []
        for inicio in range(0, len(texts), self.batch_size):
            lote = texts[inicio : inicio + self.batch_size]
            encoded = self._tokenizer.encode_batch(lote)

            ids = np.array([e.ids for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)

            entradas = {"input_ids": ids, "attention_mask": mask}
            nombres = {i.name for i in self._session.get_inputs()}
            if "token_type_ids" in nombres:
                entradas["token_type_ids"] = np.zeros_like(ids)

            estados = self._session.run(None, entradas)[0]

            # Promedio de los tokens reales, ignorando el relleno: incluirlo
            # arrastraría todos los vectores hacia el vector del relleno y haría
            # que los textos cortos se parecieran entre sí.
            expandida = mask[..., None].astype(np.float32)
            sumados = (estados * expandida).sum(axis=1)
            cuenta = np.maximum(expandida.sum(axis=1), 1e-9)
            salida.append(sumados / cuenta)

        return _normalize(np.vstack(salida))

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode([PASSAGE_PREFIX + t for t in texts]).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0].tolist()


class DeterministicEmbeddingModel(EmbeddingModel):
    """Modelo simulado, para pruebas y para desarrollar sin descargar nada.

    No entiende de significado: produce un vector estable a partir del hash del
    texto. Sirve para verificar la mecánica del índice —que se guarden los
    fragmentos correctos, que se respete el consentimiento, que retirar una
    pieza borre sus vectores— sin esperar a que cargue un modelo real.

    La calidad de la recuperación **no** puede evaluarse con esto.
    """

    dimensions = 384

    def _vector(self, text: str) -> list[float]:
        semilla = hashlib.sha256(text.strip().lower().encode("utf-8")).digest()
        generador = np.random.default_rng(int.from_bytes(semilla[:8], "big"))
        vector = generador.standard_normal(self.dimensions).astype(np.float32)
        return (vector / np.linalg.norm(vector)).tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=1)
def _real_model() -> EmbeddingModel:
    return OnnxEmbeddingModel(settings.embeddings_model)


@lru_cache(maxsize=1)
def _fake_model() -> EmbeddingModel:
    return DeterministicEmbeddingModel()


def get_embedding_model() -> EmbeddingModel:
    """Dependencia de FastAPI que entrega el modelo configurado."""
    if settings.embeddings_provider == "deterministic":
        return _fake_model()
    return _real_model()
