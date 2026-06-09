# -*- coding: utf-8 -*-
import json
import os
import subprocess
from datetime import date, datetime, timedelta, timezone

import requests
from packaging.version import Version

from enferno.admin.constants import Constants
from enferno.admin.models import Activity, Location
from enferno.admin.models.Notification import Notification
from enferno.extensions import db, rds
from enferno.tasks import celery, cfg
from enferno.user.models import Session
from enferno.utils.backup_utils import pg_dump, upload_to_s3
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.maintenance")

GITHUB_LATEST_URL = "https://api.github.com/repos/sjacorg/bayanat/releases/latest"
UPDATE_CACHE_KEY = "bayanat:update:available"
UPDATE_NOTIFIED_KEY = "bayanat:update:available:notified"


def _strip_v(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def _redis_get_str(key: str):
    val = rds.get(key)
    if val is None:
        return None
    return val.decode() if isinstance(val, (bytes, bytearray)) else val


def _current_version() -> str:
    try:
        import tomllib

        with open("pyproject.toml", "rb") as fh:
            return tomllib.load(fh).get("project", {}).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def _is_patch_bump(current: str, target: str) -> bool:
    try:
        c, t = Version(current), Version(target)
    except Exception:
        return False
    if t <= c:
        return False
    return c.major == t.major and c.minor == t.minor


@celery.task
def check_for_updates():
    """Poll GitHub releases. Cache latest. Notify admins on new tag. Optionally auto-apply patch."""
    try:
        resp = requests.get(GITHUB_LATEST_URL, timeout=10)
        resp.raise_for_status()
        release = resp.json()
    except Exception as e:
        logger.warning(f"update check failed: {e}")
        return

    latest_tag = _strip_v(release.get("tag_name", ""))
    if not latest_tag:
        return

    rds.set(
        UPDATE_CACHE_KEY,
        json.dumps(
            {
                "latest": latest_tag,
                "release_notes_url": release.get("html_url"),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )

    current = _current_version()
    if latest_tag == current:
        return
    if _redis_get_str(UPDATE_NOTIFIED_KEY) == latest_tag:
        return

    auto_apply = bool(getattr(cfg, "AUTO_APPLY_PATCH_UPDATES", False))

    if auto_apply and _is_patch_bump(current, latest_tag):
        logger.info(f"auto-applying patch update {current} -> {latest_tag}")
        try:
            subprocess.run(
                ["sudo", "-n", "/usr/local/sbin/bayanat-start-update"],
                check=True,
                timeout=10,
            )
            rds.set(UPDATE_NOTIFIED_KEY, latest_tag)
            return
        except Exception as e:
            logger.warning(f"auto-apply failed, falling back to notification: {e}")

    Notification.create_for_admins(
        title=f"Update available: {latest_tag}",
        message=f"A new Bayanat release is available. {release.get('html_url', '')}",
        category=Constants.NotificationCategories.UPDATE.value,
    )
    rds.set(UPDATE_NOTIFIED_KEY, latest_tag)


@celery.task
def activity_cleanup_cron() -> None:
    """
    Periodic task to cleanup Activity Monitor logs.
    """
    expired_activities = Activity.query.filter(
        DateHelper.utcnow() - Activity.created_at > cfg.ACTIVITIES_RETENTION
    )
    logger.info("Cleaning up Activities...")
    deleted = expired_activities.delete(synchronize_session=False)
    if deleted:
        db.session.commit()
        logger.info(f"{deleted} expired activities deleted.")
    else:
        logger.info("No expired activities to delete.")


@celery.task
def session_cleanup():
    """
    Periodic task to cleanup old sessions.
    """
    if cfg.SESSION_RETENTION_PERIOD:
        session_retention_days = int(cfg.SESSION_RETENTION_PERIOD)
        if session_retention_days == 0:
            logger.info("Session cleanup is disabled.")
            return

        cutoff_date = DateHelper.utcnow() - timedelta(days=session_retention_days)
        expired_sessions = db.session.query(Session).filter(Session.created_at < cutoff_date)

        logger.info("Cleaning up expired sessions...")
        deleted = expired_sessions.delete(synchronize_session=False)
        if deleted:
            db.session.commit()
            logger.info(f"{deleted} expired sessions deleted.")
        else:
            logger.info("No expired sessions to delete.")


@celery.task
def daily_backup_cron():
    """
    Daily task to backup the database.
    """
    filename = f"bayanat-backup-{date.today().isoformat()}.tar"
    filepath = f"{cfg.BACKUPS_LOCAL_PATH}/{filename}"
    try:
        pg_dump(filepath)
    except Exception:
        logger.error("Error during daily backups", exc_info=True)
        return

    if cfg.BACKUPS_S3_BUCKET:
        if upload_to_s3(filepath):
            try:
                os.remove(filepath)
            except FileNotFoundError:
                logger.error(f"Backup file {filename} not found to delete.", exc_info=True)
            except OSError:
                logger.error(f"Unable to remove backup file {filename}.", exc_info=True)


@celery.task
def regenerate_locations() -> None:
    """
    Regenerate full locations for all entities.
    """
    try:
        rds.set(Location.CELERY_FLAG, 1)
        Location.regenerate_all_full_locations()
    finally:
        rds.delete(Location.CELERY_FLAG)


def reload_app():
    """Touch reload.ini to trigger uWSGI graceful reload.
    Returns True if uWSGI reload was triggered, False in dev mode.
    """
    import pathlib

    reload_file = pathlib.Path(__file__).resolve().parents[2] / "reload.ini"
    try:
        import uwsgi  # noqa: F401

        reload_file.touch()
        return True
    except ImportError:
        # Dev mode (flask run), no uWSGI available
        return False


def restart_celery():
    """Restart Celery worker via systemd. Requires sudoers entry.
    Silently skips in dev mode (no systemd).
    """
    import subprocess

    try:
        subprocess.Popen(
            ["sudo", "/usr/bin/systemctl", "restart", "bayanat-celery"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # Dev mode or no systemd
        pass
