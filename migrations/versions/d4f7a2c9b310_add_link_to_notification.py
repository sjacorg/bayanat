"""add link to notification

Revision ID: d4f7a2c9b310
Revises: b6e3d1a8f254
Create Date: 2026-07-30

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4f7a2c9b310"
down_revision = "b6e3d1a8f254"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notification", sa.Column("link", sa.String(), nullable=True))


def downgrade():
    op.drop_column("notification", "link")
