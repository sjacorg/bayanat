# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta, date

from enferno.admin.models import Activity, Location
from enferno.extensions import db, rds
from enferno.user.models import Session
from enferno.utils.backup_utils import pg_dump, upload_to_s3
from enferno.utils.logging_utils import get_logger

from enferno.tasks import celery, cfg

logger = get_logger("celery.tasks.maintenance")


@celery.task
def activity_cleanup_cron() -> None:
    """
    Periodic task to cleanup Activity Monitor logs.
    """
    expired_activities = Activity.query.filter(
        datetime.utcnow() - Activity.created_at > cfg.ACTIVITIES_RETENTION
    )
    logger.info(f"Cleaning up Activities...")
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

        cutoff_date = datetime.utcnow() - timedelta(days=session_retention_days)
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
    except:
        logger.error("Error during daily backups", exc_info=True)
        return

    if cfg.BACKUPS_S3_BUCKET:
        if upload_to_s3(filepath):
            try:
                os.remove(filepath)
            except FileNotFoundError:
                logger.error(f"Backup file {filename} not found to delete.", exc_info=True)
            except OSError as e:
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
    import os
    import signal

    os.kill(os.getppid(), signal.SIGHUP)


@celery.task
def reload_celery():
    reload_app()
