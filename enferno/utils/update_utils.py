import subprocess
from contextlib import suppress
from pathlib import Path
from typing import Optional

from flask import current_app
from sqlalchemy import text

from enferno.extensions import rds, db
from enferno.utils.logging_utils import get_logger

logger = get_logger()

STATUS_KEY = "bayanat:update:status"
LOCK_TTL = 3600


def is_update_running():
    """Check if update is currently running."""
    return bool(rds.get(STATUS_KEY))


def start_update(message="Updating system"):
    """Start update. Returns False if already running (prevents concurrent updates)."""
    if not rds.set(STATUS_KEY, message, nx=True, ex=LOCK_TTL):
        return False
    return True


def end_update():
    """End update and clear status."""
    rds.delete(STATUS_KEY)


def set_update_message(message):
    """Update the status message without clearing the lock."""
    if is_update_running():
        rds.set(STATUS_KEY, message, ex=LOCK_TTL)


def get_update_status():
    """Get current update status message or None if not running."""
    data = rds.get(STATUS_KEY)
    return data.decode() if data else None


def is_update_scheduled():
    """Check if update is scheduled."""
    return bool(rds.get("bayanat:update:scheduled"))


def get_scheduled_update_time():
    """Get scheduled update time or None if not scheduled."""
    data = rds.get("bayanat:update:scheduled")
    return data.decode() if data else None


def rollback_update(
    git_commit: str,
    backup_file: Optional[str] = None,
    restart_service: bool = True,
) -> bool:
    """
    Rollback failed update: restore code, dependencies, and database.

    Args:
        git_commit: Git commit hash to rollback to
        backup_file: Path to database backup file (optional)
        restart_service: Whether to restart service after rollback

    Returns:
        bool: True if rollback succeeded, False otherwise
    """
    # Import here to avoid circular dependency:
    # enferno.tasks -> enferno.commands -> enferno.utils.update_utils
    from enferno.tasks import restart_service as restart
    from enferno.commands import restore_backup

    project_root = Path(current_app.root_path).parent
    rollback_success = True

    # Rollback git to previous commit
    if git_commit:
        try:
            subprocess.run(["git", "reset", "--hard", git_commit], cwd=project_root, check=True)
            logger.info(f"Rolled back code to: {git_commit[:8]}")
        except Exception as e:
            logger.error(f"Git rollback failed: {e}")
            rollback_success = False

        # Restore dependencies to match rolled-back code
        try:
            subprocess.run(["uv", "sync", "--frozen"], cwd=project_root, check=True)
            logger.info("Dependencies restored")
        except Exception as e:
            logger.error(f"Dependency restore failed: {e}")
            rollback_success = False

    # Rollback database from backup
    if backup_file and Path(backup_file).exists():
        try:
            # Clean up database connections
            with suppress(Exception):
                db.session.rollback()
                db.session.remove()
                db.engine.dispose()

            # Terminate active connections
            with suppress(Exception):
                with db.engine.begin() as conn:
                    conn.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) "
                            "FROM pg_stat_activity "
                            "WHERE datname = :dbname AND pid <> pg_backend_pid()"
                        ),
                        {"dbname": db.engine.url.database},
                    )
                logger.info("Terminated active database connections")

            # Restore database backup
            if restore_backup(backup_file, timeout=600):
                logger.info(f"Database restored from: {backup_file}")
            else:
                logger.error("Database restore failed")
                rollback_success = False

        except Exception as e:
            logger.error(f"Database rollback failed: {e}")
            rollback_success = False

    # Restart services if requested
    if restart_service:
        try:
            # Signal app to auto-clear maintenance if rollback succeeded
            if rollback_success:
                rds.set("bayanat:maintenance:auto_clear", "1", ex=300)
            restart("bayanat")
            restart("bayanat-celery")
            logger.info("Services restarted after rollback")
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            rollback_success = False

    return rollback_success
