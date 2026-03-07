import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from enferno.extensions import db
from enferno.utils.logging_utils import get_logger

logger = get_logger()

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

# Strip explicit BEGIN/COMMIT from SQL since the runner manages transactions
_TX_PATTERN = re.compile(r"^\s*(BEGIN|COMMIT)\s*;?\s*$", re.MULTILINE | re.IGNORECASE)

BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_file VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _ensure_table(session):
    """Create migration_history table if it doesn't exist."""
    session.execute(text(BOOTSTRAP_SQL))
    session.commit()


def _get_migration_files():
    """Return sorted list of .sql migration files."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda f: f.name)


def _get_applied(session):
    """Return set of already-applied migration filenames."""
    rows = session.execute(text("SELECT migration_file FROM migration_history")).all()
    return {row[0] for row in rows}


def _get_pending(session):
    """Return list of pending migration filenames in order."""
    applied = _get_applied(session)
    return [f for f in _get_migration_files() if f.name not in applied]


def run_migrations(dry_run=False, backfill=False):
    """
    Apply pending SQL migrations.

    Args:
        dry_run: If True, list pending migrations without running them.
        backfill: If True, mark all migrations as applied without running them.

    Returns:
        List of migration filenames that were applied (or would be applied in dry_run mode).
    """
    from enferno.admin.models.MigrationHistory import MigrationHistory

    with Session(db.engine) as session:
        _ensure_table(session)
        pending = _get_pending(session)

        if not pending:
            logger.info("Database is up to date. No pending migrations.")
            return []

        names = [f.name for f in pending]

        if dry_run:
            logger.info(f"Found {len(pending)} pending migrations:")
            for name in names:
                logger.info(f"  - {name}")
            return names

        if backfill:
            with session.begin():
                for f in pending:
                    MigrationHistory.record(f.name, session)
            logger.info(f"Backfilled {len(pending)} migrations as applied.")
            return names

        # Apply each migration in its own transaction
        applied = []
        for i, migration_file in enumerate(pending, 1):
            raw_sql = migration_file.read_text(encoding="utf-8").strip()
            if not raw_sql:
                continue
            # Strip BEGIN/COMMIT since runner manages transactions
            sql = _TX_PATTERN.sub("", raw_sql).strip()
            if not sql:
                continue

            try:
                with session.begin():
                    logger.info(f"[{i}/{len(pending)}] Applying {migration_file.name}...")
                    session.execute(text(sql))
                    MigrationHistory.record(migration_file.name, session)
                applied.append(migration_file.name)
            except Exception as e:
                logger.error(f"Migration {migration_file.name} failed: {e}")
                logger.error(f"Stopping. {len(applied)} of {len(pending)} migrations applied.")
                raise

        logger.info(f"Applied {len(applied)} migrations successfully.")
        return applied
