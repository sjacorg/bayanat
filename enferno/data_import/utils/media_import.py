import logging
import os, boto3
from typing import Any, Literal, Optional
import pyexifinfo as exiflib
from docx import Document
from pypdf import PdfReader
from pdf2image import convert_from_path

try:
    import whisper
    from whisper.tokenizer import TO_LANGUAGE_CODE

    whisper_available = True
except ImportError:
    whisper_available = False

from enferno.admin.models import Media, Bulletin, Source, Label, Location, Activity
from enferno.data_import.models import DataImport
from enferno.user.models import User, Role
from enferno.utils.data_helpers import get_file_hash, media_check_duplicates
from enferno.utils.date_helper import DateHelper
import arrow, shutil
from enferno.settings import Config as cfg
import subprocess

from enferno.utils.base import DatabaseException
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t
from enferno.extensions import db
from sqlalchemy import any_
from urllib.parse import urlparse

logger = get_logger()


def now() -> str:
    """Function to return current time in UTC."""
    return str(arrow.utcnow())


if cfg.OCR_ENABLED:
    from pytesseract import image_to_string, pytesseract

    try:
        pytesseract.tesseract_cmd = cfg.TESSERACT_CMD
        tesseract_langs = "+".join(pytesseract.get_languages(config=""))
    except Exception as e:
        logger.error(
            f"Tesseract system package is missing or Bayanat's OCR settings are not set properly: {e}"
        )


