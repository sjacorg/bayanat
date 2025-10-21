"""Background system update task with locking and progress tracking."""

from enferno.utils.maintenance import disable_maintenance, enable_maintenance
from enferno.utils.update_utils import (
    get_status,
    is_update_in_progress,
    set_complete,
    set_status,
    clear_update_lock,
)
from enferno.admin.models import SystemInfo
from enferno.settings import Config


def progress_callback(step_name):
    """Helper to update status during update process."""
    steps = {
        "backup": ("Backing up database", 2),
        "pull": ("Pulling code changes", 3),
        "install": ("Installing dependencies", 4),
        "migrate": ("Running migrations", 5),
        "restart": ("Restarting service", 6),
    }
    if step_name in steps:
        msg, step_num = steps[step_name]
        set_status(msg, step_num, 6)


def perform_system_update_task(skip_backup: bool = False) -> dict:
    """Execute system update in background with system lock.

    This function is imported and registered as a Celery task in
    enferno/tasks/__init__.py (not decorated here).

    NOTE: run_system_update is imported inside function to avoid circular
    dependency (enferno.commands imports enferno.tasks).
    """
    from enferno.commands import run_system_update

    lock_acquired = False

    try:
        if is_update_in_progress():
            return {"success": False, "error": "Update already in progress", "status": get_status()}

        # Lock system
        set_status("Acquiring lock", 1, 6)
        if not enable_maintenance("System is being updated. Please wait..."):
            raise RuntimeError("Failed to acquire system lock")
        lock_acquired = True

        # Run update (task names like "backup", "pull", etc trigger progress_callback)
        success, message = run_system_update(skip_backup=skip_backup)

        # Mark complete
        if success:
            new_version = SystemInfo.get_value("app_version") or Config.VERSION
            set_complete(success=True, new_version=new_version)
        else:
            set_complete(success=False, error=message)

        return {"success": success, "message": message}

    except Exception as e:
        set_complete(success=False, error=str(e))
        return {"success": False, "error": str(e)}

    finally:
        # Always unlock and clear lock
        if lock_acquired:
            disable_maintenance()
        clear_update_lock()
