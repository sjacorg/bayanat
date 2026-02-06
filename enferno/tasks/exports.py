# -*- coding: utf-8 -*-
import os
import shutil
import time
from datetime import datetime
from typing import Literal, Optional

import boto3
import pandas as pd
from celery import chain
from sqlalchemy import and_

from enferno.admin.models import Bulletin, Actor, Incident
from enferno.export.models import Export
from enferno.extensions import db
from enferno.utils.csv_utils import convert_list_attributes
from enferno.utils.logging_utils import get_logger
from enferno.utils.pdf_utils import PDFUtil
import enferno.utils.typing as t

from enferno.tasks import celery, cfg, chunk_list, BULK_CHUNK_SIZE

logger = get_logger("celery.tasks.exports")


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

    if not export_request:
        return False

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
                try:
                    shutil.copy2(f"{media.media_dir}/{media.media_file}", target_file)
                except Exception as e:
                    logger.error(
                        f"Error copying Export #{export_request.id} file from {media.media_dir}/{media.media_file} to {target_file}: {str(e)}",
                        exc_info=True,
                    )
                    clear_failed_export(export_request)
                    return False  # to stop chain
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
                    clear_failed_export(export_request)
                    return False  # to stop chain

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
