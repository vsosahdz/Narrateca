# NarraTECa

Plataforma digital de archivo testimonial sobre cuatro comunidades: migrantes,
comunidad LGBTQ+, mujeres con discapacidad, y mujeres y violencia de género.

Difunde fotografías, testimonios, videos, entrevistas, mapas y noticias, e incluye
un chatbot que permite conversar con la voz de cada comunidad, anclada en el
archivo real: cada afirmación proviene de un fragmento recuperado, citado y
enlazado a su pieza original.

## Estructura

```
backend/     API REST en FastAPI · RAG · ingesta
frontend/    Sitio público y panel de administración en Next.js
openspec/    Especificaciones, diseño y tareas del proyecto
docs/        Documentación operativa
```

## Requisitos

- Python 3.12+
- Node.js 20+
- Docker (para PostgreSQL con pgvector en desarrollo)

## Puesta en marcha

```bash
# Base de datos local
docker compose up -d db

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Documentación de la API: http://localhost:8000/docs

## Especificaciones

El proyecto se desarrolla con [OpenSpec](https://github.com/Fission-AI/OpenSpec).
Las capacidades, requisitos y tareas viven en `openspec/`.

```bash
openspec status --change narrateca-fase-1
openspec validate narrateca-fase-1
```

## Confidencialidad

El material del archivo está sujeto a un acuerdo de confidencialidad. **No debe
versionarse en este repositorio bajo ninguna circunstancia.** Las decisiones de
arquitectura que se derivan de esa restricción están documentadas en
`openspec/changes/narrateca-fase-1/design.md`, decisión 2.

## Flujo de trabajo

Ver [docs/flujo-de-trabajo.md](docs/flujo-de-trabajo.md).
