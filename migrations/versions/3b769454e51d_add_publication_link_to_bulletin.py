"""add publication_link to bulletin

Adds a link to the publication (report, article) a bulletin appeared in, shown in
the bulletin editor as a core dynamic field and exported to the public archive.

Revision ID: 3b769454e51d
Revises: a7c3e5f9b2d1
Create Date: 2026-10-27

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3b769454e51d"
down_revision = "a7c3e5f9b2d1"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Adding a nullable column is metadata-only but needs a brief exclusive lock on
    # bulletin; fail fast rather than queue behind long reads and block everyone.
    conn.exec_driver_sql("SET LOCAL lock_timeout = '10s'")
    if "publication_link" not in {c["name"] for c in sa.inspect(conn).get_columns("bulletin")}:
        op.add_column("bulletin", sa.Column("publication_link", sa.Text(), nullable=True))

    # Register the core dynamic field right after public_description (idempotent).
    # Later fields shift down one so the order stays deterministic and keeps any
    # custom ordering an admin has set.
    exists = conn.exec_driver_sql("""
        SELECT 1 FROM dynamic_fields
        WHERE name = 'publication_link' AND entity_type = 'bulletin' AND core = true
        """).scalar()
    if exists:
        return
    after = conn.exec_driver_sql("""
        SELECT sort_order FROM dynamic_fields
        WHERE name = 'public_description' AND entity_type = 'bulletin' AND core = true
        """).scalar() or 6
    conn.exec_driver_sql(
        "UPDATE dynamic_fields SET sort_order = sort_order + 1 "
        "WHERE entity_type = 'bulletin' AND sort_order > %(after)s",
        {"after": after},
    )
    conn.exec_driver_sql(
        """
        INSERT INTO dynamic_fields (
            name, title, entity_type, field_type, searchable,
            ui_component, schema_config, ui_config, validation_config,
            options, active, sort_order, core
        )
        VALUES (
            'publication_link', 'Publication Link', 'bulletin', 'text', false,
            'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
            '[]'::jsonb, true, %(after)s + 1, true
        )
        """,
        {"after": after},
    )


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("""
        DELETE FROM dynamic_fields
        WHERE name = 'publication_link' AND entity_type = 'bulletin' AND core = true
        """)
    op.drop_column("bulletin", "publication_link")
