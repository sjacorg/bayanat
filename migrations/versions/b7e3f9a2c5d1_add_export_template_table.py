"""add export template table

Revision ID: b7e3f9a2c5d1
Revises: d4f7a2c9b310
Create Date: 2026-08-06 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7e3f9a2c5d1"
down_revision = "d4f7a2c9b310"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "export_template",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=32), server_default="actor", nullable=False),
        sa.Column("locale", sa.String(length=8), server_default="ar", nullable=False),
        sa.Column("blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("published_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_export_template_user_id"), "export_template", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_export_template_user_id"), table_name="export_template")
    op.drop_table("export_template")
