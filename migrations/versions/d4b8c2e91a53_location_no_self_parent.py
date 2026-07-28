"""prevent a location from being its own parent

Mirrors label_no_self_parent. A full cycle cannot be expressed as a check
constraint, so the application guards that; this catches the simplest case for
writers that never go through the application, which is how the location table
has picked up inconsistencies before.

Revision ID: d4b8c2e91a53
Revises: c9e1b7a4f206
Create Date: 2026-07-27 00:00:00.000000

"""

from alembic import op

revision = "d4b8c2e91a53"
down_revision = "c9e1b7a4f206"
branch_labels = None
depends_on = None


def upgrade():
    # break any existing self-parent rows first, otherwise the constraint cannot be added
    op.execute("""
        CREATE TEMP TABLE promoted_roots AS
            SELECT id FROM location WHERE parent_id = id;
        UPDATE location SET parent_id = NULL WHERE id IN (SELECT id FROM promoted_roots);
        -- promoting a row to a root changes its ancestry, so its stored path and
        -- everything under it are now wrong. flask doctor would report them; clear
        -- them instead so the next regenerate is the only thing needed.
        UPDATE location SET full_location = NULL, id_tree = NULL
         WHERE id IN (SELECT id FROM promoted_roots)
            OR id_tree LIKE ANY (SELECT '%[' || id || ']%' FROM promoted_roots);
        DROP TABLE promoted_roots;
        """)
    op.create_check_constraint("location_no_self_parent", "location", "parent_id != id")


def downgrade():
    op.drop_constraint("location_no_self_parent", "location", type_="check")
