# -*- coding: utf-8 -*-
import io
import mimetypes
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
import yt_dlp
from sqlalchemy.orm.attributes import flag_modified
from yt_dlp.utils import DownloadError

from enferno.extensions import db
from enferno.admin.constants import Constants
from enferno.admin.models import Media
from enferno.admin.models.Notification import Notification
from enferno.data_import.models import DataImport
from enferno.tasks import celery, cfg
from enferno.user.models import User
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.dep_utils import require_tools
from enferno.utils.logging_utils import get_logger

logger = get_logger("celery.tasks.media_download")


@celery.task
def download_media_from_web(url: str, user_id: int, batch_id: str, import_id: int) -> None:
    """Download and process media from web URL."""
    data_import = db.session.get(DataImport, import_id)
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
        _start_etl_process(final_filename, url, batch_id, user_id, import_id, info)

        # Notify user
        Notification.send_notification_for_event(
            Constants.NotificationEvent.WEB_IMPORT_STATUS,
            db.session.get(User, user_id),
            "Web Import Status",
            f"Web import of {url} has been completed successfully.",
        )

    except Exception as e:
        # Expected failures are raised as ValueError and need no traceback
        logger.error(f"Download failed: {e}", exc_info=not isinstance(e, ValueError))
        data_import.add_to_log(f"Download failed: {e}")
        data_import.fail()
        Notification.send_notification_for_event(
            Constants.NotificationEvent.WEB_IMPORT_STATUS,
            db.session.get(User, user_id),
            "Web Import Status",
            f"Web import of {url} has failed: {e}",
        )


def _get_ytdl_options(with_cookies: bool = False) -> dict:
    """Get yt-dlp options."""
    options = {
        # removed format to allow yt-dlp to choose the best format
        "outtmpl": str(Media.media_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "proxy": cfg.YTDLP_PROXY if cfg.YTDLP_PROXY else None,
        # Keep HLS on yt-dlp's own downloader, which honours any proxy (ffmpeg ignores SOCKS)
        "external_downloader": {"m3u8": "native"},
    }

    if with_cookies and cfg.YTDLP_COOKIES:
        # In memory only: a temp file would leave session cookies on disk
        options["cookiefile"] = io.StringIO(cfg.YTDLP_COOKIES)

    return options


def _run_download(url: str, options: dict) -> tuple[dict, Path]:
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        info["requested_downloads"][0].pop("__postprocessors", None)
        return info, Path(ydl.prepare_filename(info))


def _download_media(url: str) -> tuple[dict, Path]:
    """Download media using yt-dlp."""
    # Without them yt-dlp silently picks low-quality formats or saves raw HLS as .mp4
    require_tools("ffmpeg", "ffprobe")
    try:
        # First attempt without cookies
        return _run_download(url, _get_ytdl_options())

    except DownloadError as e:
        error_msg = str(e)
        if any(
            msg in error_msg.lower()
            for msg in ["unsupported url", "no video", "no downloadable video"]
        ):
            return _download_image(url)

        # Retry with cookies only when some are configured; otherwise report the real error
        if cfg.YTDLP_COOKIES and any(
            msg in error_msg.lower()
            for msg in [
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
                return _run_download(url, _get_ytdl_options(with_cookies=True))
            except DownloadError:
                # Don't chain the exception, just raise a new ValueError
                raise ValueError(
                    "Failed to download content. Authentication cookies may be expired or invalid."
                )

        # The task handler adds the "Download failed" prefix
        raise ValueError(error_msg)


def _download_image(url: str) -> tuple[dict, Path]:
    """Download a direct image URL that yt-dlp rejected."""
    max_size = cfg.MEDIA_UPLOAD_MAX_FILE_SIZE * 1024 * 1024
    session = requests.Session()
    # The configured proxy is the only route: ignore environment proxies and NO_PROXY.
    session.trust_env = False
    if cfg.YTDLP_PROXY:
        session.proxies = {"http": cfg.YTDLP_PROXY, "https": cfg.YTDLP_PROXY}
    try:
        # No redirects: the allowed-domains check only covers the submitted URL.
        with session.get(url, stream=True, timeout=60, allow_redirects=False) as response:
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            extension = mime_type.startswith("image/") and mimetypes.guess_extension(mime_type)
            if not extension or extension[1:] not in cfg.MEDIA_ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"This URL is not supported or contains no downloadable video content: {url}"
                )
            with NamedTemporaryFile(dir=Media.media_dir, suffix=extension, delete=False) as file:
                temp_file = Path(file.name)
                try:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if file.tell() + len(chunk) > max_size:
                            raise ValueError(
                                f"File exceeds maximum allowed size of {cfg.MEDIA_UPLOAD_MAX_FILE_SIZE} MB"
                            )
                        file.write(chunk)
                except BaseException:
                    temp_file.unlink()
                    raise
    except requests.RequestException as e:
        raise ValueError(f"Failed to download image: {e}") from None

    info = {"title": url, "webpage_url": url, "ext": extension[1:]}
    info["File:MIMEType"] = mime_type
    return info, temp_file


def _process_downloaded_file(temp_file: Path, info: dict) -> str:
    """Process downloaded file and return final filename."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    extension = info["ext"] if info.get("File:MIMEType", "").startswith("image/") else "mp4"
    final_filename = f"{info.get('id', 'web')}-{timestamp}.{extension}"
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
    data_import.add_to_log(f"Format: {file_path.suffix[1:]}")
    if info.get("duration") is not None:
        data_import.add_to_log(f"Duration: {info.get('duration')}s")
    data_import.save()


def _start_etl_process(
    filename: str, url: str, batch_id: str, user_id: int, import_id: int, info: dict
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
            "File:MIMEType": info.get("File:MIMEType", "video/mp4"),
        },
        user_id=user_id,
        data_import_id=import_id,
    )
