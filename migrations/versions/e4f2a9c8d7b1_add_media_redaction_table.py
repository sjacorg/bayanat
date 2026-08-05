"""add media redaction table

Revision ID: e4f2a9c8d7b1
Revises: b3f1c2a4d5e6
Create Date: 2026-06-05 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e4f2a9c8d7b1"
down_revision = "b3f1c2a4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "media_redaction",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_media_id", sa.Integer(), nullable=False),
        sa.Column("result_media_id", sa.Integer(), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["result_media_id"], ["media.id"]),
        sa.ForeignKeyConstraint(["source_media_id"], ["media.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_media_redaction_result_media_id"),
        "media_redaction",
        ["result_media_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_media_redaction_source_media_id"),
        "media_redaction",
        ["source_media_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_media_redaction_user_id"),
        "media_redaction",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_media_redaction_user_id"), table_name="media_redaction")
    op.drop_index(op.f("ix_media_redaction_source_media_id"), table_name="media_redaction")
    op.drop_index(op.f("ix_media_redaction_result_media_id"), table_name="media_redaction")
    op.drop_table("media_redaction")
