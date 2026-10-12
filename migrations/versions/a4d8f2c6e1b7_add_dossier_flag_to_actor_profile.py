"""add dossier flag to actor profile

Revision ID: a4d8f2c6e1b7
Revises: c3d8e1f6a9b4
Create Date: 2026-10-02 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a4d8f2c6e1b7"
down_revision = "c3d8e1f6a9b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "actor_profile",
        sa.Column("dossier", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade():
    op.drop_column("actor_profile", "dossier")
