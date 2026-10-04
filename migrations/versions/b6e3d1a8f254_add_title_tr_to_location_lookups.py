"""add title_tr to location admin levels and location types

Revision ID: b6e3d1a8f254
Revises: f0a3d6c1e8b2
Create Date: 2026-07-19 13:40:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b6e3d1a8f254"
down_revision = "f0a3d6c1e8b2"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: an unstamped database can already have this (see the upgrading guide)
    for table in ("location_admin_level", "location_type"):
        if "title_tr" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}:
            op.add_column(table, sa.Column("title_tr", sa.String(), nullable=True))


def downgrade():
    op.drop_column("location_type", "title_tr")
    op.drop_column("location_admin_level", "title_tr")
