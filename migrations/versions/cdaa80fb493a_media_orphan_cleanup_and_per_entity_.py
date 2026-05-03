"""media orphan cleanup and per-entity etag uniqueness

Cleans up media records and replaces the global etag unique constraint
with per-bulletin and per-actor constraints.

Steps:
  1. Soft-delete orphaned media (no bulletin or actor attachment)
  2. Soft-delete same-bulletin duplicate etags (keep newest)
  3. Soft-delete same-actor duplicate etags (keep newest)
  4. Drop the global unique index on etag
  5. Create per-bulletin and per-actor partial unique indexes
  6. Set deleted=FALSE where NULL, enforce NOT NULL + DEFAULT

All cleanup uses soft-delete (deleted=TRUE). No files are removed.

Revision ID: cdaa80fb493a
Revises: 6bbb9e68dc26
Create Date: 2026-04-11 14:42:07.890989

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "cdaa80fb493a"
down_revision = "6bbb9e68dc26"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Soft-delete orphaned media (not attached to any bulletin or actor)
    op.execute(
        """
        UPDATE media SET deleted = TRUE
        WHERE bulletin_id IS NULL
          AND actor_id IS NULL
          AND (deleted IS NULL OR deleted = FALSE)
    """
    )

    # 2. Soft-delete same-bulletin duplicate etags (keep the newest per bulletin)
    op.execute(
        """
        UPDATE media SET deleted = TRUE
        WHERE id IN (
            SELECT m.id FROM media m
            INNER JOIN (
                SELECT etag, bulletin_id, MAX(id) AS keep_id
                FROM media
                WHERE etag IS NOT NULL
                  AND bulletin_id IS NOT NULL
                  AND (deleted IS NULL OR deleted = FALSE)
                GROUP BY etag, bulletin_id
                HAVING COUNT(*) > 1
            ) dups ON m.etag = dups.etag
                  AND m.bulletin_id = dups.bulletin_id
                  AND m.id != dups.keep_id
            WHERE (m.deleted IS NULL OR m.deleted = FALSE)
        )
    """
    )

    # 3. Soft-delete same-actor duplicate etags (keep the newest per actor)
    op.execute(
        """
        UPDATE media SET deleted = TRUE
        WHERE id IN (
            SELECT m.id FROM media m
            INNER JOIN (
                SELECT etag, actor_id, MAX(id) AS keep_id
                FROM media
                WHERE etag IS NOT NULL
                  AND actor_id IS NOT NULL
                  AND (deleted IS NULL OR deleted = FALSE)
                GROUP BY etag, actor_id
                HAVING COUNT(*) > 1
            ) dups ON m.etag = dups.etag
                  AND m.actor_id = dups.actor_id
                  AND m.id != dups.keep_id
            WHERE (m.deleted IS NULL OR m.deleted = FALSE)
        )
    """
    )

    # 4. Drop the global unique index
    op.execute(
        """
        DROP INDEX IF EXISTS ix_media_etag_unique_not_deleted
    """
    )

    # 5. Create per-entity partial unique indexes
    op.execute(
        """
        CREATE UNIQUE INDEX ix_media_etag_bulletin_unique
        ON media (etag, bulletin_id)
        WHERE deleted = FALSE AND bulletin_id IS NOT NULL
    """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX ix_media_etag_actor_unique
        ON media (etag, actor_id)
        WHERE deleted = FALSE AND actor_id IS NOT NULL
    """
    )

    # 6. Now safe to fix the deleted column on media
    op.execute("UPDATE media SET deleted = FALSE WHERE deleted IS NULL")
    op.execute("ALTER TABLE media ALTER COLUMN deleted SET DEFAULT FALSE")
    op.execute("ALTER TABLE media ALTER COLUMN deleted SET NOT NULL")


def downgrade():
    # Restore global unique index, drop per-entity indexes
    op.execute("DROP INDEX IF EXISTS ix_media_etag_bulletin_unique")
    op.execute("DROP INDEX IF EXISTS ix_media_etag_actor_unique")
    op.execute(
        """
        CREATE UNIQUE INDEX ix_media_etag_unique_not_deleted
        ON media (etag)
        WHERE deleted = FALSE
    """
    )
    # Note: soft-deleted records are NOT restored (data cleanup is one-way)
    op.execute("ALTER TABLE media ALTER COLUMN deleted DROP NOT NULL")
