# -*- coding: utf-8 -*-
import tempfile
from datetime import datetime
from pathlib import Path

import yt_dlp
from sqlalchemy.orm.attributes import flag_modified
from yt_dlp.utils import DownloadError

from enferno.admin.constants import Constants
from enferno.admin.models import Media
from enferno.admin.models.Notification import Notification
from enferno.data_import.models import DataImport
from enferno.tasks import celery, cfg
from enferno.user.models import User
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.media_download")


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

        # Notify user
        Notification.send_notification_for_event(
            Constants.NotificationEvent.WEB_IMPORT_STATUS,
            User.query.get(user_id),
            "Web Import Status",
            f"Web import of {url} has been completed successfully.",
        )

    except ValueError as e:
        # Handle specific error messages without traceback
        logger.error(f"Download failed: {str(e)}")
        data_import.add_to_log(f"Download failed: {str(e)}")
        data_import.fail()
        # Notify user
        Notification.send_notification_for_event(
            Constants.NotificationEvent.WEB_IMPORT_STATUS,
            User.query.get(user_id),
            "Web Import Status",
            f"Web import of {url} has failed.",
        )

    except Exception as e:
        # Handle other errors with traceback
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        data_import.add_to_log(f"Download failed: {str(e)}")
        data_import.fail()
        # Notify user
        Notification.send_notification_for_event(
            Constants.NotificationEvent.WEB_IMPORT_STATUS,
            User.query.get(user_id),
            "Web Import Status",
            f"Web import of {url} has failed.",
        )


def _get_ytdl_options(with_cookies: bool = False) -> dict:
    """Get yt-dlp options."""
    options = {
        # removed format to allow yt-dlp to choose the best format
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
            info["requested_downloads"][0].pop("__postprocessors")
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
    data_import.add_to_log("Format: mp4")
    data_import.add_to_log(f"Duration: {info.get('duration')}s")
    data_import.save()


def _start_etl_process(
    filename: str, url: str, batch_id: str, user_id: int, import_id: int
) -> None:
    """Start ETL process for downloaded file."""
    from enferno.tasks.data_import import etl_process_file

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
