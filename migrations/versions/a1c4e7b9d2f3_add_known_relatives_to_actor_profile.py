"""add known_relatives to actor_profile

Revision ID: a1c4e7b9d2f3
Revises: d4f7a2c9b310
Create Date: 2026-08-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1c4e7b9d2f3"
down_revision = "d4f7a2c9b310"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "actor_profile",
        sa.Column(
            "known_relatives",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="MP",
        ),
    )


def downgrade():
    op.drop_column("actor_profile", "known_relatives")
