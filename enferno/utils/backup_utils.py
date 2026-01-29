import os
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import check_output

import boto3
from flask import current_app

from enferno.settings import Config
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def pg_dump(filepath):
    """Create a PostgreSQL dump using connection info from database URI."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri:
        raise RuntimeError("No database URI configured")

    cmd = ["pg_dump", "-Fc", "-f", filepath, f"--dbname={db_uri}"]
    return check_output(cmd)


def upload_to_s3(filepath):
    filename = os.path.basename(filepath)
    try:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=Config.get("BACKUPS_AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=Config.get("BACKUPS_AWS_SECRET_ACCESS_KEY"),
            region_name=Config.get("BACKUPS_AWS_REGION"),
        )
        s3.Bucket(Config.get("BACKUPS_S3_BUCKET")).upload_file(filepath, filename)
        return True
    except Exception:
        logger.error("Error uploading backup file to S3", exc_info=True)
        return False


def cleanup_old_backups(backup_dir: str, retention_days: int) -> int:
    """Remove backup files older than retention_days. Returns count deleted."""
    if retention_days <= 0:
        return 0

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    backup_path = Path(backup_dir)

    if not backup_path.exists():
        return 0

    for f in backup_path.glob("bayanat-backup-*.tar"):
        try:
            date_str = f.stem.replace("bayanat-backup-", "")
            if datetime.strptime(date_str, "%Y-%m-%d") < cutoff_date:
                f.unlink()
                deleted += 1
                logger.info(f"Deleted old backup: {f.name}")
        except (ValueError, OSError) as e:
            logger.warning(f"Could not process {f}: {e}")

    return deleted
