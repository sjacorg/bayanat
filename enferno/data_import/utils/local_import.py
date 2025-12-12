"""Local filesystem import utility for Bayanat."""

import os
import shutil
from typing import Optional

import boto3
import pyexifinfo as exiflib

from enferno.extensions import db
from enferno.settings import Config
from enferno.admin.models import Bulletin, Media, Activity
from enferno.user.models import User, Role
from enferno.data_import.models import DataImport
from enferno.utils.base import DatabaseException
from enferno.utils.data_helpers import get_file_hash, media_check_duplicates
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()

# OCR imports (conditional)
try:
    from pytesseract import image_to_string, pytesseract

    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False
    logger.warning("pytesseract not available. OCR functionality will be unavailable.")

# PDF imports (conditional)
try:
    from pypdf import PdfReader
    from pdf2image import convert_from_path

    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False
    logger.warning("PDF support not available. Install pypdf and pdf2image.")


def _set_tesseract_path():
    """Set tesseract path from config or common locations."""
    tesseract_cmd = Config.get("TESSERACT_CMD")
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        pytesseract.tesseract_cmd = tesseract_cmd
    elif os.path.exists("/opt/homebrew/bin/tesseract"):
        pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
    elif os.path.exists("/usr/local/bin/tesseract"):
        pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"


