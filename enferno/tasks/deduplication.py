# -*- coding: utf-8 -*-
from sqlalchemy.sql.expression import func

from enferno.deduplication.models import DedupRelation
from enferno.extensions import rds
from enferno.utils.logging_utils import get_logger

from enferno.tasks import celery, cfg

logger = get_logger("celery.tasks.deduplication")


def update_stats() -> None:
    """Send a message to update the stats on the UI."""
    rds.publish("dedprocess", 1)


@celery.task
def process_dedup(id, user_id) -> None:
    """
    Process deduplication task.

    Args:
        - id: Deduplication ID.
        - user_id: User ID.

    Returns:
        None
    """
    d = DedupRelation.query.get(id)
    if d:
        d.process(user_id)
        # detect final task and send a refresh message
        if rds.scard("dedq") == 0:
            rds.set("dedup", 2)


@celery.task
def start_dedup(user_id) -> None:
    """
    Initiates the Deduplication process and queue unprocessed items.
    """
    print("Queuing unprocessed matches for deduplication...")
    items = DedupRelation.query.filter_by(status=0).order_by(func.random())
    for item in items:
        # add all item ids to redis with current user id
        rds.sadd("dedq", f"{item.id}|{user_id}")
    # activate redis flag to process data
    rds.set("dedup", 1)
    print("Starting Deduplication process...")


@celery.task
def dedup_cron() -> None:
    """Deduplication cron task."""
    # shut down processing when we hit 0 items in the queue or when we turn off the processing
    if rds.get("dedup") != b"1" or rds.scard("dedq") == 0:
        rds.set("dedup", 0)
        # Pause processing / do nothing
        return

    # clear current processing
    rds.delete("dedup_processing")
    data = []
    items = rds.spop("dedq", cfg.DEDUP_BATCH_SIZE)
    for item in items:
        data = item.decode().split("|")
        process_dedup.delay(data[0], data[1])

    update_stats()
