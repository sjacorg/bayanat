import os

from subprocess import check_output
import boto3
from flask import current_app

from enferno.settings import Config
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def pg_dump(filepath):
    # localhost with no password set
    if Config.get("POSTGRES_HOST") == "localhost" and not Config.get("POSTGRES_PASSWORD"):
        cmd = ["pg_dump", "-Fc", f"{Config.get("POSTGRES_DB")}", "-f", f"{filepath}"]
        return check_output(cmd)
    else:
        cmd = [
            "pg_dump",
            "-Fc",
            f"{Config.get("POSTGRES_DB")}",
            "-h",
            f"{Config.get("POSTGRES_HOST")}",
            "-U",
            f"{Config.get("POSTGRES_USER")}" "-f",
            f"{filepath}",
        ]
        return check_output(cmd, env={"PGPASSWORD": Config.get("POSTGRES_PASSWORD")})


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
