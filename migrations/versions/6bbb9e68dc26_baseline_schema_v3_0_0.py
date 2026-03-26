"""baseline schema v3.0.0

This is the baseline migration for Bayanat v3.0.0.

For existing deployments: run `flask db stamp head` to mark this as applied.
For new deployments: `flask create-db` builds the full schema, then `flask db stamp head`.

Revision ID: 6bbb9e68dc26
Revises:
Create Date: 2026-03-26 16:17:37.547634

"""

# revision identifiers, used by Alembic.
revision = "6bbb9e68dc26"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Baseline: schema already exists via create-db or prior manual migrations.
    pass


def downgrade():
    # Cannot downgrade past the baseline.
    raise RuntimeError("Cannot downgrade past the baseline migration.")
