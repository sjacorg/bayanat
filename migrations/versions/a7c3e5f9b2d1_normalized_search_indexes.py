"""Expression indexes for normalized Arabic term search on entity search columns

Revision ID: a7c3e5f9b2d1
Revises: d4f7a2c9b310
Create Date: 2026-09-17
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c3e5f9b2d1"
down_revision = "d4f7a2c9b310"
branch_labels = None
depends_on = None

TABLES = ("bulletin", "actor", "actor_profile", "incident")


def upgrade():
    # CONCURRENTLY keeps writes flowing on large tables; it cannot run inside a transaction.
    with op.get_context().autocommit_block():
        for table in TABLES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_{table}_search_normalized "
                f"ON {table} USING gin (normalize_arabic_text(search) gin_trgm_ops)"
            )


def downgrade():
    with op.get_context().autocommit_block():
        for table in TABLES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS ix_{table}_search_normalized")
