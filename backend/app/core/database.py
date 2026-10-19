"""Motor de base de datos y sesiones.

PostgreSQL es la fuente de verdad del proyecto. El índice vectorial vive en la
misma base mediante pgvector y es reconstruible por completo desde aquí
(ver spec `rag-ingestion`, requisito de reconstrucción).
"""

import enum
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Enum de PostgreSQL que almacena el *valor*, no el nombre del miembro.

    Sin `values_callable`, SQLAlchemy guarda el nombre del miembro —`DRAFT`—
    mientras el código compara contra su valor —`draft`—, y la base rechaza la
    inserción con `invalid input value for enum`. El error aparece al sembrar,
    no al definir el modelo, que es lo que lo hace molesto de diagnosticar.
    """
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


# Convención de nombres explícita para que las migraciones de Alembic generen
# nombres estables de índices y restricciones en lugar de nombres aleatorios.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Trae los valores generados por el servidor (`created_at`, `updated_at`) en
    # el mismo INSERT/UPDATE mediante RETURNING. Sin esto, leer esas columnas
    # después de un flush dispara una carga diferida, que en un contexto
    # asíncrono falla con `MissingGreenlet` en vez de simplemente ser lenta.
    __mapper_args__ = {"eager_defaults": True}


class TimestampMixin:
    """Marcas de tiempo de creación y actualización."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


engine = create_async_engine(
    str(settings.database_url),
    echo=settings.database_echo,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """Dependencia de FastAPI que entrega una sesión por petición.

    **No confirma la transacción.** Confirmar aquí, en el desmontaje de la
    dependencia, produce una carrera observable: el desmontaje no está
    garantizado a completarse antes de que la respuesta llegue al cliente, así
    que quien recibe un 201 y consulta de inmediato puede no ver lo que acaba de
    crear. Se reprodujo en aproximadamente 1 de cada 40 escrituras seguidas de
    una lectura inmediata.

    El límite de la transacción pertenece al caso de uso, no al transporte: cada
    método de servicio que modifica datos confirma explícitamente al terminar.
    Eso hace que la escritura y su entrada de auditoría sean atómicas y que el
    dato esté visible antes de responder.

    Aquí solo queda la red de seguridad: revertir si algo escapó sin confirmar.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
