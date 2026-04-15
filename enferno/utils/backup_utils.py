import os

from subprocess import check_output
import boto3

from enferno.settings import Config
from enferno.utils.logging_utils import get_logger

logger = get_logger()

# Upper bound for pg_dump so a hung network / auth / lock can't block the
# backup job forever. One hour is generous for large DBs but still bounded.
PG_DUMP_TIMEOUT = 3600


def pg_dump(filepath):
    db = Config.get("POSTGRES_DB")
    host = Config.get("POSTGRES_HOST")
    password = Config.get("POSTGRES_PASSWORD")

    # localhost with no password set
    if host == "localhost" and not password:
        cmd = ["pg_dump", "-Fc", db, "-f", filepath]
        return check_output(cmd, timeout=PG_DUMP_TIMEOUT)

    cmd = [
        "pg_dump",
        "-Fc",
        db,
        "-h",
        host,
        "-U",
        Config.get("POSTGRES_USER"),
        "-f",
        filepath,
    ]
    env = {**os.environ}
    if password:
        env["PGPASSWORD"] = password
    return check_output(cmd, env=env, timeout=PG_DUMP_TIMEOUT)


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
