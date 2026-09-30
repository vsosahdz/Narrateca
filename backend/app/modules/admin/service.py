"""Reglas de negocio de cuentas y autenticación."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.security import hash_password, needs_rehash, verify_password
from app.modules.admin.models import Account, Role
from app.modules.admin.repository import AccountRepository, AuditRepository
from app.modules.admin.schemas import AccountCreate, AccountUpdate
from app.modules.themes.service import ThemeService


class AuthenticationError(PermissionDeniedError):
    """Credenciales inválidas o cuenta inhabilitada."""


#: Mensaje único para credenciales inválidas y para correos inexistentes.
#: Distinguirlos permitiría averiguar qué correos tienen cuenta.
INVALID_CREDENTIALS = "Correo o contraseña incorrectos."


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AccountRepository(session)
        self.audit = AuditRepository(session)
        self.themes = ThemeService(session)

    # --- Autenticación ------------------------------------------------------

    async def authenticate(self, email: str, password: str) -> Account:
        """Verifica credenciales y devuelve la cuenta.

        Ante cualquier fallo lanza el mismo error con el mismo mensaje, sin
        revelar si el correo existe.
        """
        account = await self.repo.get_by_email(email)

        if account is None:
            # Se verifica igualmente contra un hash ficticio para que el tiempo
            # de respuesta no delate si el correo existe.
            verify_password(password, _DUMMY_HASH)
            raise AuthenticationError(INVALID_CREDENTIALS)

        if not verify_password(password, account.password_hash):
            raise AuthenticationError(INVALID_CREDENTIALS)

        if not account.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)

        # Endurecimiento transparente: si los parámetros de hashing subieron,
        # se regenera con la contraseña que acaba de verificarse.
        if needs_rehash(account.password_hash):
            account.password_hash = hash_password(password)

        account.last_login_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.commit()
        return account

    async def change_password(
        self, account: Account, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, account.password_hash):
            raise ValidationError("La contraseña actual no es correcta.")
        account.password_hash = hash_password(new_password)
        await self.session.flush()
        await self.audit.record(
            account=account, action="change_password", entity_type="account", entity_id=account.id
        )
        await self.session.commit()

    # --- Gestión de cuentas -------------------------------------------------

    async def get(self, account_id: uuid.UUID) -> Account:
        account = await self.repo.get_by_id(account_id)
        if account is None:
            raise NotFoundError("La cuenta solicitada no existe.")
        return account

    async def list_accounts(self) -> list[Account]:
        return await self.repo.list_all()

    async def create(self, payload: AccountCreate, *, actor: Account) -> Account:
        email = payload.email.lower()
        if await self.repo.get_by_email(email):
            raise ConflictError("Ya existe una cuenta con ese correo.")

        account = Account(
            email=email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        account.themes = [await self.themes.get_by_slug(slug) for slug in payload.theme_slugs]

        await self.repo.add(account)
        await self.audit.record(
            account=actor,
            action="create_account",
            entity_type="account",
            entity_id=account.id,
            details={"email": email, "role": account.role.value},
        )
        await self.session.commit()
        return account

    async def update(
        self, account_id: uuid.UUID, payload: AccountUpdate, *, actor: Account
    ) -> Account:
        account = await self.get(account_id)
        data = payload.model_dump(exclude_unset=True)

        theme_slugs = data.pop("theme_slugs", None)
        if theme_slugs is not None:
            account.themes = [await self.themes.get_by_slug(slug) for slug in theme_slugs]

        for field, value in data.items():
            setattr(account, field, value)

        # Una cuenta no puede quitarse a sí misma el rol de administrador ni
        # inhabilitarse: es la forma más común de quedarse sin acceso al panel.
        if account.id == actor.id:
            if payload.role is not None and payload.role is not Role.ADMIN:
                raise ValidationError(
                    "Una cuenta no puede quitarse a sí misma el rol de administrador."
                )
            if payload.is_active is False:
                raise ValidationError("Una cuenta no puede inhabilitarse a sí misma.")

        await self.session.flush()
        await self.audit.record(
            account=actor,
            action="update_account",
            entity_type="account",
            entity_id=account.id,
            details=data,
        )
        await self.session.commit()
        return account

    async def delete(self, account_id: uuid.UUID, *, actor: Account) -> None:
        account = await self.get(account_id)
        if account.id == actor.id:
            raise ValidationError("Una cuenta no puede eliminarse a sí misma.")

        email = account.email
        await self.repo.delete(account)
        await self.audit.record(
            account=actor,
            action="delete_account",
            entity_type="account",
            entity_id=account_id,
            details={"email": email},
        )
        await self.session.commit()


#: Hash de una contraseña arbitraria, usado para igualar el tiempo de respuesta
#: cuando el correo no existe.
_DUMMY_HASH = hash_password("contraseña-que-nunca-se-usa-para-nada")