class MediaImport:
    """Class to handle media file imports."""

    # Import mode constants
    MODE_UPLOAD = 1  # Direct file upload mode
    MODE_SERVER = 2  # Server-side file processing mode
    MODE_WEB = 3  # Web import mode (e.g. YouTube)

    _whisper_model = None

    @classmethod
    def get_whisper_model(cls):
        if not cls._whisper_model and whisper_available and cfg.TRANSCRIPTION_ENABLED:
            cls._whisper_model = whisper.load_model(cfg.WHISPER_MODEL)
        return cls._whisper_model

    # file: Filestorage class
    def __init__(self, batch_id: t.id, meta: Any, user_id: Any, data_import_id: t.id):
        self.meta = meta
        self.batch_id = batch_id
        self.user_id = user_id
        self.data_import = DataImport.query.get(data_import_id)

    def upload(self, filepath: str, target: str) -> bool:
        """
        Copies file to media folder or S3 bucket.

        Args:
            - filepath: Filepath of the file to be copied.
            - target: File name in media.

        Returns:
            - True if successful, False otherwise.
        """

        if cfg.FILESYSTEM_LOCAL:
            try:
                shutil.copy(filepath, target)
                self.data_import.add_to_log(f"File saved as {target}.")
                return True
            except Exception as e:
                self.data_import.add_to_log("Failed to save file in local filesystem.")
                self.data_import.add_to_log(str(e))
                return False

        elif cfg.S3_BUCKET:
            target = os.path.basename(target)
            s3 = boto3.resource(
                "s3",
                aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                region_name=cfg.AWS_REGION,
            )
            try:
                s3.Bucket(cfg.S3_BUCKET).put_object(Key=target, Body=open(filepath, "rb"))
                self.data_import.add_to_log(f"File uploaded to S3 bucket.")
                return True
            except Exception as e:
                self.data_import.add_to_log("Failed to upload to S3 bucket.")
                self.data_import.add_to_log(str(e))
                return False
        else:
            self.data_import.add_to_log("Filesystem is not configured properly")
            return False

    def get_duration(self, filepath: str) -> Optional[str]:
        """
        Returns duration of a video file.

        Args:
            - filepath: Filepath of the video file.

        Returns:
            - Duration of the video file as float string.
        """
        try:
            # get video duration via ffprobe
            # cmd = f'ffprobe -i "{filepath}" -show_entries format=duration -v quiet -of csv="p=0"'
            cmd = [
                "ffprobe",
                "-i",
                f"{filepath}",
                "-show_entries",
                "format=duration",
                "-v",
                "quiet",
                "-of",
                "csv=p=0",
            ]
            duration = subprocess.check_output(cmd, shell=False).strip().decode("utf-8")
            return duration
        except Exception as e:
            self.data_import.add_to_log("Failed to get video duration")
            self.data_import.add_to_log(str(e))
            return None

    def parse_docx(self, filepath: str) -> Optional[str]:
        """
        Parses MS Word file.

        Args:
            - filepath: filepath of MS Word file.

        Returns:
            - text content of the MS Word file.
        """
        try:
            doc = Document(filepath)
            text_content = []

            for p in doc.paragraphs:
                if p.text:
                    text_content.append(p.text)

            return "<p>\n</p>".join(text_content)
        except Exception as e:
            self.data_import.add_to_log("Failed to parse DOCx file.")
            self.data_import.add_to_log(str(e))
            return None

    def parse_pdf(self, filepath: str, attempt_ocr: bool = False) -> Optional[str]:
        """
        Parses PDF file.

        Args:
            - filepath: filepath of PDF file.

        Returns:
            - text content of the PDF file.
        """
        try:
            pdf = PdfReader(filepath)
            text_content = []

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

            # if no text contect recognize
            # attempt to use Tesseract OCR
            if not text_content and attempt_ocr:
                images = convert_from_path(filepath)
                for image in images:
                    text = image_to_string(image, lang=tesseract_langs)
                    if text:
                        text_content.append(text)

            return "<p>\n</p>".join(text_content)

        except Exception as e:
            self.data_import.add_to_log("Failed to parse PDF file.")
            self.data_import.add_to_log(str(e))
            return None

    def parse_pic(self, filepath: str) -> Optional[Any]:
        """
        Parses image files using Google's
        Tesseract OCR engine for text content.

        Args:
            - filepath: filepath of image file.

        Returns:
            - text content of the image file.
        """
        try:
            text_content = image_to_string(filepath, lang=tesseract_langs)
            return text_content
        except Exception as e:
            self.data_import.add_to_log("Failed to parse image file using Tesseract.")
            self.data_import.add_to_log(str(e))
            return None

    def optimize(
        self, old_filename: str, old_path: str
    ) -> tuple[Literal[True], str, str, str] | tuple[Literal[False], None, None, None]:
        """
        Converts a video to H.264 format.

        Args:
            - old_filename: unoptimized video filename
            - old_path: video path

        Returns:
            - True/Flase: whether op is successful
            - new_filename: optimized video filename
            - new_filepath: optimized video file path
            - new_etag: optimized video md5 hash
        """
        check = ""
        _, ext = os.path.splitext(old_filename)

        try:
            # get video codec
            # cmd = f'ffprobe -i "{old_path}" -show_entries stream=codec_name -v quiet -of csv="p=0"'
            cmd = [
                "ffprobe",
                "-i",
                f"{old_path}",
                "-show_entries",
                "stream=codec_name",
                "-v",
                "quiet",
                "-of",
                "csv=p=0",
            ]
            check = subprocess.check_output(cmd, shell=False).strip().decode("utf-8")

        except Exception as e:
            self.data_import.add_to_log("Failed to get original video codec, optimizing anyway.")
            self.data_import.add_to_log(str(e))

        accepted_codecs = "h264" in check or "theora" in check or "vp8" in check
        accepted_formats = "mp4" in ext or "ogg" in ext or "webm" in ext
        accepted_codecs = accepted_formats

        if not accepted_formats or (accepted_formats and not accepted_codecs):
            # process video
            try:
                new_filename = f"{Media.generate_file_name(old_filename)}.mp4"
                new_filepath = (Media.media_dir / new_filename).as_posix()
                command = f'ffmpeg -i "{old_path}" -vcodec libx264  -acodec aac -strict -2 "{new_filepath}"'
                command = [
                    "ffmpeg",
                    "-i",
                    f"{old_path}",
                    "-vcodec",
                    "libx264",
                    "-acodec",
                    "aac",
                    "-strict",
                    "-2",
                    f"{new_filepath}",
                ]
                subprocess.call(command, shell=False)

                new_etag = get_file_hash(new_filepath)
                self.data_import.add_to_log(f"Optimized version saved at {new_filepath}.")
                return True, new_filename, new_filepath, new_etag

            except Exception as e:
                self.data_import.add_to_log("An exception occurred while transcoding file.")
                self.data_import.add_to_log(str(e))
                return False, None, None, None
        else:
            return False, None, None, None

    def transcribe_video(self, filepath: str, language: str = None) -> Optional[str]:
        """
        Transcribes video using Whisper.

        Args:
            - filepath: Path to the video file
            - language: Language code to use for transcription
        Returns:
            - Transcribed text if successful, None otherwise
        """
        whisper_model = self.get_whisper_model()
        if not cfg.TRANSCRIPTION_ENABLED or not whisper_available or not whisper_model:
            return None

        try:
            self.data_import.add_to_log(f"Transcribing video...")

            # Configure Whisper's logger to use our logging system
            whisper_logger = logging.getLogger("whisper")
            whisper_logger.addHandler(logger.handlers[0])  # Use our JSON formatter
            whisper_logger.setLevel(logging.INFO)

            if language and language.lower() in TO_LANGUAGE_CODE.values():
                self.data_import.add_to_log(f"Language: {language}")
                result = whisper_model.transcribe(
                    filepath, language=language, word_timestamps=True, verbose=True
                )
            else:
                self.data_import.add_to_log(f"Language: Auto-detect")
                result = whisper_model.transcribe(filepath, word_timestamps=True, verbose=True)

            if result and result.get("segments"):
                self.data_import.add_to_log("Video transcription completed successfully.")

                # Format transcription with timestamps for each segment
                transcription_parts = []
                for segment in result["segments"]:
                    start_time = str(arrow.get(segment["start"]).float_timestamp)
                    end_time = str(arrow.get(segment["end"]).float_timestamp)
                    text = segment["text"].strip()

                    transcription_parts.append(f"[{start_time}s - {end_time}s] {text}")

                formatted_transcription = "<br />".join(transcription_parts)
                return f"<br /><br />--- Auto-generated Transcription ---<br /><br />{formatted_transcription}<br /><br />--- End of Transcription ---"
            else:
                self.data_import.add_to_log("Transcription completed but no text was generated.")
            return None

        except Exception as e:
            self.data_import.add_to_log("Failed to transcribe video.")
            self.data_import.add_to_log(str(e))
            return None

    def process(self, file: str) -> Optional[Any]:
        duration = None
        optimized = False
        text_content = None
        transcription = None
        self.data_import.processing()

        # Check for duplicates using centralized helper
        if file.get("etag"):
            if media_check_duplicates(etag=file.get("etag"), data_import_id=self.data_import.id):
                # log duplicate and fail
                self.data_import.add_to_log(f"Duplicate file detected: {file.get('filename')}")
                self.data_import.fail()
                return

        import_mode = self.meta.get("mode")

        # Web import mode
        if import_mode == self.MODE_WEB:
            self.data_import.add_to_log(f"Processing web import {file.get('filename')}...")

            filename = file.get("filename")
            filepath = (Media.media_dir / filename).as_posix()
            info = exiflib.get_json(filepath)[0]

            # Add YouTube metadata
            youtube_info = self.data_import.data.get("info", {})
            if youtube_info:
                info.update(youtube_info)
                # Use YouTube title for bulletin
                info["bulletinTitle"] = youtube_info.get(
                    "title", os.path.splitext(file.get("name"))[0]
                )

            # Get file extension and duration
            _, ext = os.path.splitext(filename)
            file_ext = ext[1:].lower()
            self.data_import.add_format(file_ext)

            if file_ext in cfg.ETL_VID_EXT:
                duration = self.get_duration(filepath)
                info["vduration"] = duration

            # Upload to S3 if needed
            if not cfg.FILESYSTEM_LOCAL:
                self.upload(filepath, os.path.basename(filepath))

            # Bundle info for bulletin creation
            info["filename"] = filename
            info["filepath"] = filepath
            info["source_url"] = file.get("source_url")
            info["etag"] = file.get("etag")

            self.data_import.add_to_log("Metadata parsed successfully.")
            self.create_bulletin(info)
            return

        # Server-side mode
        elif import_mode == self.MODE_SERVER:
            self.data_import.add_to_log(f"Processing {file.get('filename')}...")

            old_path = file.get("path")

            # server side mode, need to copy files and generate etags
            old_filename = file.get("filename")
            title, ext = os.path.splitext(old_filename)

            filename = Media.generate_file_name(old_filename)
            filepath = (Media.media_dir / filename).as_posix()

            # copy file to media dir or s3 bucket
            if not self.upload(old_path, filepath):
                self.data_import.add_to_log("Unable to proceed without media file. Terminating.")
                self.data_import.fail()
                return

            info = exiflib.get_json(old_path)[0]

            # check file extension
            file_ext = ext[1:].lower()
            self.data_import.add_format(file_ext)

            # get duration and optimize if video
            if file_ext in cfg.ETL_VID_EXT:
                duration = self.get_duration(old_path)

                if self.meta.get("optimize"):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(
                        filename, filepath
                    )

            # ocr pictures
            elif cfg.OCR_ENABLED and self.meta.get("ocr") and file_ext in cfg.OCR_EXT:
                parsed_text = self.parse_pic(filepath)
                if parsed_text:
                    text_content = parsed_text

            # parse content of word
            elif self.meta.get("parse") and file_ext == "docx":
                parsed_text = self.parse_docx(filepath)
                if parsed_text:
                    text_content = parsed_text

            # scan pdf for text
            elif self.meta.get("parse") and file_ext == "pdf":
                attempt_ocr = cfg.OCR_ENABLED and self.meta.get("ocr")
                parsed_text = self.parse_pdf(filepath, attempt_ocr)

                if parsed_text:
                    text_content = parsed_text

        # Upload mode
        elif import_mode == self.MODE_UPLOAD:
            self.data_import.add_to_log(f"Processing {file.get('filename')}...")

            # we already have the file and the etag
            filename = file.get("filename")
            n, ext = os.path.splitext(filename)
            title, ex = os.path.splitext(file.get("name"))
            filepath = (Media.media_dir / filename).as_posix()
            info = exiflib.get_json(filepath)[0]

            if not cfg.FILESYSTEM_LOCAL:
                self.upload(filepath, os.path.basename(filepath))

            file_ext = ext[1:].lower()
            self.data_import.add_format(file_ext)

            # get duration and optimize if video
            if ext[1:].lower() in cfg.ETL_VID_EXT:
                duration = self.get_duration(filepath)

                if self.meta.get("optimize"):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(
                        filename, filepath
                    )

            # ocr pictures
            elif cfg.OCR_ENABLED and self.meta.get("ocr") and file_ext in cfg.OCR_EXT:
                parsed_text = self.parse_pic(filepath)
                if parsed_text:
                    text_content = parsed_text

            # parse content of word docs
            elif self.meta.get("parse") and file_ext == "docx":
                parsed_text = self.parse_docx(filepath)
                if parsed_text:
                    text_content = parsed_text

            # scan pdf for text
            elif self.meta.get("parse") and file_ext == "pdf":
                attempt_ocr = cfg.OCR_ENABLED and self.meta.get("ocr")
                parsed_text = self.parse_pdf(filepath, attempt_ocr)

                if parsed_text:
                    text_content = parsed_text

        else:
            self.data_import.add_to_log(f"Invalid import mode {import_mode}. Terminating.")
            self.data_import.fail()
            return

        if self.meta.get("transcription") and (
            info.get("File:MIMEType").startswith("video")
            or info.get("File:MIMEType").startswith("audio")
        ):
            language = self.meta.get("transcription_language")
            transcription = self.transcribe_video(filepath, language)

        # bundle title with json info
        info["bulletinTitle"] = title
        info["filename"] = filename
        # pass filepath for cleanup purposes
        info["filepath"] = filepath

        # include details of optimized files
        if optimized:
            info["new_filename"] = new_filename
            info["new_filepath"] = new_filepath
            info["new_etag"] = new_etag

        if text_content:
            info["text_content"] = text_content

        info["etag"] = file.get("etag")
        if import_mode == self.MODE_SERVER:
            info["old_path"] = old_path
        # pass duration
        if duration:
            info["vduration"] = duration

        if transcription:
            info["transcription"] = transcription

        self.data_import.add_to_log("Metadata parsed successfully.")
        self.create_bulletin(info)

    def create_bulletin(self, info: dict) -> None:
        """
        Creates bulletin from file and its meta data.

        Args:
            - info: dictionary containing bulletin info

        Returns:
            - None
        """
        bulletin = Bulletin()
        db.session.add(bulletin)

        # mapping
        bulletin.title = info.get("bulletinTitle")
        bulletin.status = "Machine Created"
        bulletin.comments = f"Created using Media Import Tool. Batch ID: {self.batch_id}."

        # Handle web import specific data
        is_web_import = self.meta.get("mode") == self.MODE_WEB
        if is_web_import:
            # Set source_link to original URL for duplicate checking
            bulletin.source_link = info.get("source_url")
            youtube_info = self.data_import.data.get("info", {})

            # Enhanced source handling
            uploader = youtube_info.get("uploader")
            uploader_id = youtube_info.get("uploader_id")
            uploader_url = youtube_info.get("uploader_url")
            channel_id = youtube_info.get("channel_id")
            channel_url = youtube_info.get("channel_url")
            channel = youtube_info.get("channel")

            domain = youtube_info.get("extractor_key")
            if not domain:
                url = urlparse(info.get("source_url")).netloc.lower()
                url = domain[4:] if domain.startswith("www.") else domain
                domain = url.split(".")[0].first()

            main_source = Source.query.filter(Source.title == domain).first()

            if not main_source:
                main_source = Source()
                main_source.title = domain
                main_source.etl_id = youtube_info.get("webpage_url_domain") or url
                main_source.save()
            bulletin.sources.append(main_source)

            source = None
            # Attempt to find existing source
            if uploader:
                source = (
                    Source.query.filter(Source.etl_id == uploader_id).first()
                    or Source.query.filter(Source.title == uploader).first()
                )
                if not source:
                    words = []
                    if uploader_url:
                        words.append(f"%{uploader_url}%")
                    if channel_id:
                        words.append(f"%{channel_id}%")
                    if channel_url:
                        words.append(f"%{channel_url}%")
                    if channel:
                        words.append(f"%{channel}%")
                    if words:
                        source = Source.query.filter(Source.comments.ilike(any_(words))).first()

            # Create new source if none found
            if not source:
                source = Source()
                source.title = uploader
                source.etl_id = uploader_id
                source.parent = main_source

                # Build comments only with available info
                comments = []
                if channel_id:
                    comments.append(f"channel_id: {channel_id}")
                if channel:
                    comments.append(f"channel: {channel}")
                if uploader_url:
                    comments.append(f"uploader_url: {uploader_url}")
                if channel_url:
                    comments.append(f"channel_url: {channel_url}")
                source.comments = " | ".join(comments) if comments else None
                source.save()

            if source:
                bulletin.sources.append(source)

            # Set bulletin fields
            if video_id := youtube_info.get("id"):
                bulletin.originid = video_id
            bulletin.source_link = youtube_info.get("webpage_url")
            bulletin.title = youtube_info.get("fulltitle")
            bulletin.title_ar = youtube_info.get("fulltitle")

            if upload_date := youtube_info.get("upload_date"):
                bulletin.publish_date = upload_date

            # Add YouTube info to bulletin meta
            if youtube_info:
                bulletin.meta = youtube_info
                if description := youtube_info.get("description"):
                    bulletin.description = description
        else:
            bulletin.source_link = info.get("old_path")

        if info.get("text_content"):
            bulletin.description = info.get("text_content")

        if info.get("transcription"):
            if bulletin.description:
                bulletin.description += info.get("transcription")
            else:
                bulletin.description = info.get("transcription")

        create = info.get("EXIF:CreateDate")
        if create:
            create_date = DateHelper.file_date_parse(create)
            if create_date:
                bulletin.documentation_date = create_date

        refs = [str(self.batch_id)]
        serial = info.get("EXIF:SerialNumber")
        if serial:
            refs.append(str(serial))

        # media for the original file
        org_media = Media()
        # mark as undeletable
        org_media.main = True

        # Set media title to video ID for web imports
        if is_web_import and youtube_info.get("id"):
            org_media.title = youtube_info.get("id")
        else:
            org_media.title = bulletin.title

        org_media.media_file = info.get("filename")
        # handle mime type failure
        mime_type = info.get("File:MIMEType")
        duration = info.get("vduration")
        if duration:
            org_media.duration = duration

        if not mime_type:
            self.data_import.add_to_log("Unable to retrieve file mime type.")
            try:
                os.remove(info.get("filepath"))
                self.data_import.add_to_log("Unknown file type removed.")
            except OSError as e:
                self.data_import.add_to_log("Unable to remove unknown file type.")
                self.data_import.add_to_log(str(e))

            self.data_import.fail()
            return

        org_media.media_file_type = mime_type
        org_media.etag = info.get("etag")
        bulletin.medias.append(org_media)

        # additional media for optimized video
        if info.get("new_filename"):
            new_media = Media()
            new_media.title = bulletin.title
            new_media.media_file = info.get("new_filename")
            new_media.media_file_type = "video/mp4"
            new_media.etag = info.get("new_etag")
            if duration:
                new_media.duration = duration
            bulletin.medias.append(new_media)

        # add additional meta data
        sources = self.meta.get("sources")
        if sources:
            ids = [s.get("id") for s in sources]
            bulletin.sources = Source.query.filter(Source.id.in_(ids)).all()

        labels = self.meta.get("labels")
        if labels:
            ids = [l.get("id") for l in labels]
            bulletin.labels = Label.query.filter(Label.id.in_(ids)).all()

        vlabels = self.meta.get("ver_labels")
        if vlabels:
            ids = [l.get("id") for l in vlabels]
            bulletin.ver_labels = Label.query.filter(Label.id.in_(ids)).all()

        locations = self.meta.get("locations")
        if locations:
            ids = [l.get("id") for l in locations]
            bulletin.locations = Location.query.filter(Location.id.in_(ids)).all()

        mrefs = self.meta.get("tags")

        if mrefs:
            refs = refs + mrefs
        bulletin.tags = refs

        # access roles restrictions
        roles = self.meta.get("roles")
        if roles:
            # Fetch Roles
            bulletin_roles = Role.query.filter(Role.id.in_([r.get("id") for r in roles])).all()
            bulletin.roles = []
            bulletin.roles.extend(bulletin_roles)

        user = User.query.get(self.user_id)

        bulletin.meta = info

        try:
            bulletin.save(raise_exception=True)
            bulletin.create_revision(user_id=user.id)
            # Record bulletin creation activity
            Activity.create(
                user,
                Activity.ACTION_CREATE,
                Activity.STATUS_SUCCESS,
                bulletin.to_mini(),
                "bulletin",
            )

            self.data_import.add_to_log(f"Created Bulletin {bulletin.id} successfully.")
            self.data_import.add_item(bulletin.id)
            self.data_import.sucess()
        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create Bulletin.")
            self.data_import.fail(e)
