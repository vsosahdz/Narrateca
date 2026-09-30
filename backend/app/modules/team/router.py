"""Endpoints del equipo de investigación."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.dependencies import require_admin
from app.modules.admin.models import Account
from app.modules.team.schemas import TeamMemberCreate, TeamMemberRead, TeamMemberUpdate
from app.modules.team.service import TeamService

router = APIRouter(prefix="/team", tags=["Equipo"])
admin_router = APIRouter(prefix="/admin/team", tags=["Administración"])


def get_service(session: AsyncSession = Depends(get_session)) -> TeamService:
    return TeamService(session)


@router.get(
    "",
    response_model=list[TeamMemberRead],
    summary="Listar integrantes del equipo de investigación",
)
async def list_team(service: TeamService = Depends(get_service)) -> list[TeamMemberRead]:
    members = await service.list_members(only_active=True)
    return [TeamMemberRead.model_validate(m) for m in members]


@admin_router.get(
    "",
    response_model=list[TeamMemberRead],
    summary="Listar integrantes para administración",
)
async def admin_list_team(
    _: Account = Depends(require_admin),
    service: TeamService = Depends(get_service),
) -> list[TeamMemberRead]:
    members = await service.list_members(only_active=False)
    return [TeamMemberRead.model_validate(m) for m in members]


@admin_router.post(
    "",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un integrante",
)
async def create_member(
    payload: TeamMemberCreate,
    _: Account = Depends(require_admin),
    service: TeamService = Depends(get_service),
) -> TeamMemberRead:
    return TeamMemberRead.model_validate(await service.create(payload))


@admin_router.patch(
    "/{member_id}",
    response_model=TeamMemberRead,
    summary="Actualizar un integrante",
)
async def update_member(
    member_id: uuid.UUID,
    payload: TeamMemberUpdate,
    _: Account = Depends(require_admin),
    service: TeamService = Depends(get_service),
) -> TeamMemberRead:
    return TeamMemberRead.model_validate(await service.update(member_id, payload))


@admin_router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un integrante",
)
async def delete_member(
    member_id: uuid.UUID,
    _: Account = Depends(require_admin),
    service: TeamService = Depends(get_service),
) -> None:
    await service.delete(member_id)
