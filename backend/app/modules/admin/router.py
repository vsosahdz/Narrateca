"""Endpoints de autenticación y gestión de cuentas."""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.dependencies import SESSION_KEY, get_current_account, require_admin
from app.modules.admin.models import Account
from app.modules.admin.repository import AuditRepository
from app.modules.admin.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    AuditLogRead,
    LoginRequest,
    PasswordChange,
)
from app.modules.admin.service import AccountService

router = APIRouter(prefix="/admin", tags=["Administración"])


def get_service(session: AsyncSession = Depends(get_session)) -> AccountService:
    return AccountService(session)


# --- Sesión -----------------------------------------------------------------


@router.post(
    "/login",
    response_model=AccountRead,
    summary="Iniciar sesión",
    description=(
        "Establece una cookie de sesión firmada y `httponly`. Ante credenciales "
        "incorrectas devuelve el mismo error tanto si el correo existe como si no, "
        "para no revelar qué correos tienen cuenta."
    ),
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AccountService = Depends(get_service),
) -> AccountRead:
    account = await service.authenticate(payload.email, payload.password)
    # Se regenera la sesión al autenticar, para evitar fijación de sesión.
    request.session.clear()
    request.session[SESSION_KEY] = str(account.id)
    return AccountRead.model_validate(account)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
)
async def logout(request: Request) -> None:
    request.session.clear()


@router.get(
    "/me",
    response_model=AccountRead,
    summary="Cuenta de la sesión actual",
)
async def me(account: Account = Depends(get_current_account)) -> AccountRead:
    return AccountRead.model_validate(account)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar la contraseña propia",
)
async def change_password(
    payload: PasswordChange,
    account: Account = Depends(get_current_account),
    service: AccountService = Depends(get_service),
) -> None:
    await service.change_password(account, payload.current_password, payload.new_password)


# --- Cuentas (solo administración) ------------------------------------------


@router.get(
    "/accounts",
    response_model=list[AccountRead],
    summary="Listar cuentas",
)
async def list_accounts(
    _: Account = Depends(require_admin),
    service: AccountService = Depends(get_service),
) -> list[AccountRead]:
    return [AccountRead.model_validate(a) for a in await service.list_accounts()]


@router.post(
    "/accounts",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta",
    description=(
        "Solo una cuenta con rol de administrador puede crear cuentas. Los temas "
        "asignados solo tienen efecto para el rol `editor`."
    ),
)
async def create_account(
    payload: AccountCreate,
    actor: Account = Depends(require_admin),
    service: AccountService = Depends(get_service),
) -> AccountRead:
    return AccountRead.model_validate(await service.create(payload, actor=actor))


@router.patch(
    "/accounts/{account_id}",
    response_model=AccountRead,
    summary="Actualizar una cuenta",
)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    actor: Account = Depends(require_admin),
    service: AccountService = Depends(get_service),
) -> AccountRead:
    return AccountRead.model_validate(await service.update(account_id, payload, actor=actor))


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una cuenta",
)
async def delete_account(
    account_id: uuid.UUID,
    actor: Account = Depends(require_admin),
    service: AccountService = Depends(get_service),
) -> None:
    await service.delete(account_id, actor=actor)


# --- Auditoría --------------------------------------------------------------


@router.get(
    "/audit",
    response_model=list[AuditLogRead],
    summary="Registro de auditoría",
    description="Quién hizo qué y cuándo sobre el contenido y las cuentas.",
)
async def list_audit(
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
    _: Account = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogRead]:
    repo = AuditRepository(session)
    entries = (
        await repo.list_for_entity(entity_id) if entity_id else await repo.list_recent(limit=limit)
    )
    return [AuditLogRead.model_validate(e) for e in entries]
