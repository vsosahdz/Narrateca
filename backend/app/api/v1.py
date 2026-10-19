"""Agregación de routers de la versión 1 de la API.

Cada módulo de dominio expone un `router`. Este archivo es el único lugar donde
se declaran las rutas de la API pública, de modo que el mapa de endpoints sea
legible de un vistazo.
"""

from fastapi import APIRouter

from app.modules.admin.router import router as admin_router
from app.modules.archive.router import router as archive_router
from app.modules.chat.router import router as chat_router
from app.modules.content.router import admin_router as content_admin_router
from app.modules.content.router import router as content_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.media.router import router as media_router
from app.modules.news.router import router as news_router
from app.modules.team.router import admin_router as team_admin_router
from app.modules.team.router import router as team_router
from app.modules.themes.router import router as themes_router

api_router = APIRouter()

api_router.include_router(themes_router)
api_router.include_router(content_router)
api_router.include_router(content_admin_router)
api_router.include_router(news_router)
api_router.include_router(team_router)
api_router.include_router(team_admin_router)
api_router.include_router(media_router)
api_router.include_router(archive_router)
api_router.include_router(dashboard_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router)

# Los módulos siguientes se registran conforme se implementan:
#   La persistencia de conversaciones (grupo 12) se añade al módulo `chat`.
