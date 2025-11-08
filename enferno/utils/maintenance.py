"""
Maintenance mode utilities.

This module provides functions to enable, disable, and check maintenance mode.
Maintenance mode is based on a file lock rather than database to ensure
it works even during database maintenance operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import render_template, request
from enferno.utils.logging_utils import get_logger

logger = get_logger()

MAINTENANCE_FILE = "maintenance.lock"


def get_maintenance_file_path() -> Path:
    """
    Get the path to the maintenance lock file.

    Returns:
        Path: Path object to the maintenance lock file
    """
    # Use pathlib for cleaner path handling
    base_dir = Path(__file__).parent.parent.parent
    maintenance_dir = base_dir / "instance"

    # Create the directory if it doesn't exist
    maintenance_dir.mkdir(exist_ok=True)
    logger.info(f"Maintenance directory ready: {maintenance_dir}")

    return maintenance_dir / MAINTENANCE_FILE


def is_maintenance_mode() -> bool:
    """
    Check if maintenance mode is enabled.

    Returns:
        bool: True if maintenance mode is enabled, False otherwise
    """
    return get_maintenance_file_path().exists()


def enable_maintenance(reason: str = "System maintenance") -> bool:
    """
    Enable maintenance mode.

    Args:
        reason: Reason for enabling maintenance mode

    Returns:
        bool: True if maintenance mode was enabled successfully
    """
    try:
        maintenance_file = get_maintenance_file_path()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"Maintenance mode enabled at {timestamp}\nReason: {reason}"

        maintenance_file.write_text(content, encoding="utf-8")
        logger.info(f"Maintenance mode enabled: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable maintenance mode: {e}")
        return False


def disable_maintenance() -> bool:
    """
    Disable maintenance mode.

    Returns:
        bool: True if maintenance mode was disabled successfully
    """
    try:
        maintenance_file = get_maintenance_file_path()
        if maintenance_file.exists():
            maintenance_file.unlink()
        logger.info("Maintenance mode disabled")
        return True
    except Exception as e:
        logger.error(f"Failed to disable maintenance mode: {e}")
        return False


def logout_all_users() -> int:
    """
    Logout all users by clearing their sessions.

    Returns:
        int: Number of users logged out
    """
    try:
        from flask import current_app

        session_redis = current_app.config["SESSION_REDIS"]
        session_keys = session_redis.keys("session:*")

        if session_keys:
            session_redis.delete(*session_keys)
            logger.info(f"Logged out {len(session_keys)} users")
            return len(session_keys)
        else:
            logger.info("No active sessions to logout")
            return 0
    except Exception as e:
        logger.error(f"Failed to logout users: {e}")
        return 0


def get_maintenance_details() -> str:
    """
    Get maintenance mode details.

    Returns:
        str: Content of maintenance file or empty string if not in maintenance mode
    """
    if not is_maintenance_mode():
        return ""

    try:
        maintenance_file = get_maintenance_file_path()
        return maintenance_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read maintenance details: {e}")
        return "System is under maintenance."


def register_maintenance_middleware(app) -> None:
    """
    Register the maintenance middleware with a Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def check_maintenance_mode() -> Optional[tuple[str, int]]:
        """Check if maintenance mode is enabled and redirect to maintenance page."""
        # Skip for static files and maintenance page itself
        if request.path.startswith("/static/") or request.path == "/maintenance":
            return None

        # Check maintenance mode
        if is_maintenance_mode():
            try:
                details = get_maintenance_details()
                current_year = datetime.now().year
                return (
                    render_template("maintenance.html", details=details, current_year=current_year),
                    503,
                )
            except Exception as e:
                logger.error(f"Error rendering maintenance page: {e}")
                # Fallback to simple message if template rendering fails
                return "System is under maintenance", 503

        return None
