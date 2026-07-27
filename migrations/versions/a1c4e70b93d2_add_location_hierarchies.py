"""add location hierarchies and scope admin levels by hierarchy

Revision ID: a1c4e70b93d2
Revises: f0a3d6c1e8b2
Create Date: 2026-07-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a1c4e70b93d2"
down_revision = "f0a3d6c1e8b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "location_hierarchy",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("title_tr", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
    )

    op.add_column("location_admin_level", sa.Column("hierarchy_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "location_admin_level_hierarchy_id_fkey",
        "location_admin_level",
        "location_hierarchy",
        ["hierarchy_id"],
        ["id"],
    )

    # existing levels stay global: code is unique per hierarchy, and a partial
    # index keeps the legacy (null hierarchy) codes unique on their own.
    # Drop whatever the global unique on code is actually called: a hard coded
    # name would no-op on an install that named it differently, silently leaving
    # the old constraint to reject a second hierarchy's codes.
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_unique_constraints("location_admin_level"):
        if constraint["column_names"] == ["code"]:
            op.drop_constraint(constraint["name"], "location_admin_level", type_="unique")
    op.create_index(
        "ix_location_admin_level_legacy_code",
        "location_admin_level",
        ["code"],
        unique=True,
        postgresql_where=sa.text("hierarchy_id IS NULL"),
    )
    op.create_index(
        "ix_location_admin_level_hierarchy_code",
        "location_admin_level",
        ["hierarchy_id", "code"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_location_admin_level_hierarchy_code", table_name="location_admin_level")
    op.drop_index("ix_location_admin_level_legacy_code", table_name="location_admin_level")
    op.create_unique_constraint("location_admin_level_code_key", "location_admin_level", ["code"])
    op.drop_constraint(
        "location_admin_level_hierarchy_id_fkey", "location_admin_level", type_="foreignkey"
    )
    op.drop_column("location_admin_level", "hierarchy_id")
    op.drop_table("location_hierarchy")
