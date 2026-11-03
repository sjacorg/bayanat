"""turn bulletin publication_link into a publication_links list

A document can appear in several publications. Each existing link becomes a
one-item list, and the core dynamic field is renamed to match.

Revision ID: c4e8a1d2f7b3
Revises: 3b769454e51d
Create Date: 2026-11-02

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e8a1d2f7b3"
down_revision = "3b769454e51d"
branch_labels = None
depends_on = None


def _columns(conn):
    return {c["name"] for c in sa.inspect(conn).get_columns("bulletin")}


def upgrade():
    conn = op.get_bind()

    custom = conn.exec_driver_sql("""
        SELECT 1 FROM dynamic_fields
        WHERE name = 'publication_links' AND entity_type = 'bulletin' AND core = false
        """).scalar()
    if custom:
        raise RuntimeError(
            "A custom bulletin field named 'publication_links' already exists. "
            "Rename or remove it, then rerun the upgrade."
        )

    # A database built from current models already has the new core field, and the
    # previous migration may have added the old one next to it: keep the new one.
    removed = conn.exec_driver_sql("""
        DELETE FROM dynamic_fields
        WHERE name = 'publication_link' AND entity_type = 'bulletin' AND core = true
          AND EXISTS (SELECT 1 FROM dynamic_fields WHERE name = 'publication_links'
                      AND entity_type = 'bulletin' AND core = true)
        RETURNING sort_order
        """).scalar()
    if removed is not None:
        conn.exec_driver_sql(
            "UPDATE dynamic_fields SET sort_order = sort_order - 1 "
            "WHERE entity_type = 'bulletin' AND sort_order > %(removed)s",
            {"removed": removed},
        )
    conn.exec_driver_sql("""
        UPDATE dynamic_fields SET name = 'publication_links', title = 'Publication Links'
        WHERE name = 'publication_link' AND entity_type = 'bulletin' AND core = true
        """)

    # Add, copy, drop instead of ALTER TYPE: a constant default and a column drop are
    # metadata-only, so the large bulletin table is never rewritten. Each step commits
    # on its own so the exclusive lock from the DDL is not held through the backfill
    # scan. Every step is guarded, so an interrupted run resumes cleanly.
    with op.get_context().autocommit_block():
        conn.exec_driver_sql("SET lock_timeout = '10s'")
        try:
            if "publication_links" not in _columns(conn):
                conn.exec_driver_sql(
                    "ALTER TABLE bulletin ADD COLUMN publication_links TEXT[] NOT NULL DEFAULT '{}'"
                )
            if "publication_link" in _columns(conn):
                conn.exec_driver_sql("""
                    UPDATE bulletin SET publication_links = ARRAY[publication_link]
                    WHERE coalesce(publication_link, '') <> '' AND publication_links = '{}'
                    """)
                conn.exec_driver_sql("ALTER TABLE bulletin DROP COLUMN publication_link")
        finally:
            conn.exec_driver_sql("RESET lock_timeout")


def downgrade():
    # Keeps only the first link of each bulletin.
    conn = op.get_bind()
    conn.exec_driver_sql("""
        UPDATE dynamic_fields SET name = 'publication_link', title = 'Publication Link'
        WHERE name = 'publication_links' AND entity_type = 'bulletin' AND core = true
        """)
    if "publication_link" not in _columns(conn):
        op.add_column("bulletin", sa.Column("publication_link", sa.Text(), nullable=True))
    if "publication_links" in _columns(conn):
        conn.exec_driver_sql("""
            UPDATE bulletin SET publication_link = publication_links[1]
            WHERE cardinality(publication_links) > 0
            """)
        conn.exec_driver_sql("ALTER TABLE bulletin DROP COLUMN publication_links")