class LocalImport:
    """Import files from local filesystem to Bayanat."""

    def __init__(self, file_path: str, batch_id: str, user_id: int, data_import: DataImport):
        self.file_path = file_path
        self.batch_id = batch_id
        self.user_id = user_id
        self.data_import = data_import

    def process(self) -> bool:
        """
        Process a local file and create a bulletin.

        Returns:
            True if successful, False otherwise.
        """
        self.data_import.processing()

        # Validate file exists
        if not os.path.isfile(self.file_path):
            self.data_import.add_to_log(f"File not found: {self.file_path}")
            self.data_import.fail()
            return False

        # Generate file hash
        file_hash = get_file_hash(self.file_path)
        self.data_import.file_hash = file_hash
        self.data_import.add_to_log(f"File hash: {file_hash}")

        # Check for duplicates
        if media_check_duplicates(file_hash, self.data_import.id):
            self.data_import.add_to_log("Duplicate file detected, skipping.")
            self.data_import.fail("Duplicate file")
            return False

        # Get filename and extension
        original_filename = os.path.basename(self.file_path)
        title, ext = os.path.splitext(original_filename)
        self.data_import.file_format = ext[1:].lower() if ext else ""
        self.data_import.add_to_log(f"Processing {original_filename}...")

        # Generate unique filename and copy to storage
        new_filename = Media.generate_file_name(original_filename)
        target_path = (Media.media_dir / new_filename).as_posix()

        if not self._copy_to_storage(self.file_path, target_path, new_filename):
            self.data_import.fail("Failed to copy file to storage")
            return False

        # Extract EXIF metadata
        info = self._extract_metadata(self.file_path)
        info["etag"] = file_hash

        # OCR for images
        text_content = None
        if ext[1:].lower() in Config.get("OCR_EXT", []):
            parsed_text = self._parse_pic(self.file_path)
            if parsed_text:
                text_content = parsed_text
                self.data_import.add_to_log("Text parsed successfully via OCR.")

        # PDF text extraction
        elif ext[1:].lower() == "pdf" and HAS_PDF_SUPPORT:
            parsed_text = self._parse_pdf(self.file_path, attempt_ocr=True)
            if parsed_text:
                text_content = parsed_text
                self.data_import.add_to_log("Text parsed successfully from PDF.")

        if text_content:
            info["text_content"] = text_content

        # Bundle metadata
        info["bulletinTitle"] = title
        info["filename"] = new_filename
        info["filepath"] = target_path

        self.data_import.add_to_log("Metadata parsed successfully.")

        # Create bulletin
        return self._create_bulletin(info)

    def _copy_to_storage(self, source: str, target: str, filename: str) -> bool:
        """
        Copy file to media storage (local or S3).

        Args:
            source: Source file path.
            target: Target file path (for local storage).
            filename: Filename for S3.

        Returns:
            True if successful, False otherwise.
        """
        if Config.get("FILESYSTEM_LOCAL"):
            try:
                shutil.copy(source, target)
                self.data_import.add_to_log(f"File copied to {target}")
                return True
            except Exception as e:
                self.data_import.add_to_log(f"Failed to copy file: {e}")
                return False

        elif Config.get("S3_BUCKET"):
            try:
                s3 = boto3.resource(
                    "s3",
                    aws_access_key_id=Config.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=Config.get("AWS_SECRET_ACCESS_KEY"),
                    region_name=Config.get("AWS_REGION"),
                )
                with open(source, "rb") as f:
                    s3.Bucket(Config.get("S3_BUCKET")).put_object(Key=filename, Body=f)
                self.data_import.add_to_log("File uploaded to S3")
                return True
            except Exception as e:
                self.data_import.add_to_log(f"Failed to upload to S3: {e}")
                return False

        self.data_import.add_to_log("Storage not configured")
        return False

    def _extract_metadata(self, filepath: str) -> dict:
        """
        Extract EXIF/file metadata.

        Args:
            filepath: Path to the file.

        Returns:
            Dictionary of metadata.
        """
        try:
            info = exiflib.get_json(filepath)[0]
            self.data_import.add_to_log("Metadata extracted")
            return info
        except Exception as e:
            self.data_import.add_to_log(f"Failed to extract metadata: {e}")
            return {}

    def _parse_pic(self, filepath: str) -> Optional[str]:
        """
        Parse image files using Tesseract OCR.

        Args:
            filepath: Path to image file.

        Returns:
            Text content from image, or None.
        """
        if not Config.get("OCR_ENABLED") or not HAS_PYTESSERACT:
            self.data_import.add_to_log("OCR not available, skipping image parsing.")
            return None

        try:
            _set_tesseract_path()
            self.data_import.add_to_log("Parsing image file using Tesseract OCR...")
            text_content = image_to_string(filepath, lang="ara")
            return text_content if text_content.strip() else None
        except Exception as e:
            self.data_import.add_to_log(f"Failed to parse image with OCR: {e}")
            return None

    def _parse_pdf(self, filepath: str, attempt_ocr: bool = False) -> Optional[str]:
        """
        Parse PDF file for text content.

        Args:
            filepath: Path to PDF file.
            attempt_ocr: Whether to attempt OCR if no text found.

        Returns:
            Text content from PDF, or None.
        """
        if not HAS_PDF_SUPPORT:
            self.data_import.add_to_log("PDF support not available.")
            return None

        try:
            pdf = PdfReader(filepath)
            text_content = []

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

            # If no text found, attempt OCR on pages
            if not text_content and attempt_ocr:
                if Config.get("OCR_ENABLED") and HAS_PYTESSERACT:
                    _set_tesseract_path()
                    self.data_import.add_to_log("No text in PDF, attempting OCR...")
                    images = convert_from_path(filepath)
                    for image in images:
                        text = image_to_string(image, lang="ara")
                        if text:
                            text_content.append(text)

            return "<p>\n</p>".join(text_content) if text_content else None

        except Exception as e:
            self.data_import.add_to_log(f"Failed to parse PDF: {e}")
            return None

    def _create_bulletin(self, info: dict) -> bool:
        """
        Create bulletin with media attachment.

        Args:
            info: Dictionary containing file metadata and parsed content.

        Returns:
            True if successful, False otherwise.
        """
        bulletin = Bulletin()
        db.session.add(bulletin)

        # Set bulletin fields
        bulletin.title = info.get("bulletinTitle")
        bulletin.status = "Machine Created"
        bulletin.comments = f"Local import.\n\nPath: {self.file_path}\n\nBatch ID: {self.batch_id}"
        bulletin.source_link = self.file_path
        bulletin.originid = self.file_path

        # Tags
        bulletin.tags = [self.batch_id]

        # Add serial number tag if available
        serial = info.get("EXIF:SerialNumber")
        if serial:
            bulletin.tags.append(str(serial))

        # Set description from OCR/PDF text
        if info.get("text_content"):
            bulletin.description = info.get("text_content")

        # Parse documentation date from EXIF
        create = info.get("EXIF:CreateDate")
        if create:
            create_date = DateHelper.file_date_parse(create)
            if create_date:
                bulletin.documentation_date = create_date
                self.data_import.add_to_log(f"Documentation date: {create_date}")

        # Store full metadata
        bulletin.meta = info

        # Assign Docs role for access control
        bulletin.roles = []
        docs_role = Role.query.filter(Role.name == "Docs").first()
        if docs_role:
            bulletin.roles.append(docs_role)

        # Create media record
        media = Media()
        media.main = True
        media.title = bulletin.title
        media.media_file = info.get("filename")
        media.etag = info.get("etag")

        # Get mime type from metadata
        mime_type = info.get("File:MIMEType")
        if not mime_type:
            # Fallback based on extension
            ext = os.path.splitext(info.get("filename", ""))[1].lower()
            mime_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".mp4": "video/mp4",
                ".pdf": "application/pdf",
            }
            mime_type = mime_map.get(ext, "application/octet-stream")

        media.media_file_type = mime_type
        bulletin.medias.append(media)

        # Get user for activity log
        user = User.query.get(self.user_id)

        try:
            bulletin.save(raise_exception=True)
            bulletin.create_revision(user_id=self.user_id)

            Activity.create(
                user,
                Activity.ACTION_CREATE,
                Activity.STATUS_SUCCESS,
                bulletin.to_mini(),
                "bulletin",
            )

            self.data_import.add_to_log(f"Created Bulletin {bulletin.id}")
            self.data_import.add_item(bulletin.id)
            self.data_import.success()
            return True

        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create bulletin: {e}")
            self.data_import.fail(str(e))
            return False
