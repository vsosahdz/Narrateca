"""Puerto de sincronización con el índice del chatbot.

Publicar contenido modifica lo que la persona sintética puede decir. Si el
catálogo y el índice se tratan como sistemas separados, se termina con un
chatbot que cita testimonios retirados o que ignora los que se subieron ayer
(ver `design.md`, decisión 7).

Este puerto hace explícito ese acoplamiento desde ahora. El grupo 10 conecta la
implementación real; mientras tanto, la implementación nula deja el sistema
funcionando y las reglas de consentimiento ya escritas y probadas.
"""

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from fastapi import Depends

from app.core.database import get_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class IndexSynchronizer(Protocol):
    """Mantiene el índice vectorial alineado con el catálogo."""

    async def index_item(self, item_id: UUID) -> None:
        """Segmenta e indexa una pieza recién publicada e indexable."""
        ...

    async def remove_item(self, item_id: UUID) -> None:
        """Elimina del índice todos los fragmentos de una pieza."""
        ...


class NullIndexSynchronizer:
    """Implementación nula, usada hasta que exista el índice real.

    No es un descarte silencioso: registra la intención para que sea visible en
    el panel de control que hay piezas pendientes de indexar.
    """

    def __init__(self) -> None:
        self.indexed: list[UUID] = []
        self.removed: list[UUID] = []

    async def index_item(self, item_id: UUID) -> None:
        self.indexed.append(item_id)

    async def remove_item(self, item_id: UUID) -> None:
        self.removed.append(item_id)


def get_index_synchronizer(
    session: "AsyncSession" = Depends(get_session),
) -> IndexSynchronizer:
    """Dependencia de FastAPI que entrega el sincronizador real del índice.

    Se resuelve aquí y no en el módulo `rag` para no invertir la dirección de
    las dependencias: el catálogo define el puerto, el índice lo implementa.
    """
    from app.modules.rag.embeddings import get_embedding_model
    from app.modules.rag.indexer import ChunkIndexer

    return ChunkIndexer(session, get_embedding_model())
