# -*- coding: utf-8 -*-
import hashlib
import json
import os
import shutil
import tempfile
import time
from collections import namedtuple
from pathlib import Path

from typing import Any, Generator, Literal, Optional
from datetime import datetime, timedelta, date

import boto3
import pandas as pd
from celery import Celery, chain
from celery.schedules import crontab
from sqlalchemy import and_
from sqlalchemy.sql.expression import func
import yt_dlp
from sqlalchemy.orm.attributes import flag_modified
from yt_dlp.utils import DownloadError

from enferno.admin.models import (
    Bulletin,
    Actor,
    Incident,
    BulletinHistory,
    Activity,
    ActorHistory,
    IncidentHistory,
    Location,
    Media,
)
from enferno.deduplication.models import DedupRelation
from enferno.export.models import Export
from enferno.extensions import db, rds
from enferno.settings import Config as cfg
from enferno.user.models import Role, User, Session
from enferno.utils.csv_utils import convert_list_attributes
from enferno.data_import.models import DataImport
from enferno.data_import.utils.media_import import MediaImport
from enferno.data_import.utils.sheet_import import SheetImport
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.logging_utils import get_logger
from enferno.utils.pdf_utils import PDFUtil
from enferno.utils.search_utils import SearchUtils
from enferno.utils.graph_utils import GraphUtils
import enferno.utils.typing as t

from enferno.utils.backup_utils import pg_dump, upload_to_s3

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


