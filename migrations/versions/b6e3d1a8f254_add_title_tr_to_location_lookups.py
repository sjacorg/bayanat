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
    op.add_column("location_admin_level", sa.Column("title_tr", sa.String(), nullable=True))
    op.add_column("location_type", sa.Column("title_tr", sa.String(), nullable=True))


def downgrade():
    op.drop_column("location_type", "title_tr")
    op.drop_column("location_admin_level", "title_tr")
