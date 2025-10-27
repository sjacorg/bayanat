"""Background system update task with locking and progress tracking."""

from enferno.utils.maintenance import disable_maintenance, enable_maintenance
from enferno.utils.update_utils import (
    start_update,
    end_update,
    set_update_message,
)
from enferno.admin.models import SystemInfo, UpdateHistory
from enferno.settings import Config


def perform_system_update_task(skip_backup: bool = False) -> dict:
    """Execute system update in background with system lock.

    This function is imported and registered as a Celery task in
    enferno/tasks/__init__.py (not decorated here).

    NOTE: run_system_update is imported inside function to avoid circular
    dependency (enferno.commands imports enferno.tasks).
    """
    from enferno.commands import run_system_update
    from enferno.extensions import rds

    # Clear schedule flag - update is starting now, is_update_running() takes over
    rds.delete("bayanat:update:scheduled")

    lock_acquired = False

    try:
        # Acquire lock - prevents concurrent updates
        if not start_update("Acquiring lock..."):
            return {"success": False, "error": "Update already running"}
        lock_acquired = True

        set_update_message("Enabling maintenance mode...")
        if not enable_maintenance("System is being updated. Please wait..."):
            raise RuntimeError("Failed to acquire system lock")
        lock_acquired = True

        set_update_message("Running update...")
        success, message = run_system_update(skip_backup=skip_backup)

        if success:
            new_version = SystemInfo.get_value("app_version") or Config.VERSION
            set_update_message(f"Update complete: {new_version}")
            UpdateHistory(version_to=new_version).save()
        else:
            set_update_message(f"Update failed: {message}")

        return {"success": success, "message": message}

    except Exception as e:
        set_update_message(f"Error: {str(e)}")
        return {"success": False, "error": str(e)}

    finally:
        if lock_acquired:
            disable_maintenance()
        end_update()
