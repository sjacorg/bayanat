"""add for_incident to eventtype

Gives event types their own Incidents toggle, independent of Bulletins. Until now
the Incidents screen reused the `for_bulletin` flag, so event types could not be
scoped to Incidents separately. Existing rows are backfilled with `for_bulletin`
so the Incidents event-type list stays identical on day one; admins can then
curate it from there.

Revision ID: c7d2e9f4a1b8
Revises: b3f1c2a4d5e6
Create Date: 2026-06-27

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7d2e9f4a1b8"
down_revision = "b3f1c2a4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: an unstamped database can already have this (see the upgrading guide)
    # If the column already exists, its values cannot be told apart from settings an
    # admin chose, so the one-time copy is skipped rather than risk overwriting them
    if "for_incident" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("eventtype")}:
        return
    op.add_column(
        "eventtype",
        sa.Column("for_incident", sa.Boolean(), server_default=sa.false(), nullable=True),
    )
    # Preserve current behavior: Incidents previously borrowed the Bulletin flag.
    op.execute("UPDATE eventtype SET for_incident = for_bulletin")


def downgrade():
    op.drop_column("eventtype", "for_incident")
