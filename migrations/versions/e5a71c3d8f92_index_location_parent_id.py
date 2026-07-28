"""index location.parent_id

Every tree walk joins on parent_id, and the table had no index on it at all, so
each recursive pass fell back to a sequential scan.

Revision ID: e5a71c3d8f92
Revises: d4b8c2e91a53
Create Date: 2026-07-29 00:00:00.000000

"""

from alembic import op

revision = "e5a71c3d8f92"
down_revision = "d4b8c2e91a53"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_location_parent_id", "location", ["parent_id"])


def downgrade():
    op.drop_index("ix_location_parent_id", table_name="location")
