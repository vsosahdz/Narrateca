"""Acceso a datos de cuentas y auditoría."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import Account, AuditLogEntry


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, account_id: uuid.UUID) -> Account | None:
        return await self.session.get(Account, account_id)

    async def get_by_email(self, email: str) -> Account | None:
        # El correo se normaliza a minúsculas al guardarse, así que la búsqueda
        # también, para que el inicio de sesión no dependa de cómo se escribió.
        stmt = select(Account).where(Account.email == email.lower())
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_all(self) -> list[Account]:
        stmt = select(Account).order_by(Account.full_name)
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def add(self, account: Account) -> Account:
        self.session.add(account)
        await self.session.flush()
        return account

    async def delete(self, account: Account) -> None:
        await self.session.delete(account)
        await self.session.flush()


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        account: Account | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            account_id=account.id if account else None,
            account_email=account.email if account else "sistema",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_entity(self, entity_id: uuid.UUID) -> list[AuditLogEntry]:
        stmt = (
            select(AuditLogEntry)
            .where(AuditLogEntry.entity_id == entity_id)
            .order_by(AuditLogEntry.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 100) -> list[AuditLogEntry]:
        stmt = select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
