"""add dossier flag to media

Revision ID: e9c2d7f4a8b3
Revises: b7e3f9a2c5d1
Create Date: 2026-08-14 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e9c2d7f4a8b3"
down_revision = "b7e3f9a2c5d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "media",
        sa.Column("dossier", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade():
    op.drop_column("media", "dossier")
