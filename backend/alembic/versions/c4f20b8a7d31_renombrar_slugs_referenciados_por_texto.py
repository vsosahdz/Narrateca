"""renombrar slugs referenciados por texto

Completa la migración 9a3c1b7f4e20, que renombró los slugs de tema a guion
medio pero solo en la tabla `themes`.

Tres tablas guardan el slug como texto en lugar de referenciar `themes.id`:

    chunks.theme_slug             partición del índice vectorial
    archive_documents.theme_slug  comunidad a la que pertenece un documento
    persona_configs.theme_slug    comunidad de la narradora

`persona_configs` nació después del renombrado, así que ya tenía la grafía
nueva. Las otras dos se quedaron con la antigua, y en el caso de `chunks` eso
no es cosmético: el recuperador filtra por `theme_slug`, de modo que los
fragmentos de una comunidad renombrada dejaron de ser alcanzables. El chatbot
habría respondido «no cuento con material» sobre un corpus que estaba ahí.

El fallo no apareció en las pruebas porque cada prueba crea sus datos después
del renombrado. Solo se ve en una base que ya tenía contenido indexado, que es
exactamente el caso de cualquier instalación real.

Lección, anotada donde toca: cuando un slug se usa como clave en otras tablas,
renombrarlo es una migración de datos de todas ellas, no solo de su dueña.

Revision ID: c4f20b8a7d31
Revises: 1ed97d4e8e2d
Create Date: 2026-10-19 10:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4f20b8a7d31"
down_revision: str | None = "1ed97d4e8e2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RENOMBRES = {
    "mujeres_discapacidad": "mujeres-discapacidad",
    "mujeres_violencia": "mujeres-violencia",
}

#: Tablas con una columna `theme_slug` que apunta a un tema.
TABLAS = ("chunks", "archive_documents", "persona_configs")


def _renombrar(parejas: dict[str, str]) -> None:
    conexion = op.get_bind()
    for tabla in TABLAS:
        for origen, destino in parejas.items():
            conexion.execute(
                sa.text(
                    f"UPDATE {tabla} SET theme_slug = :destino WHERE theme_slug = :origen"  # noqa: S608
                ),
                {"origen": origen, "destino": destino},
            )


def upgrade() -> None:
    _renombrar(RENOMBRES)


def downgrade() -> None:
    _renombrar({destino: origen for origen, destino in RENOMBRES.items()})
