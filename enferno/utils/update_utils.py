import json
from datetime import datetime, timezone
from enferno.extensions import rds

REDIS_KEY = "bayanat:update:status"
REDIS_TTL = 3600


def set_status(step, step_number, total_steps, error=None):
    """Update Redis with current update step."""
    status = {
        "in_progress": True,
        "step": step,
        "step_number": step_number,
        "total_steps": total_steps,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "last_error": error,
    }
    rds.setex(REDIS_KEY, REDIS_TTL, json.dumps(status))


def set_complete(success, error=None, new_version=None):
    """Mark update as complete."""
    status = {
        "in_progress": False,
        "success": success,
        "error": error,
        "new_version": new_version,
        "end_time": datetime.now(timezone.utc).isoformat(),
    }
    rds.setex(REDIS_KEY, REDIS_TTL, json.dumps(status))


def get_status():
    """Get current update status."""
    data = rds.get(REDIS_KEY)
    return json.loads(data) if data else {"in_progress": False}
