"""Background system update task with locking and progress tracking."""

from enferno.utils.maintenance import enable_maintenance, disable_maintenance
from enferno.utils.update_utils import set_status, set_complete, get_status
from enferno.admin.models import SystemInfo
from enferno.settings import Config


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
        # Lock system
        set_status("Acquiring lock", 1, 6)
        if not enable_maintenance("System is being updated. Please wait..."):
            raise RuntimeError("Failed to acquire system lock")
        lock_acquired = True

        # Run update
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
        # Always unlock
        if lock_acquired:
            disable_maintenance()
