# -*- coding: utf-8 -*-
from celery import chord, group

from enferno.admin.constants import Constants
from enferno.admin.models.Notification import Notification
from enferno.extensions import rds
from enferno.tasks import celery
from enferno.tasks.extraction import process_media_extraction_task
from enferno.user.models import User
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.ocr")

process_media_extraction = celery.task(process_media_extraction_task)


@celery.task(rate_limit="1200/m")
def ocr_single(
    media_id: int, user_id: int = None, language_hints: list = None, force: bool = False
) -> dict:
    """Process one media item with rate limiting. Removes itself from Redis tracking set on completion."""
    result = process_media_extraction_task(media_id, language_hints=language_hints, force=force)
    if user_id:
        rds.srem(f"ocr_processing:{user_id}", media_id)
    return result


@celery.task
def bulk_ocr_finalize(results: list, user_id: int = None) -> dict:
    """Callback after all ocr_single tasks complete. Notifies user with summary."""
    processed = sum(1 for r in results if r and r.get("success") and not r.get("skipped"))
    skipped = sum(1 for r in results if r and r.get("success") and r.get("skipped"))
    failed = len(results) - processed - skipped

    # Clear any remaining tracking keys
    if user_id:
        rds.delete(f"ocr_processing:{user_id}")

    logger.info(f"Bulk OCR complete. Processed: {processed}, Skipped: {skipped}, Failed: {failed}")

    if user_id:
        user = User.query.get(user_id)
        if user:
            Notification.send_notification_for_event(
                Constants.NotificationEvent.BULK_OPERATION_STATUS,
                user,
                "Bulk OCR Complete",
                f"{processed} processed, {skipped} skipped, {failed} failed.",
            )

    return {"processed": processed, "skipped": skipped, "failed": failed}


def bulk_ocr_process(
    media_ids: list, user_id: int = None, language_hints: list = None, force: bool = False
):
    """Dispatch OCR tasks as a parallel group with a finalize callback."""
    tasks = group(
        ocr_single.s(mid, user_id=user_id, language_hints=language_hints, force=force)
        for mid in media_ids
    )
    callback = bulk_ocr_finalize.s(user_id=user_id)
    chord(tasks)(callback)
