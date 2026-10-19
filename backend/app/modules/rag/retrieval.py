"""Recuperación híbrida: vector más léxico.

El puntaje vectorial absoluto no distingue una consulta relevante de una que no
tiene nada que ver: con e5, «receta de mole poblano» puntúa 0.797 contra este
corpus y «¿cómo fue cruzar la frontera?» puntúa 0.807. Un umbral sobre ese
número no puede sostener el requisito de declarar que no hay material.

La búsqueda léxica sí discrimina ahí: «mole poblano» no comparte ninguna palabra
con el archivo. Se fusionan los dos ordenamientos y la decisión de «no tengo
material» se toma sobre la señal combinada (`design.md`, decisión 17).
"""

from dataclasses import dataclass

from sqlalchemy import Float, Integer, and_, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import (
    INDEXABLE_SCOPES,
    ContentItem,
    PublicationStatus,
)
from app.modules.rag.embeddings import EmbeddingModel
from app.modules.rag.lexical import or_tsquery, query_lexemes
from app.modules.rag.models import TEXT_SEARCH_CONFIG, Chunk

#: Constante de la fusión por rango recíproco. Amortigua el peso de las primeras
#: posiciones para que un único ordenamiento no domine a los dos.
RRF_K = 60

#: Cuántos candidatos pide cada ordenamiento antes de fusionar. Mayor que el
#: resultado final, porque un fragmento puede venir bien colocado en uno de los
#: dos y mal en el otro.
CANDIDATES = 40


@dataclass
class RetrievedChunk:
    """Fragmento recuperado, con la traza de por qué salió."""

    chunk_id: str
    content_item_id: str
    theme_slug: str
    item_slug: str
    item_title: str
    text: str
    ordinal: int

    #: Similitud coseno con la consulta. Se conserva para poder auditar, no
    #: para decidir: por sí sola no distingue nada.
    vector_score: float
    #: Puntaje de la búsqueda de texto completo. Cero si no hubo coincidencia.
    lexical_score: float
    #: Puntaje fusionado, que es el que ordena.
    score: float
    #: Si el fragmento tuvo alguna coincidencia léxica con la consulta.
    lexical_match: bool
    #: Fracción de los términos con contenido de la consulta que aparecen en el
    #: fragmento. Es la señal que decide si hay material, porque el puntaje
    #: vectorial no distingue nada por sí solo.
    lexical_coverage: float = 0.0


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    #: Si el sistema considera que tiene material sobre la pregunta.
    has_material: bool
    #: Por qué se concluyó que no lo hay, cuando aplica. Se guarda con la
    #: conversación para poder revisar después si el criterio fue correcto.
    rejection_reason: str | None = None


