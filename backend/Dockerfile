# Imagen del backend de NarraTECa.
#
# Dos decisiones gobiernan este archivo, y ambas vienen del mismo hecho: Cloud
# Run corre con `min_instances = 0`, así que el arranque en frío lo paga la
# primera persona que pregunta algo después de un rato sin tráfico.
#
# 1. El modelo de embeddings se descarga DURANTE EL BUILD, no en el primer uso.
#    Descargarlo en caliente añadiría medio minuto a esa primera petición y
#    convertiría la disponibilidad de Hugging Face en una dependencia de
#    ejecución del chatbot.
#
# 2. Se usa ONNX Runtime y no PyTorch. Mismo modelo, mismos vectores, y la
#    imagen baja de unos 2,5 GB a unos 900 MB.

# --- Etapa de dependencias ---------------------------------------------------
FROM python:3.12-slim AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Solo el manifiesto primero: si no cambian las dependencias, esta capa se
# reutiliza aunque cambie todo el código.
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .

# --- Etapa del modelo --------------------------------------------------------
FROM deps AS model

ARG EMBEDDINGS_MODEL=intfloat/multilingual-e5-small
ENV HF_HOME=/opt/models \
    HF_HUB_DISABLE_TELEMETRY=1

RUN /opt/venv/bin/python -c "\
from huggingface_hub import hf_hub_download; \
[hf_hub_download('${EMBEDDINGS_MODEL}', f) for f in ('onnx/model.onnx','tokenizer.json','config.json')]"

# --- Imagen final ------------------------------------------------------------
FROM python:3.12-slim AS runtime

# `curl` queda para la comprobación de salud; nada más se instala.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# No se ejecuta como root. Si alguien encuentra una forma de ejecutar código en
# el proceso, no debe encontrarse además con privilegios de administrador.
RUN useradd --create-home --uid 10001 narrateca

COPY --from=deps /opt/venv /opt/venv
COPY --from=model /opt/models /opt/models

WORKDIR /app

# Directorio escribible para el almacenamiento local de desarrollo. En
# producción el backend usa Cloud Storage y este directorio queda sin usar,
# pero existir evita que la aplicación tenga que crearlo sin permisos.
RUN mkdir -p /var/narrateca/media && chown -R narrateca:narrateca /var/narrateca

COPY --chown=narrateca:narrateca alembic.ini ./
COPY --chown=narrateca:narrateca alembic ./alembic
COPY --chown=narrateca:narrateca app ./app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/models \
    HF_HUB_OFFLINE=1 \
    STORAGE_LOCAL_ROOT=/var/narrateca/media \
    PORT=8080

USER narrateca
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/ready" || exit 1

# Un solo worker por contenedor: Cloud Run escala agregando instancias, no
# procesos. Varios workers aquí competirían por la misma CPU asignada.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
