"""Background system update task with locking and progress tracking."""

from datetime import datetime, timedelta, timezone
from flask import current_app

from enferno.utils.maintenance import disable_maintenance, enable_maintenance
from enferno.utils.update_utils import (
    start_update,
    end_update,
    set_update_message,
    is_update_running,
)
from enferno.admin.models import SystemInfo, UpdateHistory, Notification
from enferno.admin.constants import Constants
from enferno.settings import Config
from enferno.extensions import rds


def perform_system_update_task(skip_backup: bool = False) -> dict:
    """Execute system update in background with system lock.

    This function is imported and registered as a Celery task in
    enferno/tasks/__init__.py (not decorated here).

    NOTE: run_system_update is imported inside function to avoid circular
    dependency (enferno.commands imports enferno.tasks).
    """
    from enferno.commands import run_system_update

    # Clear schedule flag - update is starting now, is_update_running() takes over
    rds.delete("bayanat:update:scheduled")

    lock_acquired = False

    try:
        # Acquire lock - prevents concurrent updates
        if not start_update("Acquiring lock..."):
            return {"success": False, "error": "Update already running"}
        lock_acquired = True

        # Log out all users before maintenance mode
        set_update_message("Logging out all users...")
        session_redis = current_app.config["SESSION_REDIS"]
        session_keys = session_redis.keys("session:*")
        if session_keys:
            session_redis.delete(*session_keys)

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


def schedule_system_update_with_grace_period(skip_backup: bool = False) -> dict:
    """
    Schedule a system update with grace period notification.

    Notifies all users about the pending update, then schedules the actual
    update task to run after the grace period using Celery ETA.

    Args:
        skip_backup: Whether to skip database backup during update

    Returns:
        dict with success status, message, and scheduled time
    """
    # Guard against concurrent updates or double-scheduling
    schedule_key = "bayanat:update:scheduled"
    if rds.exists(schedule_key) or is_update_running():
        return {"success": False, "error": "Update already in progress or scheduled"}

    grace_minutes = Config.UPDATE_GRACE_PERIOD_MINUTES
    scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=grace_minutes)

    # Notify all users about the pending update
    Notification.send_notification_to_all_users(
        event=Constants.NotificationEvent.SYSTEM_UPDATE_PENDING,
        title="System Update Scheduled",
        message=f"Bayanat will be updated in {grace_minutes} minutes. You will be automatically logged out when the update starts. Please save your work.",
        category=Constants.NotificationCategories.ANNOUNCEMENT.value,
        is_urgent=True,
    )

    # Import lazily to avoid circular dependency
    from enferno.tasks import perform_system_update

    # Schedule the actual update using Celery ETA
    # Let Celery generate task ID (avoids collision, still cancellable)
    try:
        task = perform_system_update.apply_async(
            kwargs={"skip_backup": skip_backup}, eta=scheduled_time
        )
        # Only set Redis flag AFTER successful enqueue (prevents false blocks if Celery fails)
        rds.setex(schedule_key, grace_minutes * 60, scheduled_time.isoformat())
    except Exception as e:
        return {"success": False, "error": f"Failed to schedule update: {str(e)}"}

    return {
        "success": True,
        "message": f"Update scheduled for {grace_minutes} minutes from now",
        "scheduled_at": scheduled_time.isoformat(),
        "task_id": task.id,
    }
