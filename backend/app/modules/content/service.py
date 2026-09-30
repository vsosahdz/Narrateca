"""Reglas de negocio del catálogo de contenido.

Aquí viven las tres reglas que sostienen buena parte del proyecto:

1. **Publicar e indexar son permisos distintos.** Una pieza puede estar en el
   sitio y no alimentar al chatbot.
2. **El texto alternativo bloquea la publicación de contenido visual**, pero no
   el guardado como borrador.
3. **Retirar o revocar el consentimiento retira los fragmentos del índice** en la
   misma operación, de modo que el chatbot nunca cite contenido que ya no está.

A esas se suma la autorización por tema: un editor solo puede tocar el contenido
de las comunidades que tiene asignadas. La regla vive aquí y no en el router para
que sea imposible saltársela agregando un endpoint nuevo.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.admin.models import Account
from app.modules.admin.repository import AuditRepository
from app.modules.content.indexing import IndexSynchronizer, NullIndexSynchronizer
from app.modules.content.models import (
    ConsentScope,
    ContentItem,
    ContentType,
    PublicationStatus,
)
from app.modules.content.repository import ContentRepository
from app.modules.content.schemas import ContentCreate, ContentUpdate
from app.modules.themes.service import ThemeService


class ContentService:
    def __init__(
        self,
        session: AsyncSession,
        indexer: IndexSynchronizer | None = None,
        actor: Account | None = None,
    ) -> None:
        self.session = session
        self.repo = ContentRepository(session)
        self.themes = ThemeService(session)
        self.indexer = indexer or NullIndexSynchronizer()
        self.audit = AuditRepository(session)
        #: Cuenta que ejecuta la operación. Las lecturas públicas no la
        #: requieren; toda escritura sí.
        self.actor = actor

    # --- Autorización -------------------------------------------------------

    def assert_can_edit(self, theme_id: uuid.UUID) -> None:
        """Verifica que la cuenta pueda modificar contenido de ese tema.

        Un administrador puede con todos. Un editor, solo con los temas que
        tiene asignados.
        """
        if self.actor is None:
            raise PermissionDeniedError("Se requiere iniciar sesión.")
        if not self.actor.can_edit_theme(theme_id):
            raise PermissionDeniedError(
                "No tienes permiso para modificar contenido de esta comunidad."
            )

    # --- Lectura ------------------------------------------------------------

    async def list_public(
        self,
        *,
        theme_slug: str | None = None,
        content_type: ContentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContentItem]:
        """Listado para el sitio público: solo piezas publicadas."""
        return await self.repo.list_items(
            theme_slug=theme_slug,
            content_type=content_type,
            status=PublicationStatus.PUBLISHED,
            limit=limit,
            offset=offset,
        )

    async def get_public(self, theme_slug: str, slug: str) -> ContentItem:
        """Detalle público. Una pieza no publicada no existe para el público."""
        item = await self.repo.get_by_theme_and_slug(theme_slug, slug)
        if item is None or item.status is not PublicationStatus.PUBLISHED:
            raise NotFoundError("El contenido solicitado no está disponible.")
        return item

    async def get_by_id(self, item_id: uuid.UUID) -> ContentItem:
        item = await self.repo.get_by_id(item_id)
        if item is None:
            raise NotFoundError("El contenido solicitado no existe.")
        return item

    # --- Escritura ----------------------------------------------------------

    async def create(self, payload: ContentCreate) -> ContentItem:
        theme = await self.themes.get_by_slug(payload.theme_slug)
        self.assert_can_edit(theme.id)

        if await self.repo.get_by_theme_and_slug(payload.theme_slug, payload.slug):
            raise ConflictError(
                f"Ya existe una pieza con el identificador '{payload.slug}' en ese tema."
            )
        if payload.source_ref and await self.repo.get_by_source_ref(payload.source_ref):
            raise ConflictError(f"Ya se importó una pieza desde el origen '{payload.source_ref}'.")

        data = payload.model_dump(exclude={"theme_slug"})
        item = ContentItem(**data, theme_id=theme.id, status=PublicationStatus.DRAFT)
        await self.repo.add(item)
        await self._record("create", item)
        await self.session.commit()
        return item

    async def update(self, item_id: uuid.UUID, payload: ContentUpdate) -> ContentItem:
        item = await self.get_by_id(item_id)
        self.assert_can_edit(item.theme_id)
        was_indexable = item.is_indexable

        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(item, field, value)

        await self.session.flush()
        await self._reconcile_index(item, was_indexable=was_indexable, content_changed=True)
        await self._record("update", item, {"fields": sorted(changes)})
        await self.session.commit()
        return item

    async def publish(self, item_id: uuid.UUID) -> ContentItem:
        """Publica una pieza, si cumple los requisitos para estar en el sitio."""
        item = await self.get_by_id(item_id)
        self.assert_can_edit(item.theme_id)
        self._assert_publishable(item)

        item.status = PublicationStatus.PUBLISHED
        item.published_at = item.published_at or datetime.now(UTC)
        await self.session.flush()

        await self._reconcile_index(item, was_indexable=False)
        await self._record("publish", item, {"indexable": item.is_indexable})
        await self.session.commit()
        return item

    async def withdraw(self, item_id: uuid.UUID) -> ContentItem:
        """Retira una pieza del sitio y, con ella, del índice del chatbot."""
        item = await self.get_by_id(item_id)
        self.assert_can_edit(item.theme_id)
        was_indexable = item.is_indexable

        item.status = PublicationStatus.WITHDRAWN
        await self.session.flush()

        await self._reconcile_index(item, was_indexable=was_indexable)
        await self._record("withdraw", item)
        await self.session.commit()
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get_by_id(item_id)
        self.assert_can_edit(item.theme_id)
        await self._record("delete", item, {"slug": item.slug, "title": item.title})
        # Eliminar del índice siempre, no solo si era indexable: si quedaran
        # fragmentos huérfanos, el chatbot podría citar una pieza inexistente.
        await self.indexer.remove_item(item.id)
        await self.repo.delete(item)
        await self.session.commit()

    # --- Reglas -------------------------------------------------------------

    def _assert_publishable(self, item: ContentItem) -> None:
        """Requisitos para que una pieza pueda estar en el sitio público.

        Se aplican al publicar y no al guardar: un borrador incompleto es un
        estado de trabajo legítimo.
        """
        if item.requires_alt_text and not (item.alt_text or "").strip():
            raise ValidationError(
                "El contenido visual requiere texto alternativo para publicarse. "
                "Campo faltante: alt_text."
            )

        if item.type is ContentType.CURATED_LINK:
            if not item.external_url:
                raise ValidationError("Un enlace curado requiere external_url.")
            if not (item.summary or "").strip():
                raise ValidationError(
                    "Un enlace curado requiere un resumen redactado por el equipo."
                )

    async def _reconcile_index(
        self,
        item: ContentItem,
        *,
        was_indexable: bool,
        content_changed: bool = False,
    ) -> None:
        """Alinea el índice del chatbot con el estado actual de la pieza.

        La transición que importa es la que revoca el permiso: cambiar el
        `consent_scope` a `no_ai` o retirar la pieza debe borrar sus fragmentos
        en la misma operación, no en un trabajo posterior que puede no ejecutarse.
        """
        is_indexable = item.is_indexable

        if is_indexable and (not was_indexable or content_changed):
            await self.indexer.index_item(item.id)
        elif was_indexable and not is_indexable:
            await self.indexer.remove_item(item.id)

    # --- Consentimiento -----------------------------------------------------

    async def set_consent_scope(self, item_id: uuid.UUID, scope: ConsentScope) -> ContentItem:
        """Cambia el alcance de consentimiento y sincroniza el índice.

        Es una operación aparte de `update` a propósito: el consentimiento es la
        decisión más delicada del catálogo y merece su propio punto de entrada,
        auditable por separado.
        """
        item = await self.get_by_id(item_id)
        self.assert_can_edit(item.theme_id)
        was_indexable = item.is_indexable
        previous = item.consent_scope

        item.consent_scope = scope
        await self.session.flush()

        await self._reconcile_index(item, was_indexable=was_indexable)
        await self._record(
            "set_consent_scope",
            item,
            {"from": previous.value, "to": scope.value},
        )
        await self.session.commit()
        return item

    # --- Auditoría ----------------------------------------------------------

    async def _record(self, action: str, item: ContentItem, details: dict | None = None) -> None:
        """Deja constancia de quién hizo qué sobre una pieza y cuándo."""
        await self.audit.record(
            account=self.actor,
            action=action,
            entity_type="content_item",
            entity_id=item.id,
            details=details,
        )