class HybridRetriever:
    def __init__(self, session: AsyncSession, embedder: EmbeddingModel) -> None:
        self.session = session
        self.embedder = embedder

    def _visible(self):
        """Condición de qué fragmentos pueden recuperarse.

        Se aplica en la consulta y no al filtrar después: un fragmento cuya
        pieza dejó de ser indexable no debe salir de la base siquiera.
        """
        return and_(
            ContentItem.status == PublicationStatus.PUBLISHED,
            ContentItem.consent_scope.in_(list(INDEXABLE_SCOPES)),
        )

    async def _vector_candidates(
        self, theme_slug: str, embedding: list[float]
    ) -> list[tuple[Chunk, float]]:
        distancia = Chunk.embedding.cosine_distance(embedding)
        stmt = (
            select(Chunk, (1 - distancia).label("similitud"))
            .join(ContentItem, Chunk.content_item_id == ContentItem.id)
            .where(Chunk.theme_slug == theme_slug, self._visible())
            .order_by(distancia)
            .limit(CANDIDATES)
        )
        return [(fila[0], float(fila[1])) for fila in (await self.session.execute(stmt)).all()]

    async def _lexical_candidates(
        self, theme_slug: str, lexemes: list[str]
    ) -> list[tuple[Chunk, float, float]]:
        """Candidatos léxicos, con su cobertura de términos.

        Se usa **disyunción** y no conjunción: una pregunta natural siempre trae
        palabras que no están en el archivo, y exigirlas todas rechazaría casi
        cualquier pregunta legítima. La calidad de la coincidencia se mide
        aparte, contando cuántos términos aparecen de verdad.
        """
        if not lexemes:
            return []

        tsquery = func.to_tsquery(TEXT_SEARCH_CONFIG, or_tsquery(lexemes))
        rank = func.ts_rank_cd(Chunk.tsv, tsquery)

        # Cuenta exacta de términos coincidentes. Se calcula en la base y no
        # como aproximación del rango, porque el rango mezcla frecuencia y
        # proximidad y no responde la pregunta que importa: cuántas de las
        # palabras que escribió la persona están realmente en el fragmento.
        coincidencias = sum(
            (
                case(
                    (
                        Chunk.tsv.op("@@")(func.to_tsquery(TEXT_SEARCH_CONFIG, literal(lexema))),
                        1,
                    ),
                    else_=0,
                )
                for lexema in lexemes
            ),
            literal(0),
        )
        cobertura = cast(coincidencias, Float) / float(len(lexemes))

        stmt = (
            select(Chunk, cast(rank, Float).label("rank"), cobertura.label("cobertura"))
            .join(ContentItem, Chunk.content_item_id == ContentItem.id)
            .where(Chunk.theme_slug == theme_slug, self._visible(), Chunk.tsv.op("@@")(tsquery))
            .order_by(cast(coincidencias, Integer).desc(), rank.desc())
            .limit(CANDIDATES)
        )
        return [
            (fila[0], float(fila[1]), float(fila[2]))
            for fila in (await self.session.execute(stmt)).all()
        ]

    async def retrieve(
        self,
        *,
        theme_slug: str,
        query: str,
        top_k: int = 6,
        min_coverage: float = 0.34,
    ) -> RetrievalResult:
        """Recupera fragmentos y decide si hay material sobre la pregunta."""
        texto = query.strip()
        if not texto:
            return RetrievalResult([], False, "consulta vacía")

        lexemas = await query_lexemes(self.session, texto)
        if not lexemas:
            # Solo interrogativos y palabras vacías: no hay nada que buscar.
            return RetrievalResult([], False, "la pregunta no contiene términos con contenido")

        embedding = self.embedder.embed_query(texto)
        vectoriales = await self._vector_candidates(theme_slug, embedding)
        lexicos = await self._lexical_candidates(theme_slug, lexemas)

        if not vectoriales:
            return RetrievalResult([], False, "el corpus de esta comunidad está vacío")

        # Fusión por rango recíproco: cada ordenamiento aporta 1/(k + posición).
        # Se fusionan posiciones y no puntajes porque las dos escalas no son
        # comparables — una es similitud coseno y la otra un rango de ts_rank.
        fusion: dict[str, float] = {}
        for posicion, (chunk, _) in enumerate(vectoriales):
            clave = str(chunk.id)
            fusion[clave] = fusion.get(clave, 0.0) + 1.0 / (RRF_K + posicion + 1)
        for posicion, (chunk, _, _) in enumerate(lexicos):
            clave = str(chunk.id)
            fusion[clave] = fusion.get(clave, 0.0) + 1.0 / (RRF_K + posicion + 1)

        por_id = {str(c.id): c for c, _ in vectoriales}
        por_id |= {str(c.id): c for c, _, _ in lexicos}
        vec_por_id = {str(c.id): s for c, s in vectoriales}
        lex_por_id = {str(c.id): (rank, cob) for c, rank, cob in lexicos}

        ordenados = sorted(fusion.items(), key=lambda par: par[1], reverse=True)[:top_k]

        recuperados = [
            RetrievedChunk(
                chunk_id=chunk_id,
                content_item_id=str(por_id[chunk_id].content_item_id),
                theme_slug=por_id[chunk_id].theme_slug,
                item_slug=por_id[chunk_id].item.slug,
                item_title=por_id[chunk_id].item.title,
                text=por_id[chunk_id].text,
                ordinal=por_id[chunk_id].ordinal,
                vector_score=vec_por_id.get(chunk_id, 0.0),
                lexical_score=lex_por_id.get(chunk_id, (0.0, 0.0))[0],
                score=puntaje,
                lexical_match=chunk_id in lex_por_id,
                lexical_coverage=lex_por_id.get(chunk_id, (0.0, 0.0))[1],
            )
            for chunk_id, puntaje in ordenados
        ]

        has_material, motivo = self._judge(recuperados, min_coverage, len(lexemas))
        if not has_material:
            return RetrievalResult([], False, motivo)

        # El juicio es sobre el conjunto, pero lo que se entrega es cada
        # fragmento. Un fragmento que no comparte **ninguna** palabra con la
        # pregunta entró solo por vecindad vectorial, y el vecindario de este
        # corpus es ancho: medido, un texto sobre una receta de cocina puntúa
        # 0.797 contra uno relevante que puntúa 0.807.
        #
        # Dejarlo pasar no violaría la minimización —se recuperó— pero sí el
        # anclaje: es material ajeno a la pregunta puesto delante del modelo,
        # que es justo la materia prima de una respuesta inventada.
        #
        # Se descarta solo la cobertura cero, no la baja: exigir más dejaría
        # fuera fragmentos que aportan contexto legítimo alrededor del que sí
        # coincide.
        con_coincidencia = [c for c in recuperados if c.lexical_coverage > 0]
        return RetrievalResult(con_coincidencia, True, None)

    def _judge(
        self, chunks: list[RetrievedChunk], min_coverage: float, total_terms: int
    ) -> tuple[bool, str | None]:
        """Decide si los fragmentos recuperados sostienen una respuesta.

        La regla es la **cobertura léxica**, no el puntaje vectorial. Sin
        coincidencia de palabras lo que queda es el ordenamiento semántico de un
        corpus que puntúa alto con cualquier cosa: devolver eso sería inventar
        una respuesta apoyada en testimonios que no vienen al caso.

        El umbral se calibra contra un conjunto de evaluación sobre el archivo
        real (`design.md`, decisión 18). El valor por defecto es conservador.
        """
        if not chunks:
            return False, "sin fragmentos candidatos"

        mejor = max(c.lexical_coverage for c in chunks)
        if mejor <= 0:
            return False, "ninguna coincidencia léxica con el archivo"

        # Con un solo término, exigir una fracción no significa nada: o coincide
        # o no. La comprobación anterior ya resolvió ese caso.
        if total_terms > 1 and mejor < min_coverage:
            return False, (f"cobertura léxica insuficiente ({mejor:.2f} < {min_coverage:.2f})")

        return True, None
