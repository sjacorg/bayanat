import os

from subprocess import check_output
import boto3
from flask import current_app

from enferno.settings import Config
from enferno.utils.db_utils import parse_pg_uri
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def pg_dump(filepath):
    """Create a PostgreSQL dump using connection info from database URI."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri:
        raise RuntimeError("No database URI configured")

    db_info = parse_pg_uri(db_uri)

    # Build pg_dump command
    cmd = ["pg_dump", "-Fc", "-f", filepath]

    if db_info["username"]:
        cmd.extend(["-U", db_info["username"]])
    if db_info["host"]:
        cmd.extend(["-h", db_info["host"]])
    if db_info["port"]:
        cmd.extend(["-p", str(db_info["port"])])
    if db_info["dbname"]:
        cmd.append(db_info["dbname"])

    # Set password in environment if present
    env = os.environ.copy()
    if db_info["password"]:
        env["PGPASSWORD"] = db_info["password"]

    return check_output(cmd, env=env)


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
