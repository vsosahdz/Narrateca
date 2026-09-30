"""Reglas de negocio del equipo de investigación."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.modules.team.models import TeamMember
from app.modules.team.schemas import TeamMemberCreate, TeamMemberUpdate


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_members(self, *, only_active: bool = True) -> list[TeamMember]:
        stmt = select(TeamMember).order_by(TeamMember.position, TeamMember.full_name)
        if only_active:
            stmt = stmt.where(TeamMember.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, member_id: uuid.UUID) -> TeamMember:
        member = await self.session.get(TeamMember, member_id)
        if member is None:
            raise NotFoundError("El integrante solicitado no existe.")
        return member

    async def create(self, payload: TeamMemberCreate) -> TeamMember:
        member = TeamMember(**payload.model_dump())
        self.session.add(member)
        await self.session.flush()
        await self.session.commit()
        return member

    async def update(self, member_id: uuid.UUID, payload: TeamMemberUpdate) -> TeamMember:
        member = await self.get(member_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(member, field, value)

        if member.photo_key and not (member.photo_alt or "").strip():
            raise ValidationError(
                "Una fotografía requiere texto alternativo. Campo faltante: photo_alt."
            )

        await self.session.flush()
        await self.session.commit()
        return member

    async def delete(self, member_id: uuid.UUID) -> None:
        member = await self.get(member_id)
        await self.session.delete(member)
        await self.session.flush()
        await self.session.commit()
