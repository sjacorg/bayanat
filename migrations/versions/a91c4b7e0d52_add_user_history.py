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
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["target_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_history_target_user_id"), "user_history", ["target_user_id"], unique=False
    )

    # Baseline snapshot per existing user. A revision is only meaningful against
    # the one before it, and user accounts are edited rarely, so without a
    # baseline the first edit of each existing account would be undiffable
    # for as long as that account goes untouched. user_id is left null: no
    # acting user made this change. Mirrors User.to_history_dict().
    op.execute("""
        INSERT INTO user_history (target_user_id, data, user_id, created_at, updated_at, deleted)
        SELECT
            u.id,
            json_build_object(
                'id', u.id,
                'name', u.name,
                'username', u.username,
                'email', u.email,
                'active', u.active,
                'roles', COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', r.id, 'name', r.name) ORDER BY r.id)
                        FROM roles_users ru
                        JOIN role r ON r.id = ru.role_id
                        WHERE ru.user_id = u.id
                    ),
                    '[]'::json
                ),
                'view_usernames', u.view_usernames,
                'view_simple_history', u.view_simple_history,
                'view_full_history', u.view_full_history,
                'can_self_assign', u.can_self_assign,
                'can_edit_locations', u.can_edit_locations,
                'can_export', u.can_export,
                'can_import_web', u.can_import_web,
                'can_access_media', u.can_access_media
            ),
            NULL,
            timezone('utc', now()),
            timezone('utc', now()),
            false
        FROM "user" u
        """)


def downgrade():
    op.drop_index(op.f("ix_user_history_target_user_id"), table_name="user_history")
    op.drop_table("user_history")