# Class to run tasks within application's context
class ContextTask(celery.Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        from enferno.app import create_app

        with create_app(cfg).app_context():
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


@celery.task
def bulk_update_bulletins(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update bulletins task.

    Args:
        - ids: List of bulletin ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Bulletin bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    for group in chunks:
        # Fetch bulletins
        bulletins = Bulletin.query.filter(Bulletin.id.in_(group))
        for bulletin in bulletins:
            # check user can access each bulletin
            if not user.can_access(bulletin):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            # Assigned user
            assigned_to_id = bulk.get("assigned_to_id")
            clear_assignee = bulk.get("assigneeClear")
            if clear_assignee:
                bulletin.assigned_to_id = None
            elif assigned_to_id:
                bulletin.assigned_to_id = assigned_to_id
                if not status:
                    bulletin.status = "Assigned"

            # FPR user
            first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
            clear_reviewer = bulk.get("reviewerClear")
            if clear_reviewer:
                bulletin.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                bulletin.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    bulletin.status = "Peer Review Assigned"

            if status:
                bulletin.status = status

            # Ref
            tags = bulk.get("tags")
            if tags:
                if bulk.get("tagsReplace") or not bulletin.tags:
                    bulletin.tags = tags
                else:
                    # merge refs / remove dups
                    bulletin.tags = list(set(bulletin.tags + tags))

            # Comment (required)
            bulletin.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = roles
                else:
                    # clear bulletin roles
                    bulletin.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    bulletin.roles = list(set(bulletin.roles + roles))

            # add only to session
            db.session.add(bulletin)

        revmaps = []
        bulletins = Bulletin.query.filter(Bulletin.id.in_(group)).all()
        for bulletin in bulletins:
            # this commits automatically
            tmp = {"bulletin_id": bulletin.id, "user_id": cur_user.id, "data": bulletin.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(BulletinHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in bulletins]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "bulletin"
        )
        # perhaps allow a little time out
        time.sleep(0.1)

    logger.info(f"Bulletin bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")


@celery.task
def bulk_update_actors(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update actors task.

    Args:
        - ids: List of actor ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Actor bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)
    for group in chunks:
        # Fetch bulletins
        actors = Actor.query.filter(Actor.id.in_(group))
        for actor in actors:
            # check user can access each actor
            if not user.can_access(actor):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            # Assigned user
            assigned_to_id = bulk.get("assigned_to_id")
            clear_assignee = bulk.get("assigneeClear")
            if clear_assignee:
                actor.assigned_to_id = None
            elif assigned_to_id:
                actor.assigned_to_id = assigned_to_id
                if not status:
                    actor.status = "Assigned"

            # FPR user
            first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
            clear_reviewer = bulk.get("reviewerClear")
            if clear_reviewer:
                actor.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                actor.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    actor.status = "Peer Review Assigned"

            if status:
                actor.status = status

            # Tags
            tags = bulk.get("tags")
            if tags:
                if bulk.get("tagsReplace") or not actor.tags:
                    actor.tags = tags
                else:
                    # merge tags / remove dups
                    actor.tags = list(set(actor.tags + tags))

            # Comment (required)
            actor.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    actor.roles = roles
                else:
                    # clear actor roles
                    actor.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the actor
                    actor.roles = list(set(actor.roles + roles))

            # add only to session
            db.session.add(actor)

        revmaps = []
        actors = Actor.query.filter(Actor.id.in_(group)).all()
        for actor in actors:
            # this commits automatically
            tmp = {"actor_id": actor.id, "user_id": cur_user.id, "data": actor.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(ActorHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in actors]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "actor"
        )
        # perhaps allow a little time out
        time.sleep(0.25)

    logger.info(f"Actors bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")


@celery.task
def bulk_update_incidents(ids: list, bulk: dict, cur_user_id: t.id) -> None:
    """
    Bulk update incidents task.

    Args:
        - ids: List of incident ids to update.
        - bulk: Bulk update data.
        - cur_user_id: ID of the user performing the bulk update.

    Returns:
        None
    """
    logger.info(f"Processing Incident bulk-update... User ID: {cur_user_id} Total: {len(ids)}")
    # build mappings
    u = {"id": cur_user_id}
    cur_user = namedtuple("cur_user", u.keys())(*u.values())
    user = User.query.get(cur_user_id)
    chunks = chunk_list(ids, BULK_CHUNK_SIZE)

    # for ops on related items
    assign_related = bulk.get("assignRelated")
    restrict_related = bulk.get("restrictRelated")
    actors = []
    bulletins = []

    for group in chunks:
        # Fetch bulletins
        incidents = Incident.query.filter(Incident.id.in_(group))
        for incident in incidents:
            # check if user can access incident
            if not user.can_access(incident):
                # Log?
                continue

            # get Status initially
            status = bulk.get("status")

            # Assigned user
            assigned_to_id = bulk.get("assigned_to_id")
            clear_assignee = bulk.get("assigneeClear")
            if clear_assignee:
                incident.assigned_to_id = None
            elif assigned_to_id:
                incident.assigned_to_id = assigned_to_id
                if not status:
                    incident.status = "Assigned"

            # FPR user
            first_peer_reviewer_id = bulk.get("first_peer_reviewer_id")
            clear_reviewer = bulk.get("reviewerClear")
            if clear_reviewer:
                incident.first_peer_reviewer_id = None
            elif first_peer_reviewer_id:
                incident.first_peer_reviewer_id = first_peer_reviewer_id
                if not status:
                    incident.status = "Peer Review Assigned"

            if status:
                incident.status = status

            # Comment (required)
            incident.comments = bulk.get("comments", "")

            # Access Roles
            roles = bulk.get("roles")
            replace_roles = bulk.get("rolesReplace")
            if replace_roles:
                if roles:
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the bulletin
                    incident.roles = roles
                else:
                    # clear incident roles
                    incident.roles = []
            else:
                if roles:
                    # merge roles
                    role_ids = list(map(lambda x: x.get("id"), roles))
                    # get actual roles objects
                    roles = Role.query.filter(Role.id.in_(role_ids)).all()
                    # assign directly to the incident
                    incident.roles = list(set(incident.roles + roles))

            if assign_related or restrict_related:
                rel_actors = [itoa.actor_id for itoa in incident.related_actors]
                actors.extend(rel_actors)

                rel_bulletins = [itoa.bulletin_id for itoa in incident.related_bulletins]
                bulletins.extend(rel_bulletins)

            # add only to session
            db.session.add(incident)

        revmaps = []
        incidents = Incident.query.filter(Incident.id.in_(group)).all()
        for incident in incidents:
            # this commits automatically
            tmp = {"incident_id": incident.id, "user_id": cur_user.id, "data": incident.to_dict()}
            revmaps.append(tmp)
        db.session.bulk_insert_mappings(IncidentHistory, revmaps)

        # commit session when a batch of items and revisions are added
        db.session.commit()

        # Record Activity
        updated = [b.to_mini() for b in incidents]
        Activity.create(
            cur_user, Activity.ACTION_BULK_UPDATE, Activity.STATUS_SUCCESS, updated, "incident"
        )

        # restrict or assign related items
        if assign_related or restrict_related:
            # remove status
            bulk.pop("status", None)

            # not assigning related items
            if not assign_related:
                bulk.pop("assigned_to_id", None)
                bulk.pop("first_peer_reviewer_id", None)

            # not restricting related items
            if not restrict_related:
                bulk.pop("roles", None)
                bulk.pop("rolesReplace", None)

            # carry out bulk ops on related items
            if len(actors):
                bulk_update_actors(actors, bulk, cur_user_id)
            if len(bulletins):
                bulk_update_bulletins(bulletins, bulk, cur_user_id)

        # perhaps allow a little time out
        time.sleep(0.25)

    logger.info(f"Incidents bulk-update successful. User ID: {cur_user_id} Total: {len(ids)}")


@celery.task(rate_limit=10)
def etl_process_file(
    batch_id: t.id, file: str, meta: Any, user_id: t.id, data_import_id: t.id
) -> Optional[Literal["done"]]:
    """ETL process file task."""
    try:
        di = MediaImport(batch_id, meta, user_id=user_id, data_import_id=data_import_id)
        di.process(file)
        return "done"
    except Exception as e:
        log = DataImport.query.get(data_import_id)
        log.fail(e)


# this will publish a message to redis and will be captured by the front-end client
def update_stats() -> None:
    """Send a message to update the stats on the UI."""
    # send any message to refresh the UI
    # this will run only if the process is on
    rds.publish("dedprocess", 1)


@celery.task
def process_dedup(id: t.id, user_id: t.id) -> None:
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


@celery.task
def session_cleanup():
    """
    Periodic task to cleanup old sessions.
    """
    if cfg.SESSION_RETENTION_PERIOD:
        session_retention_days = int(cfg.SESSION_RETENTION_PERIOD)
        if session_retention_days == 0:
            logger.info("Session cleanup is disabled.")
            return

        cutoff_date = datetime.utcnow() - timedelta(days=session_retention_days)
        expired_sessions = db.session.query(Session).filter(Session.created_at < cutoff_date)

        logger.info("Cleaning up expired sessions...")
        deleted = expired_sessions.delete(synchronize_session=False)
        if deleted:
            db.session.commit()
            logger.info(f"{deleted} expired sessions deleted.")
        else:
            logger.info("No expired sessions to delete.")


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


def reload_app():
    import os
    import signal

    os.kill(os.getppid(), signal.SIGHUP)


@celery.task
def reload_celery():
    reload_app()


# ---- Export tasks ----
def generate_export(export_id: t.id) -> None:
    """
    Main Export generator task.

    Args:
        - export_id: Export ID.

    Raises:
        - NotImplementedError: If file format is not supported.

    Returns:
        - chained tasks' result.
    """
    export_request = Export.query.get(export_id)

    if export_request.file_format == "json":
        return chain(
            generate_json_file.s([export_id]), generate_export_media.s(), generate_export_zip.s()
        )()

    elif export_request.file_format == "pdf":
        return chain(
            generate_pdf_files.s([export_id]), generate_export_media.s(), generate_export_zip.s()
        )()
    elif export_request.file_format == "csv":
        return chain(
            generate_csv_file.s([export_id]), generate_export_media.s(), generate_export_zip.s()
        )()

    elif export_request.file_format == "csv":
        raise NotImplementedError


def clear_failed_export(export_request: Export) -> None:
    """
    Clear failed export task.

    Args:
        - export_request: Export request.

    Returns:
        None
    """
    shutil.rmtree(f"{Export.export_dir}/{export_request.file_id}")
    export_request.status = "Failed"
    export_request.file_id = None
    export_request.save()


@celery.task
def generate_pdf_files(export_id: t.id) -> t.id | Literal[False]:
    """
    PDF export generator task.

    Args:
        - export_id: Export ID.

    Returns:
        - export_id if successful, False otherwise.
    """
    export_request = Export.query.get(export_id)

    chunks = chunk_list(export_request.items, BULK_CHUNK_SIZE)
    dir_id = Export.generate_export_dir()
    try:
        for group in chunks:
            if export_request.table == "bulletin":
                for bulletin in Bulletin.query.filter(Bulletin.id.in_(group)):
                    pdf = PDFUtil(bulletin)
                    pdf.generate_pdf(f"{Export.export_dir}/{dir_id}/{pdf.filename}")

            elif export_request.table == "actor":
                for actor in Actor.query.filter(Actor.id.in_(group)):
                    pdf = PDFUtil(actor)
                    pdf.generate_pdf(f"{Export.export_dir}/{dir_id}/{pdf.filename}")

            elif export_request.table == "incident":
                for incident in Incident.query.filter(Incident.id.in_(group)):
                    pdf = PDFUtil(incident)
                    pdf.generate_pdf(f"{Export.export_dir}/{dir_id}/{pdf.filename}")

            time.sleep(0.2)

        export_request.file_id = dir_id
        export_request.save()
        logger.info(f"Export #{export_request.id} PDF file generated successfully.")
        # pass the ids to the next celery task
        return export_id
    except Exception as e:
        logger.error(f"Error writing PDF file for Export #{export_request.id}", exc_info=True)
        clear_failed_export(export_request)
        return False  # to stop chain


@celery.task
def generate_json_file(export_id: t.id) -> t.id | Literal[False]:
    """
    JSON export generator task.

    Args:
        - export_id: Export ID.

    Returns:
        - export_id if successful, False otherwise.
    """
    export_request = Export.query.get(export_id)
    chunks = chunk_list(export_request.items, BULK_CHUNK_SIZE)
    file_path, dir_id = Export.generate_export_file()
    export_type = export_request.table
    try:
        with open(f"{file_path}.json", "a") as file:
            file.write("{ \n")
            file.write(f'"{export_type}s": [ \n')
            for group in chunks:
                if export_type == "bulletin":
                    batch = ",".join(
                        bulletin.to_json()
                        for bulletin in Bulletin.query.filter(Bulletin.id.in_(group))
                    )
                    file.write(f"{batch}\n")
                elif export_type == "actor":
                    batch = ",".join(
                        actor.to_json() for actor in Actor.query.filter(Actor.id.in_(group))
                    )
                    file.write(f"{batch}\n")
                elif export_type == "incident":
                    batch = ",".join(
                        incident.to_json()
                        for incident in Incident.query.filter(Incident.id.in_(group))
                    )
                    file.write(f"{batch}\n")
                # less db overhead
                time.sleep(0.2)
            file.write("] \n }")
        export_request.file_id = dir_id
        export_request.save()
        logger.info(f"Export #{export_request.id} JSON file generated successfully.")
        # pass the ids to the next celery task
        return export_id
    except Exception as e:
        logger.error(f"Error writing JSON file for Export #{export_request.id}", exc_info=True)
        clear_failed_export(export_request)
        return False  # to stop chain


@celery.task
def generate_csv_file(export_id: t.id) -> t.id | Literal[False]:
    """
    CSV export generator task.

    Args:
        - export_id: Export ID.

    Returns:
        - export_id if successful, False otherwise.
    """
    export_request = Export.query.get(export_id)
    file_path, dir_id = Export.generate_export_file()
    export_type = export_request.table

    try:
        csv_df = pd.DataFrame()
        for id in export_request.items:
            if export_type == "bulletin":
                bulletin = Bulletin.query.get(id)
                # adjust list attributes to normal dicts
                adjusted = convert_list_attributes(bulletin.to_csv_dict())
                # normalize
                df = pd.json_normalize(adjusted)
                if csv_df.empty:
                    csv_df = df
                else:
                    csv_df = pd.merge(csv_df, df, how="outer")

            elif export_type == "actor":
                actor = Actor.query.get(id)
                # adjust list attributes to normal dicts
                actor_dict = convert_list_attributes(actor.to_csv_dict())

                # If there are profiles, merge them into the actor dict before normalizing
                if actor.actor_profiles:
                    flattened = actor.flatten_profiles()
                    # Merge the first profile data into actor dict
                    actor_dict.update(flattened if flattened else {})

                # normalize the combined dict
                df = pd.json_normalize(actor_dict)
                if csv_df.empty:
                    csv_df = df
                else:
                    csv_df = pd.concat([csv_df, df], ignore_index=True)

        csv_df.to_csv(f"{file_path}.csv")

        export_request.file_id = dir_id
        export_request.save()
        logger.info(f"Export #{export_request.id} CSV file generated successfully.")
        # pass the ids to the next celery task
        return export_id
    except Exception as e:
        logger.error(f"Error writing CSV file for Export #{export_request.id}", exc_info=True)
        clear_failed_export(export_request)
        return False  # to stop chain


@celery.task
def generate_export_media(previous_result: int) -> Optional[t.id]:
    """
    Task to attach media files to export.

    Args:
        - previous_result: Previous result.

    Returns:
        - export_request.id if successful, None otherwise.
    """
    if previous_result == False:
        return False

    export_request = Export.query.get(previous_result)

    # check if we need to export media files
    if not export_request.include_media:
        return export_request.id

    export_type = export_request.table
    # get list of previous entity ids and export their medias
    # dynamic query based on table
    if export_type == "bulletin":
        items = Bulletin.query.filter(Bulletin.id.in_(export_request.items))
    elif export_type == "actor":
        items = Actor.query.filter(Actor.id.in_(export_request.items))
    elif export_type == "incident":
        # incidents has no media
        # UI switch disabled, but just in case...
        return

    for item in items:
        if item.medias:
            media = item.medias[0]
            target_file = f"{Export.export_dir}/{export_request.file_id}/{media.media_file}"

            if cfg.FILESYSTEM_LOCAL:
                # copy file (including metadata)
                shutil.copy2(f"{media.media_dir}/{media.media_file}", target_file)
            else:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                    region_name=cfg.AWS_REGION,
                )
                try:
                    s3.download_file(cfg.S3_BUCKET, media.media_file, target_file)
                except Exception as e:
                    logger.error(
                        f"Error downloading Export #{export_request.id} file from S3.",
                        exc_info=True,
                    )

        time.sleep(0.05)
    return export_request.id


@celery.task
def generate_export_zip(previous_result: t.id) -> Optional[Literal[False]]:
    """
    Final export task to compress export folder
    into a zip archive.

    Args:
        - previous_result: Previous result.

    Returns:
        - False if previous task failed, None otherwise.
    """
    if previous_result == False:
        return False

    export_request = Export.query.get(previous_result)
    logger.info(f"Generating Export #{export_request.id} ZIP archive")

    shutil.make_archive(
        f"{Export.export_dir}/{export_request.file_id}",
        "zip",
        f"{Export.export_dir}/{export_request.file_id}",
    )
    logger.info(f"Export #{export_request.id} Complete {export_request.file_id}.zip")

    # Remove export folder after completion
    shutil.rmtree(f"{Export.export_dir}/{export_request.file_id}")

    # update request state
    export_request.status = "Ready"
    export_request.save()


@celery.task
def export_cleanup_cron() -> None:
    """
    Periodic task to change status of
    expired Exports to 'Expired'.
    """
    expired_exports = Export.query.filter(
        and_(
            Export.expires_on < datetime.utcnow(),  # expiry time before now
            Export.status != "Expired",
        )
    ).all()  # status is not expired

    if expired_exports:
        for export_request in expired_exports:
            export_request.status = "Expired"
            if export_request.save():
                logger.info(f"Expired Export #{export_request.id}")
                try:
                    os.remove(f"{Export.export_dir}/{export_request.file_id}.zip")
                except FileNotFoundError:
                    logger.warning(f"Export #{export_request.id}'s files not found to delete.")
            else:
                logger.error(f"Error expiring Export #{export_request.id}")


type_map = {"bulletin": Bulletin, "actor": Actor, "incident": Incident}


@celery.task
def activity_cleanup_cron() -> None:
    """
    Periodic task to cleanup Activity Monitor logs.
    """
    expired_activities = Activity.query.filter(
        datetime.utcnow() - Activity.created_at > cfg.ACTIVITIES_RETENTION
    )
    logger.info(f"Cleaning up Activities...")
    deleted = expired_activities.delete(synchronize_session=False)
    if deleted:
        db.session.commit()
        logger.info(f"{deleted} expired activities deleted.")
    else:
        logger.info("No expired activities to delete.")


@celery.task
def daily_backup_cron():
    """
    Daily task to backup the database.
    """
    filename = f"bayanat-backup-{date.today().isoformat()}.tar"
    filepath = f"{cfg.BACKUPS_LOCAL_PATH}/{filename}"
    try:
        pg_dump(filepath)
    except:
        logger.error("Error during daily backups", exc_info=True)
        return

    if cfg.BACKUPS_S3_BUCKET:
        if upload_to_s3(filepath):
            try:
                os.remove(filepath)
            except FileNotFoundError:
                logger.error(f"Backup file {filename} not found to delete.", exc_info=True)
            except OSError as e:
                logger.error(f"Unable to remove backup file {filename}.", exc_info=True)


## Query graph visualization tasks


@celery.task
def generate_graph(query_json: Any, entity_type: str, user_id: t.id) -> Optional[str]:
    """
    Generate graph for a given query, with caching to avoid regenerating graphs for identical queries.
    Redis Hash Sample Structure for a user with `user_id`:
    Key: "user:123"
    Fields and Values:
        - "query_key": "most_recent_generate_query_key"
        - "graph_data": "most_recent_generated_graph_data"

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Graph data.
    """
    if not user_id:
        raise ValueError("User ID is required to generate graph")

    entity_type_lower = entity_type.lower()
    if entity_type_lower not in type_map:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    query_key = create_query_key(query_json, entity_type, user_id)

    # Redis hash key for the user
    user_hash_key = f"user:{user_id}"

    # Retrieve the current query key for the user
    existing_query_key = rds.hget(user_hash_key, "query_key")

    if existing_query_key and existing_query_key.decode() == query_key:
        # Return the existing graph data if query keys match
        existing_graph_data = rds.hget(user_hash_key, "graph_data")
        return existing_graph_data.decode()

    # Generate the graph if no cache hit
    graph_data = process_graph_generation(query_json, entity_type_lower, user_id, query_key)

    # Update the hash with the new query key and graph data
    rds.hset(user_hash_key, "query_key", query_key)
    rds.hset(user_hash_key, "graph_data", graph_data)

    return graph_data


def create_query_key(query_json: Any, entity_type: str, user_id: t.id) -> str:
    """
    Create a unique key based on the query JSON, entity type, and user ID.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Query key.
    """
    normalized_query = json.dumps(query_json, sort_keys=True)  # Ensures consistent key generation
    combined_string = f"{normalized_query}-{entity_type}-{user_id}"
    return hashlib.sha256(combined_string.encode()).hexdigest()


def process_graph_generation(
    query_json: Any, entity_type: str, user_id: t.id, query_key: str
) -> Optional[str]:
    """
    The core logic for graph generation, querying, and merging graphs.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - user_id: User ID.
        - query_key: Query key.

    Returns:
        - Graph data.
    """
    result_set = get_result_set(query_json, entity_type, type_map)
    rds.set(f"user{user_id}:graph:status", "pending")
    user = User.query.get(user_id)
    graph_utils = GraphUtils(user)
    graph = merge_graphs(result_set, entity_type, graph_utils)

    # Cache the generated graph with the unique query key
    rds.set(query_key, graph)
    rds.set(f"user{user_id}:graph:data", graph)
    rds.set(f"user{user_id}:graph:status", "done")
    return graph


def get_result_set(query_json: Any, entity_type: str, type_map: dict) -> Any:
    """
    Retrieve the result set based on the query JSON and entity type.

    Args:
        - query_json: Query JSON.
        - entity_type: Entity type.
        - type_map: Type map.

    Returns:
        - Result set.
    """
    search_util = SearchUtils(query_json, cls=entity_type)
    if entity_type == "incident":
        query = search_util.get_query()
    else:
        queries, operations = search_util.get_query()
        query = queries.pop(0)
    model = type_map[entity_type]
    return model.query.filter(*query)


def merge_graphs(result_set: Any, entity_type: str, graph_utils: GraphUtils) -> Optional[str]:
    """
    Merge graphs for each item in the result set.

    Args:
        - result_set: Result set.
        - entity_type: Entity type.
        - user_id: User ID.

    Returns:
        - Merged graph data.
    """
    graph = None
    for item in result_set.all():
        current_graph = graph_utils.get_graph_json(entity_type, item.id)
        graph = current_graph if graph is None else graph_utils.merge_graphs(graph, current_graph)
    return graph


@celery.task
def regenerate_locations() -> None:
    """
    Regenerate full locations for all entities.
    """
    try:
        rds.set(Location.CELERY_FLAG, 1)
        Location.regenerate_all_full_locations()
    finally:
        rds.delete(Location.CELERY_FLAG)


@celery.task
def download_media_from_web(url: str, user_id: int, batch_id: str, import_id: int) -> None:
    """Download and process media from web URL."""
    data_import = DataImport.query.get(import_id)
    if not data_import:
        logger.error(f"Invalid import_id: {import_id}")
        return

    try:
        # Download the media
        info, temp_file = _download_media(url)

        # Process the downloaded file
        final_filename = _process_downloaded_file(temp_file, info)

        # Update import record
        _update_import_record(data_import, final_filename, info)

        # Start ETL process
        _start_etl_process(final_filename, url, batch_id, user_id, import_id)

    except ValueError as e:
        # Handle specific error messages without traceback
        logger.error(f"Download failed: {str(e)}")
        data_import.add_to_log(f"Download failed: {str(e)}")
        data_import.fail()
    except Exception as e:
        # Handle other errors with traceback
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        data_import.add_to_log(f"Download failed: {str(e)}")
        data_import.fail()


def _get_ytdl_options(with_cookies: bool = False) -> dict:
    """Get yt-dlp options."""
    options = {
        "format": "mp4[height<=1080]/best[ext=mp4]/best",
        "outtmpl": str(Media.media_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "proxy": cfg.YTDLP_PROXY if cfg.YTDLP_PROXY else None,
    }

    if with_cookies and hasattr(cfg, "YTDLP_COOKIES"):
        cookie_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        cookie_file.write(cfg.YTDLP_COOKIES)
        cookie_file.close()
        options["cookiefile"] = cookie_file.name

    return options


def _download_media(url: str) -> tuple[dict, Path]:
    """Download media using yt-dlp."""
    try:
        # First attempt without cookies
        with yt_dlp.YoutubeDL(_get_ytdl_options()) as ydl:
            info = ydl.extract_info(url, download=True)
            temp_file = Path(ydl.prepare_filename(info))
            return info, temp_file

    except DownloadError as e:
        error_msg = str(e)
        if "Unsupported URL:" in error_msg:
            raise ValueError(
                f"This URL is not supported or contains no downloadable video content: {url}"
            )

        # Check for any authentication/login related errors
        if any(
            msg in error_msg.lower()
            for msg in [
                "age",
                "confirm your age",
                "inappropriate",
                "need to log in",
                "login",
                "cookies",
            ]
        ):
            logger.info("Authentication required, retrying with cookies...")
            try:
                # Second attempt with cookies
                with yt_dlp.YoutubeDL(_get_ytdl_options(with_cookies=True)) as ydl:
                    info = ydl.extract_info(url, download=True)
                    temp_file = Path(ydl.prepare_filename(info))
                    return info, temp_file
            except DownloadError:
                # Don't chain the exception, just raise a new ValueError
                raise ValueError(
                    "Failed to download content. Authentication cookies may be expired or invalid."
                )

        # For other download errors, wrap in ValueError without chaining
        raise ValueError(f"Download failed: {error_msg}")


def _process_downloaded_file(temp_file: Path, info: dict) -> str:
    """Process downloaded file and return final filename."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    final_filename = f"{info.get('id', 'video')}-{timestamp}.mp4"
    final_path = Media.media_dir / final_filename

    temp_file.rename(final_path)
    return final_filename


def _update_import_record(data_import: DataImport, filename: str, info: dict) -> None:
    """Update data import record."""
    file_path = Media.media_dir / filename
    file_hash = get_file_hash(file_path)

    data_import.file = filename
    data_import.file_hash = file_hash
    data_import.data["info"] = info
    flag_modified(data_import, "data")

    data_import.add_to_log(f"Downloaded file: {filename}")
    data_import.add_to_log(f"Format: mp4")
    data_import.add_to_log(f"Duration: {info.get('duration')}s")
    data_import.save()


def _start_etl_process(
    filename: str, url: str, batch_id: str, user_id: int, import_id: int
) -> None:
    """Start ETL process for downloaded file."""
    file_path = Media.media_dir / filename
    file_hash = get_file_hash(file_path)

    etl_process_file.delay(
        batch_id=batch_id,
        file={
            "name": filename,
            "filename": filename,
            "etag": file_hash,
            "path": str(file_path),
            "source_url": url,
        },
        meta={
            "mode": 3,
            "File:MIMEType": "video/mp4",
        },
        user_id=user_id,
        data_import_id=import_id,
    )
