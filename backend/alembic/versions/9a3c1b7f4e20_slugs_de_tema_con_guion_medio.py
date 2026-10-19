"""slugs de tema con guion medio

Unifica la ortografía de los slugs. Los temas usaban guion bajo
(`mujeres_discapacidad`) mientras el contenido exige guion medio
(`un-testimonio`), y ambas grafías aparecían en las mismas URL públicas.

Se renombra **la etiqueta, no la identidad**. El identificador de cada tema se
deriva con `uuid5` del slug original en la migración 058580d982e4, así que
regenerarlo lo cambiaría y dejaría huérfano todo el contenido que lo
referencia. Un slug es un nombre de cara al público; el id es quién es la
cosa. Cambiar lo primero no debe tocar lo segundo.

Por eso 058580d982e4 sigue sembrando con la grafía antigua y es esta migración
la que renombra: así cualquier base —recién creada o ya existente— termina con
los mismos identificadores y los mismos slugs nuevos.

Revision ID: 9a3c1b7f4e20
Revises: 35e838137d08
Create Date: 2026-10-17 09:12:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9a3c1b7f4e20"
down_revision: str | None = "35e838137d08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Antiguo -> nuevo. Solo cambian los dos que llevaban guion bajo; `migrantes` y
# `lgbtq` ya eran de una sola palabra.
RENOMBRES = {
    "mujeres_discapacidad": "mujeres-discapacidad",
    "mujeres_violencia": "mujeres-violencia",
}


def _renombrar(parejas: dict[str, str]) -> None:
    conexion = op.get_bind()
    for origen, destino in parejas.items():
        conexion.execute(
            sa.text("UPDATE themes SET slug = :destino WHERE slug = :origen"),
            {"origen": origen, "destino": destino},
        )
        # El token de acento nombra la variable CSS del tema en el frontend. Se
        # renombra a la vez para que el proyecto tenga una sola ortografía y no
        # haya que recordar cuál aplica en cada capa.
        conexion.execute(
            sa.text("UPDATE themes SET accent_token = :destino WHERE accent_token = :origen"),
            {"origen": origen, "destino": destino},
        )


def upgrade() -> None:
    _renombrar(RENOMBRES)


def downgrade() -> None:
    _renombrar({destino: origen for origen, destino in RENOMBRES.items()})
