# -*- coding: utf-8 -*-
from enferno.extensions import rds
from enferno.tasks import celery
from enferno.tasks.extraction import process_media_extraction_task
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.ocr")


@celery.task(rate_limit="1200/m")
def ocr_single(
    media_id: int, user_id: int = None, language_hints: list = None, force: bool = False
) -> dict:
    """Process one media item with rate limiting. Removes itself from Redis tracking set on completion."""
    result = process_media_extraction_task(media_id, language_hints=language_hints, force=force)
    if user_id:
        rds.srem(f"ocr_processing:{user_id}", media_id)
    return result


def bulk_ocr_process(
    media_ids: list, user_id: int = None, language_hints: list = None, force: bool = False
):
    """Dispatch independent OCR tasks. Each task is fire-and-forget with rate limiting."""
    for mid in media_ids:
        ocr_single.delay(mid, user_id=user_id, language_hints=language_hints, force=force)
