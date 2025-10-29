import os

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
