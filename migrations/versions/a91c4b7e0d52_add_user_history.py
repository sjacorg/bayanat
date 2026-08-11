"""add user history

Revision ID: a91c4b7e0d52
Revises: d4f7a2c9b310
Create Date: 2026-08-11

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a91c4b7e0d52"
down_revision = "d4f7a2c9b310"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["target_user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_history_target_user_id"), "user_history", ["target_user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_user_history_target_user_id"), table_name="user_history")
    op.drop_table("user_history")
