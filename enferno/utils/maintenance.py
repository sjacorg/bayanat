"""
Maintenance mode utilities.

This module provides functions to enable, disable, and check maintenance mode.
Maintenance mode is based on a file lock rather than database to ensure
it works even during database maintenance operations.
"""

import os
import datetime
from flask import current_app, render_template, request
from enferno.utils.logging_utils import get_logger

logger = get_logger()

MAINTENANCE_FILE = "maintenance.lock"


def get_maintenance_file_path():
    """
    Get the path to the maintenance lock file.

    Returns:
        str: Absolute path to the maintenance lock file
    """
    # Use a location that's guaranteed to exist
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    maintenance_dir = os.path.join(base_dir, "instance")

    # Create the directory if it doesn't exist
    if not os.path.exists(maintenance_dir):
        try:
            os.makedirs(maintenance_dir)
            logger.info(f"Created maintenance directory: {maintenance_dir}")
        except Exception as e:
            logger.error(f"Failed to create maintenance directory: {str(e)}")

    return os.path.join(maintenance_dir, MAINTENANCE_FILE)


def is_maintenance_mode():
    """
    Check if maintenance mode is enabled.

    Returns:
        bool: True if maintenance mode is enabled, False otherwise
    """
    return os.path.exists(get_maintenance_file_path())


def enable_maintenance(reason="System maintenance"):
    """
    Enable maintenance mode.

    Args:
        reason (str): Reason for enabling maintenance mode

    Returns:
        bool: True if maintenance mode was enabled successfully
    """
    try:
        with open(get_maintenance_file_path(), "w") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"Maintenance mode enabled at {timestamp}\nReason: {reason}")
        logger.info(f"Maintenance mode enabled: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable maintenance mode: {str(e)}")
        return False


def disable_maintenance():
    """
    Disable maintenance mode.

    Returns:
        bool: True if maintenance mode was disabled successfully
    """
    try:
        if os.path.exists(get_maintenance_file_path()):
            os.remove(get_maintenance_file_path())
        logger.info("Maintenance mode disabled")
        return True
    except Exception as e:
        logger.error(f"Failed to disable maintenance mode: {str(e)}")
        return False


def get_maintenance_details():
    """
    Get maintenance mode details.

    Returns:
        str: Content of maintenance file or empty string if not in maintenance mode
    """
    if not is_maintenance_mode():
        return ""

    try:
        with open(get_maintenance_file_path(), "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read maintenance details: {str(e)}")
        return "System is under maintenance."


def register_maintenance_middleware(app):
    """
    Register the maintenance middleware with a Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def check_maintenance_mode():
        """Check if maintenance mode is enabled and redirect to maintenance page."""
        # Skip for static files and maintenance page
        if request.path.startswith("/static/") or request.path == "/maintenance":
            return None

        # Check maintenance mode
        if is_maintenance_mode():
            try:
                details = get_maintenance_details()
                current_year = datetime.datetime.now().year
                return (
                    render_template("maintenance.html", details=details, current_year=current_year),
                    503,
                )
            except Exception as e:
                logger.error(f"Error rendering maintenance page: {str(e)}")
                # Fallback to simple message if template rendering fails
                return "System is under maintenance", 503
