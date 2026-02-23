# -*- coding: utf-8 -*-
import os
from typing import Any, Generator

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from enferno.extensions import db
from enferno.utils.logging_utils import get_logger

# Simple test detection - use TestConfig if in test environment
if os.environ.get("BAYANAT_CONFIG_FILE") == "config.test.json":
    from enferno.settings import TestConfig

    cfg = TestConfig()
else:
    from enferno.settings import Config

    cfg = Config()

celery = Celery("tasks", broker=cfg.celery_broker_url)
# remove deprecated warning
celery.conf.update({"accept_content": ["pickle", "json", "msgpack", "yaml"]})
celery.conf.update({"result_backend": os.environ.get("CELERY_RESULT_BACKEND", cfg.result_backend)})
celery.conf.update(
    {
        "SQLALCHEMY_DATABASE_URI": os.environ.get(
            "SQLALCHEMY_DATABASE_URI", cfg.SQLALCHEMY_DATABASE_URI
        )
    }
)
celery.conf.update({"SECRET_KEY": os.environ.get("SECRET_KEY", cfg.SECRET_KEY)})
celery.conf.broker_connection_retry_on_startup = True
celery.conf.add_defaults(cfg)

logger = get_logger("celery.tasks")

# Global variable to store the Flask app instance
_flask_app = None


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize the Flask app when the worker process starts."""
    global _flask_app
    if _flask_app is None:
        from enferno.app import create_app

        _flask_app = create_app(cfg)
        logger.info("Flask app initialized for worker process")


# Class to run tasks within application's context
class ContextTask(celery.Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        global _flask_app
        if _flask_app is None:
            # Lazy load the app if it hasn't been initialized yet
            from enferno.app import create_app

            _flask_app = create_app(cfg)
            logger.info("Flask app lazy-loaded in task context")

        with _flask_app.app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


celery.Task = ContextTask

# splitting db operations for performance
BULK_CHUNK_SIZE = 250


def chunk_list(lst: list, n: int) -> Generator[list, Any, None]:
    """
    Yield successive n-sized chunks from lst.

    Args:
        - lst: List to be chunked.
        - n: Size of each chunk.

    Yields:
        - Generator: n-sized chunks of lst.
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


# --- Periodic task setup ---


@celery.on_after_configure.connect
def setup_periodic_tasks(sender: Any, **kwargs: dict[str, Any]) -> None:
    """
    Setup periodic tasks.

    Args:
        - sender: Sender.
        - **kwargs: Keyword arguments.

    Returns:
        None
    """
    from enferno.tasks.deduplication import dedup_cron
    from enferno.tasks.exports import export_cleanup_cron
    from enferno.tasks.maintenance import activity_cleanup_cron, daily_backup_cron, session_cleanup

    # Deduplication periodic task
    if cfg.DEDUP_TOOL == True:
        seconds = int(os.environ.get("DEDUP_INTERVAL", cfg.DEDUP_INTERVAL))
        sender.add_periodic_task(seconds, dedup_cron.s(), name="Deduplication Cron")
        logger.info("Deduplication periodic task is set up.")
    # Export expiry periodic task
    if "export" in db.metadata.tables.keys():
        sender.add_periodic_task(300, export_cleanup_cron.s(), name="Exports Cleanup Cron")
        logger.info("Export cleanup periodic task is set up.")

    # activity peroidic task every 24 hours
    sender.add_periodic_task(24 * 60 * 60, activity_cleanup_cron.s(), name="Activity Cleanup Cron")
    logger.info("Activity cleanup periodic task is set up.")

    # Backups periodic task
    if cfg.BACKUPS:
        every_x_day = f"*/{cfg.BACKUP_INTERVAL}"
        sender.add_periodic_task(
            crontab(minute=0, hour=3, day_of_month=every_x_day),
            daily_backup_cron.s(),
            name="Backups Cron",
        )
        logger.info(
            f"Backup periodic task is set up. Backups will run at 3:00 every {cfg.BACKUP_INTERVAL} day(s)."
        )

    # session cleanup task
    sender.add_periodic_task(24 * 60 * 60, session_cleanup.s(), name="Session Cleanup Cron")


# --- Import submodules so Celery discovers all tasks ---
from enferno.tasks.bulk_ops import (
    bulk_update_bulletins,
    bulk_update_actors,
    bulk_update_incidents,
)  # noqa: E402, F401
from enferno.tasks.notifications import send_email_notification  # noqa: E402, F401
from enferno.tasks.data_import import (
    etl_process_file,
    batch_complete_notification,
    process_files,
    process_row,
)  # noqa: E402, F401
from enferno.tasks.exports import (
    generate_export,
    export_cleanup_cron,
    generate_pdf_files,
    generate_json_file,
    generate_csv_file,
    generate_export_media,
    generate_export_zip,
)  # noqa: E402, F401
from enferno.tasks.deduplication import (
    start_dedup,
    process_dedup,
    dedup_cron,
    update_stats,
)  # noqa: E402, F401
from enferno.tasks.graph import generate_graph  # noqa: E402, F401
from enferno.tasks.maintenance import (
    activity_cleanup_cron,
    session_cleanup,
    daily_backup_cron,
    regenerate_locations,
    reload_app,
    reload_celery,
)  # noqa: E402, F401
from enferno.tasks.media_download import download_media_from_web  # noqa: E402, F401
from enferno.tasks.ml import load_whisper_model, load_whisper_model_on_startup  # noqa: E402, F401
from enferno.tasks.ocr import (
    process_media_extraction,
    ocr_single,
    bulk_ocr_finalize,
    bulk_ocr_process,
)  # noqa: E402, F401
