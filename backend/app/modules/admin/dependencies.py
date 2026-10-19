"""Dependencias de autenticación y autorización.

La sesión vive en una cookie firmada, marcada `httponly`, no en un token que el
navegador guarde en JavaScript. Un token accesible desde JavaScript es
extraíble por cualquier script inyectado; una cookie `httponly` no.
"""

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import PermissionDeniedError
from app.modules.admin.models import Account
from app.modules.admin.repository import AccountRepository

SESSION_KEY = "account_id"

NOT_AUTHENTICATED = "Se requiere iniciar sesión."
NOT_AUTHORIZED = "No tienes permiso para realizar esta operación."


class NotAuthenticatedError(PermissionDeniedError):
    """No hay sesión activa."""


async def get_current_account(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Account:
    """Cuenta autenticada de la petición.

    La cuenta se recarga de la base en cada petición en lugar de confiar en lo
    que traiga la cookie: así, inhabilitar una cuenta o cambiarle el rol surte
    efecto de inmediato y no cuando expire su sesión.
    """
    raw_id = request.session.get(SESSION_KEY)
    if not raw_id:
        raise NotAuthenticatedError(NOT_AUTHENTICATED)

    try:
        account_id = uuid.UUID(str(raw_id))
    except ValueError as exc:
        request.session.clear()
        raise NotAuthenticatedError(NOT_AUTHENTICATED) from exc

    account = await AccountRepository(session).get_by_id(account_id)
    if account is None or not account.is_active:
        request.session.clear()
        raise NotAuthenticatedError(NOT_AUTHENTICATED)

    return account


async def get_optional_account(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Account | None:
    """La cuenta autenticada, o `None` si no hay sesión.

    Para endpoints públicos cuyo comportamiento cambia si quien pregunta
    pertenece al equipo. El caso concreto es el chatbot: una narradora en
    estado `draft` acepta conversación de una cuenta de administración y la
    rechaza del público, y eso no puede resolverse exigiendo sesión —el
    endpoint es público— ni ignorándola.
    """
    try:
        return await get_current_account(request, session)
    except NotAuthenticatedError:
        return None


async def require_admin(account: Account = Depends(get_current_account)) -> Account:
    """Exige rol de administrador.

    Gestionar cuentas y ver el panel de control y los registros de conversación
    son operaciones de administración, no de edición.
    """
    if not account.is_admin:
        raise PermissionDeniedError(NOT_AUTHORIZED)
    return account
