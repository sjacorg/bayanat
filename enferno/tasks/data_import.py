# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Any, Literal, Optional

from celery import chord, group
from werkzeug.utils import safe_join

import enferno.utils.typing as t
from enferno.admin.constants import Constants
from enferno.admin.models.Notification import Notification
from enferno.data_import.models import DataImport
from enferno.data_import.utils.media_import import MediaImport
from enferno.data_import.utils.sheet_import import SheetImport
from enferno.tasks import celery, cfg
from enferno.user.models import User
from enferno.utils.data_helpers import get_file_hash, media_check_duplicates
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.data_import")


@celery.task(rate_limit=10)
def etl_process_file(
    batch_id: t.id, file: str, meta: Any, user_id: t.id, data_import_id: t.id
) -> Optional[Literal["done"]]:
    """Process individual file for import. Part of coordinated batch operation."""
    try:
        di = MediaImport(batch_id, meta, user_id=user_id, data_import_id=data_import_id)
        di.process(file)
        return "done"
    except Exception as e:
        log = DataImport.query.get(data_import_id)
        log.fail(e)
        raise  # Re-raise for chord coordination


@celery.task
def batch_complete_notification(results: list, batch_id: str, user_id: int) -> None:
    """Callback executed when all files in a batch are processed."""
    from enferno.data_import.models import DataImport

    batch_imports = DataImport.query.filter_by(batch_id=batch_id).all()
    successful = [imp for imp in batch_imports if imp.status == "Ready"]
    failed = [imp for imp in batch_imports if imp.status == "Failed"]

    user = User.query.get(user_id)
    if not user:
        logger.error(f"User {user_id} not found for batch completion notification")
        return

    if len(failed) == 0:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.BATCH_STATUS,
            user,
            "Batch Import Complete",
            f"Batch {batch_id} completed successfully. All {len(successful)} files processed.",
        )
    else:
        Notification.send_notification_for_event(
            Constants.NotificationEvent.BATCH_STATUS,
            user,
            "Batch Import Completed with Errors",
            f"Batch {batch_id} completed. {len(successful)} succeeded, {len(failed)} failed.",
        )

    logger.info(f"Batch {batch_id} complete: {len(successful)} success, {len(failed)} failed")


@celery.task
def process_files(files: list, meta: dict, user_id: int, batch_id: str) -> None:
    """Process multiple files using Celery chord pattern for coordinated batch completion."""
    file_tasks = []

    for file in files:
        f = file.get("path") or file.get("filename")

        data_import = DataImport(
            user_id=user_id, table="bulletin", file=f, batch_id=batch_id, data=meta
        )

        if meta.get("mode") == 2:
            # Server-side import: copy files and generate hashes
            allowed_path = Path(cfg.ETL_ALLOWED_PATH)
            full_path = safe_join(allowed_path, f)
            data_import.file_hash = file["etag"] = get_file_hash(full_path)
            data_import.save()

            if media_check_duplicates(file.get("etag"), data_import.id):
                data_import.add_to_log(f"File already exists {f}.")
                data_import.fail()
                continue

            file["path"] = full_path

        data_import.add_to_log(f"Added file {file} to import queue.")

        file_tasks.append(etl_process_file.s(batch_id, file, meta, user_id, data_import.id))

    if not file_tasks:
        # Edge case: all files were duplicates or invalid
        Notification.send_notification_for_event(
            Constants.NotificationEvent.BATCH_STATUS,
            User.query.get(user_id),
            "Batch Import Complete",
            f"Batch {batch_id} had no valid files to process.",
        )
        return

    # Execute all file tasks in parallel, with single callback when complete
    chord(group(file_tasks), batch_complete_notification.s(batch_id, user_id)).apply_async()


@celery.task
def process_row(
    filepath: str,
    sheet: Any,
    row_id: Any,
    data_import_id: t.id,
    map: Any,
    batch_id: Any,
    vmap: Optional[Any],
    actor_config: Any,
    lang: str,
    roles: list = [],
) -> None:
    """
    Process row task.

    Args:
        - filepath: File path.
        - sheet: Sheet.
        - row_id: Row ID.
        - data_import_id: Data Import ID.
        - map: Map.
        - batch_id: Batch ID.
        - vmap: Vmap.
        - actor_config: Actor config.
        - lang: Language.
        - roles: Roles.

    Returns:
        None
    """
    si = SheetImport(
        filepath,
        sheet,
        row_id,
        data_import_id,
        map,
        batch_id,
        vmap,
        roles,
        config=actor_config,
        lang=lang,
    )
    si.import_row()
