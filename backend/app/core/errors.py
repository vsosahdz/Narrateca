"""Errores de dominio.

Los servicios lanzan estos errores sin saber nada de HTTP. El router los traduce
a códigos de estado, de modo que la lógica de negocio permanezca independiente
del transporte.
"""


class DomainError(Exception):
    """Error de negocio. No conoce códigos HTTP."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """La entidad solicitada no existe."""


class ConflictError(DomainError):
    """La operación choca con el estado actual (por ejemplo, un slug duplicado)."""


class ValidationError(DomainError):
    """La operación viola una regla de negocio."""


class PermissionDeniedError(DomainError):
    """La cuenta autenticada no tiene permiso para esta operación."""


class ConsentViolationError(DomainError):
    """La operación violaría el alcance de consentimiento registrado.

    Se distingue de `ValidationError` a propósito: estas violaciones son la razón
    de ser de buena parte del diseño y deben poder auditarse por separado
    (ver `design.md`, decisión 6).
    """
