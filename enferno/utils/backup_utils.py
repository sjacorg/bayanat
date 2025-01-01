import os

from subprocess import check_output
import boto3
from flask import current_app

from enferno.settings import Config as cfg
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def pg_dump(filepath):
    # localhost with no password set
    if cfg.POSTGRES_HOST == "localhost" and not cfg.POSTGRES_PASSWORD:
        cmd = ["pg_dump", "-Fc", f"{cfg.POSTGRES_DB}", "-f", f"{filepath}"]
        return check_output(cmd)
    else:
        cmd = [
            "pg_dump",
            "-Fc",
            f"{cfg.POSTGRES_DB}",
            "-h",
            f"{cfg.POSTGRES_HOST}",
            "-U",
            f"{cfg.POSTGRES_USER}" "-f",
            f"{filepath}",
        ]
        return check_output(cmd, env={"PGPASSWORD": cfg.POSTGRES_PASSWORD})


def upload_to_s3(filepath):
    filename = os.path.basename(filepath)
    try:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=cfg.BACKUPS_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.BACKUPS_AWS_SECRET_ACCESS_KEY,
            region_name=cfg.BACKUPS_AWS_REGION,
        )
        s3.Bucket(cfg.BACKUPS_S3_BUCKET).upload_file(filepath, filename)
        return True
    except Exception:
        logger.error("Error uploading backup file to S3", exc_info=True)
        return False
