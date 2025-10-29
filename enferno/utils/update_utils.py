from datetime import datetime, timezone
import json
from enferno.extensions import rds

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
