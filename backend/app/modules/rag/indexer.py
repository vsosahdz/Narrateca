"""Mantenimiento del índice del corpus.

Implementa el puerto `IndexSynchronizer` que el catálogo invoca al publicar,
retirar o cambiar el consentimiento de una pieza. Ese acoplamiento es
deliberado: si el catálogo y el índice se trataran como sistemas separados, se
terminaría con un chatbot que cita testimonios retirados (`design.md`,
decisión 7).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import ContentItem, PublicationStatus
from app.modules.rag.chunking import build_indexable_text, chunk_text
from app.modules.rag.embeddings import EmbeddingModel
from app.modules.rag.models import Chunk, ChunkReviewStatus


@dataclass
class IndexReport:
    indexed_items: int = 0
    removed_items: int = 0
    chunks_created: int = 0
    chunks_removed: int = 0
    skipped_no_consent: int = 0
    skipped_no_text: int = 0


class ChunkIndexer:
    """Sincroniza el índice vectorial y léxico con el catálogo."""

    def __init__(
        self,
        session: AsyncSession,
        embedder: EmbeddingModel,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> None:
        self.session = session
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # --- Puerto IndexSynchronizer -------------------------------------------

    async def index_item(self, item_id: UUID) -> None:
        """Indexa una pieza, reemplazando lo que hubiera de ella."""
        item = await self.session.get(ContentItem, item_id)
        if item is None:
            return
        await self._reindex(item)

    async def remove_item(self, item_id: UUID) -> None:
        """Elimina del índice todos los fragmentos de una pieza."""
        await self.session.execute(delete(Chunk).where(Chunk.content_item_id == item_id))

    # --- Reindexación --------------------------------------------------------

    async def _reindex(self, item: ContentItem) -> int:
        # Siempre se borra antes de escribir. Actualizar en el sitio dejaría
        # fragmentos viejos cuando el texto se acorta, y esos huérfanos serían
        # citables por el chatbot.
        await self.remove_item(item.id)

        if not item.is_indexable:
            return 0

        texto = build_indexable_text(item.title, item.summary, item.body)
        fragmentos = chunk_text(texto, size=self.chunk_size, overlap=self.chunk_overlap)
        if not fragmentos:
            return 0

        vectores = self.embedder.embed_passages([f.text for f in fragmentos])

        for fragmento, vector in zip(fragmentos, vectores, strict=True):
            self.session.add(
                Chunk(
                    content_item_id=item.id,
                    theme_slug=item.theme.slug,
                    ordinal=fragmento.ordinal,
                    text=fragmento.text,
                    char_start=fragmento.char_start,
                    char_end=fragmento.char_end,
                    embedding=vector,
                    # Entra al índice de inmediato, marcado como no revisado:
                    # publicar no debe esperar a una aprobación, pero alguien
                    # debe poder ver qué entró (`design.md`, decisión 7).
                    review_status=ChunkReviewStatus.PENDING,
                )
            )

        await self.session.flush()
        return len(fragmentos)

    # --- Reconstrucción completa --------------------------------------------

    async def rebuild(self, *, theme_slug: str | None = None) -> IndexReport:
        """Reconstruye el índice desde la base de datos relacional.

        PostgreSQL es la fuente de verdad; el índice es derivado y siempre debe
        poder regenerarse. Es también lo que permite cambiar de modelo de
        embeddings sin migrar datos: se reindexa y ya.
        """
        report = IndexReport()

        stmt = select(ContentItem).where(ContentItem.status == PublicationStatus.PUBLISHED)
        if theme_slug:
            stmt = stmt.join(ContentItem.theme).where(ContentItem.theme.has(slug=theme_slug))

        items = list((await self.session.execute(stmt)).unique().scalars().all())

        for item in items:
            if not item.is_indexable:
                report.skipped_no_consent += 1
                await self.remove_item(item.id)
                continue

            creados = await self._reindex(item)
            if creados == 0:
                report.skipped_no_text += 1
                continue

            report.indexed_items += 1
            report.chunks_created += creados

        await self.session.commit()
        return report

    # --- Auditoría -----------------------------------------------------------

    async def audit(self) -> dict[str, int]:
        """Verifica que el índice no contenga nada que no deba.

        Busca las dos formas de divergencia que importan: fragmentos de piezas
        que ya no son indexables, y piezas indexables sin fragmentos.
        """
        huerfanos = await self.session.execute(
            select(func.count(Chunk.id))
            .join(ContentItem, Chunk.content_item_id == ContentItem.id)
            .where(ContentItem.status != PublicationStatus.PUBLISHED)
        )

        sin_consentimiento = await self.session.execute(
            select(func.count(Chunk.id))
            .join(ContentItem, Chunk.content_item_id == ContentItem.id)
            .where(ContentItem.consent_scope != "public")
        )

        indexables = (
            await self.session.execute(
                select(func.count(ContentItem.id)).where(
                    ContentItem.status == PublicationStatus.PUBLISHED,
                    ContentItem.consent_scope == "public",
                )
            )
        ).scalar_one()

        con_fragmentos = (
            await self.session.execute(select(func.count(func.distinct(Chunk.content_item_id))))
        ).scalar_one()

        return {
            "chunks_de_piezas_no_publicadas": huerfanos.scalar_one(),
            "chunks_sin_consentimiento": sin_consentimiento.scalar_one(),
            "piezas_indexables": indexables,
            "piezas_con_fragmentos": con_fragmentos,
            "piezas_indexables_sin_indexar": max(indexables - con_fragmentos, 0),
        }
