"""add public_description to bulletin

Adds a curated, public-facing description to bulletins. This is distinct from the
internal `description`: it holds the SJAC-authored summary shown in the public
archive. The field is also registered as a core dynamic field so it appears in
the bulletin editor.

Revision ID: b3f1c2a4d5e6
Revises: cdaa80fb493a
Create Date: 2026-05-29

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3f1c2a4d5e6"
down_revision = "cdaa80fb493a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bulletin", sa.Column("public_description", sa.Text(), nullable=True))

    # Register the core dynamic field (idempotent). exec_driver_sql avoids
    # text() colon parsing clashing with JSON values like {"width":"w-50"}.
    conn = op.get_bind()
    conn.exec_driver_sql("""
        INSERT INTO dynamic_fields (
            name, title, entity_type, field_type, searchable,
            ui_component, schema_config, ui_config, validation_config,
            options, active, sort_order, core
        )
        SELECT
            'public_description', 'Public Description', 'bulletin', 'long_text', false,
            'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
            '[]'::jsonb, true, COALESCE((
                SELECT sort_order
                FROM dynamic_fields
                WHERE name = 'description' AND entity_type = 'bulletin' AND core = true
                LIMIT 1
            ), 6), true
        WHERE NOT EXISTS (
            SELECT 1 FROM dynamic_fields
            WHERE name = 'public_description' AND entity_type = 'bulletin' AND core = true
        )
        """)


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("""
        DELETE FROM dynamic_fields
        WHERE name = 'public_description' AND entity_type = 'bulletin' AND core = true
        """)
    op.drop_column("bulletin", "public_description")
