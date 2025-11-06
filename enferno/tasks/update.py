"""Background system update task with locking and progress tracking."""

import json
from datetime import datetime, timedelta, timezone
from flask import current_app

from enferno.utils.maintenance import disable_maintenance, enable_maintenance, logout_all_users
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


def perform_system_update_task(skip_backup: bool = False, user_id: int = None) -> dict:
    """Execute system update in background with system lock.

    This function is imported and registered as a Celery task in
    enferno/tasks/__init__.py (not decorated here).

    NOTE: run_system_update is imported inside function to avoid circular
    dependency (enferno.commands imports enferno.tasks).

    Args:
        skip_backup: Whether to skip database backup
        user_id: ID of user who initiated the update (None for scheduled/system updates)
    """
    from enferno.commands import run_system_update

    # Clear schedule flag - update is starting now, is_update_running() takes over
    rds.delete("bayanat:update:scheduled")

    # Acquire lock BEFORE try block - prevents concurrent updates
    # If we can't get the lock, return early without entering try/finally
    if not start_update("Acquiring lock..."):
        return {"success": False, "error": "Update already running"}

    # If we get here, we acquired the lock - finally block WILL cleanup
    # Initialize versions early so they're available in exception handler
    current_version = None
    target_version = Config.VERSION

    try:

        # Log out all users before maintenance mode
        set_update_message("Logging out all users...")
        logout_all_users()

        set_update_message("Enabling maintenance mode...")
        if not enable_maintenance("System is being updated. Please wait..."):
            raise RuntimeError("Failed to acquire system lock")

        # Capture current version before update
        # Do this BEFORE any operations that might fail
        current_version = Config.VERSION

        set_update_message("Running update...")
        success, message = run_system_update(skip_backup=skip_backup)

        if success:
            # After restart, Config.VERSION will be loaded from new pyproject.toml
            # For now, read it directly from the checked-out tag
            from pathlib import Path
            import tomli

            project_root = Path(current_app.root_path).parent
            pyproject_path = project_root / "pyproject.toml"
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
                new_version = pyproject_data["project"]["version"]

            set_update_message(f"Update complete: {new_version}")

            # Clear release notes cache so new version is fetched
            rds.delete("bayanat:release:notes")

            # Only record history if version actually changed
            if new_version != current_version:
                UpdateHistory(
                    version_from=current_version,
                    version_to=new_version,
                    status="success",
                    user_id=user_id,
                ).save()
        else:
            set_update_message(f"Update failed: {message}")
            # For failures, target version is unknown (update failed before determining it)
            # Store failure in Redis first (survives DB rollback)
            _store_failure_in_redis(current_version, None, message, user_id)
            # Try to save to DB (might fail if rolled back to version without table)
            # .save() handles exceptions internally - logs error and returns False
            UpdateHistory(
                version_from=current_version,
                version_to=None,
                status="failed",
                user_id=user_id,
            ).save()

        return {"success": success, "message": message}

    except Exception as e:
        set_update_message(f"Error: {str(e)}")
        # Use captured version from before update (don't query DB in exception handler)
        # If version wasn't captured yet, try to get it but don't fail if DB is unavailable
        failure_current_version = current_version

        if failure_current_version is None:
            # Version not captured yet, use Config.VERSION
            try:
                failure_current_version = Config.VERSION
            except Exception:
                # Unable to read version, use None
                failure_current_version = None

        # Store failure in Redis first (survives any DB issues)
        # Target version is unknown for failures
        _store_failure_in_redis(failure_current_version, None, str(e), user_id)

        # Try to save to DB (might fail if DB is unavailable)
        # .save() handles exceptions internally - logs error and returns False
        UpdateHistory(
            version_from=failure_current_version,
            version_to=None,
            status="failed",
            user_id=user_id,
        ).save()

        return {"success": False, "error": str(e)}

    finally:
        # Cleanup - only runs if we acquired the lock (got past the check above)
        # If lock acquisition failed, we returned early before entering try block
        # Don't clear maintenance here - let maintenance page detect completion
        end_update()


def _store_failure_in_redis(version_from, version_to, error_message, user_id):
    """Store update failure in Redis as backup (survives DB rollback).

    This ensures failures are recorded even if database rollback removes
    the UpdateHistory table or invalidates connections.
    """
    try:
        failure_key = "bayanat:update:failure"
        failure_data = {
            "version_from": version_from,
            "version_to": version_to,
            "status": "failed",
            "user_id": user_id,
            "error": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Store for 24 hours - long enough to sync to DB when table exists
        rds.setex(failure_key, 86400, json.dumps(failure_data))
        current_app.logger.info(f"Update failure stored in Redis: {failure_key}")
    except Exception as redis_error:
        # If Redis fails, log it but don't crash - at least we tried
        current_app.logger.error(f"Failed to store update failure in Redis: {redis_error}")


def schedule_system_update_with_grace_period(
    skip_backup: bool = False, user_id: int = None
) -> dict:
    """
    Schedule a system update with grace period notification.

    Notifies all users about the pending update, then schedules the actual
    update task to run after the grace period using Celery ETA.

    Args:
        skip_backup: Whether to skip database backup during update
        user_id: ID of user who scheduled the update

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
            kwargs={"skip_backup": skip_backup, "user_id": user_id}, eta=scheduled_time
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
