"""backfill location admin level display_order

Levels seeded before this point carry a null display_order, and full_location
orders its components by that column. With every value null the order is
arbitrary, so an installation that never dragged the levels into an order in
system administration gets its location text assembled in no particular order.
Codes were already assigned in ladder order, so they are the correct fallback.

Revision ID: c9e1b7a4f206
Revises: a1c4e70b93d2
Create Date: 2026-07-27 00:00:00.000000

"""

from alembic import op

revision = "c9e1b7a4f206"
down_revision = "a1c4e70b93d2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE location_admin_level SET display_order = code "
        "WHERE display_order IS NULL OR display_order = 0"
    )


def downgrade():
    # the previous state was "unordered", which is not worth restoring
    pass
