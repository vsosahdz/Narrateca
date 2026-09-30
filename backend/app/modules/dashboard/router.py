"""Endpoint del panel de control."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.dependencies import require_admin
from app.modules.admin.models import Account
from app.modules.dashboard.schemas import DashboardRead
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/admin/dashboard", tags=["Administración"])


@router.get(
    "",
    response_model=DashboardRead,
    summary="Panel de control",
    description=(
        "Salud del archivo, cobertura de consentimiento, situación de la ingesta y "
        "actividad reciente.\n\n"
        "Las secciones que dependen del chatbot se devuelven en `pending_sections` "
        "con el motivo por el que aún no pueden medirse, en lugar de reportar cero: "
        "un cero haría creer que nadie usa el chatbot, y lo que ocurre es que todavía "
        "no existe.\n\n"
        "Requiere rol de administrador."
    ),
)
async def dashboard(
    _: Account = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> DashboardRead:
    return await DashboardService(session).build()
