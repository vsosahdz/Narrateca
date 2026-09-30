"""crear extension pgvector y tabla de temas

Siembra además las cuatro comunidades de NarraTECa. Son datos y no valores
codificados en la aplicación, por lo que su lugar es una migración y no una
constante en el código (spec `content-catalog`).

Revision ID: 058580d982e4
Revises:
Create Date: 2026-09-08 11:35:28.651036
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "058580d982e4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Espacio de nombres fijo para generar identificadores deterministas a partir del
# slug. Así los cuatro temas tienen el mismo id en desarrollo y en producción, lo
# que hace comparables los volcados entre entornos.
THEME_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

THEMES = [
    {
        "slug": "migrantes",
        "name_es": "Migrantes",
        "name_en": "Migrants",
        "description_es": (
            "Testimonios, entrevistas y materiales sobre las experiencias de personas "
            "migrantes: el tránsito, la llegada y la vida cotidiana en el destino."
        ),
        "description_en": (
            "Testimonies, interviews and materials on the experiences of migrants: "
            "the journey, the arrival and daily life at the destination."
        ),
        "accent_token": "migrantes",
        "position": 1,
    },
    {
        "slug": "lgbtq",
        "name_es": "Comunidad LGBTQ+",
        "name_en": "LGBTQ+ community",
        "description_es": (
            "Voces y materiales sobre las trayectorias, luchas y vida comunitaria de "
            "las personas de la diversidad sexual y de género."
        ),
        "description_en": (
            "Voices and materials on the trajectories, struggles and community life of "
            "people of sexual and gender diversity."
        ),
        "accent_token": "lgbtq",
        "position": 2,
    },
    {
        "slug": "mujeres_discapacidad",
        "name_es": "Mujeres con discapacidad",
        "name_en": "Women with disabilities",
        "description_es": (
            "Testimonios y materiales sobre las experiencias de mujeres con "
            "discapacidad: autonomía, barreras y formas de organización."
        ),
        "description_en": (
            "Testimonies and materials on the experiences of women with disabilities: "
            "autonomy, barriers and forms of organizing."
        ),
        "accent_token": "mujeres_discapacidad",
        "position": 3,
    },
    {
        "slug": "mujeres_violencia",
        "name_es": "Mujeres y violencia de género",
        "name_en": "Women and gender-based violence",
        "description_es": (
            "Materiales sobre la violencia de género y las trayectorias de las mujeres "
            "que la han enfrentado y documentado."
        ),
        "description_en": (
            "Materials on gender-based violence and the trajectories of the women who "
            "have faced and documented it."
        ),
        "accent_token": "mujeres_violencia",
        "position": 4,
    },
]


def upgrade() -> None:
    # El índice vectorial vive en la misma base que el contenido, para que
    # PostgreSQL siga siendo la única fuente de verdad y el índice sea
    # reconstruible desde ella.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    themes = op.create_table(
        "themes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name_es", sa.String(length=160), nullable=False),
        sa.Column("name_en", sa.String(length=160), nullable=False),
        sa.Column("description_es", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("accent_token", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_themes")),
    )
    op.create_index(op.f("ix_themes_slug"), "themes", ["slug"], unique=True)

    op.bulk_insert(
        themes,
        [
            {
                **theme,
                "id": uuid.uuid5(THEME_NAMESPACE, theme["slug"]),
                "is_active": True,
            }
            for theme in THEMES
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_themes_slug"), table_name="themes")
    op.drop_table("themes")
    # La extensión no se elimina: puede haber otros objetos que dependan de ella.
