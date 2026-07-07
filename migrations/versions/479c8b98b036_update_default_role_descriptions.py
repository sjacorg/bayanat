"""update default role descriptions

Revision ID: 479c8b98b036
Revises: 68396035f041
Create Date: 2026-07-06 11:06:11.207531

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '479c8b98b036'
down_revision = '68396035f041'
branch_labels = None
depends_on = None


role_table = sa.table(
    "role",
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)

NEW_DESCRIPTIONS = {
    "Admin": (
        "Full access to all items and actions, including Activity Monitor and user "
        "management across the system."
    ),
    "DA": (
        "User can view all items and edit only those assigned to them. User can "
        "review assigned items for peer review."
    ),
    "Mod": "User can manage system data, edit assigned items, and perform bulk updates.",
}

OLD_DESCRIPTION = "System Role"


def upgrade():
    for name, description in NEW_DESCRIPTIONS.items():
        op.execute(
            role_table.update()
            .where(role_table.c.name == name)
            .where(role_table.c.description == OLD_DESCRIPTION)
            .values(description=description)
        )


def downgrade():
    for name, description in NEW_DESCRIPTIONS.items():
        op.execute(
            role_table.update()
            .where(role_table.c.name == name)
            .where(role_table.c.description == description)
            .values(description=OLD_DESCRIPTION)
        )
