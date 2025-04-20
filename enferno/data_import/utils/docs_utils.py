import os

import boto3
import gnupg
import hashlib
import pandas as pd
import pyexifinfo as exiflib
from typing import Any, Literal, Optional
from pypdf import PdfReader
from pdf2image import convert_from_path
from pytesseract import image_to_string, pytesseract  
from PIL import Image      

from enferno.extensions import db
from enferno.settings import Config as cfg
from enferno.admin.models import Bulletin, Media, Activity
from enferno.user.models import User, Role
from enferno.data_import.utils.media_import import MediaImport
from enferno.utils.base import DatabaseException
from enferno.utils.data_helpers import get_file_hash, media_check_duplicates
from enferno.utils.date_helper import DateHelper

pytesseract.tesseract_cmd = cfg.TESSERACT_CMD

class DocImport(MediaImport):

    def __init__(self, batch_id, meta, user_id, data_import_id, file_path):
        super().__init__(batch_id, meta, user_id, data_import_id)
        self.file_path = file_path
        gpg_home = f"{os.environ.get('HOME')}/.gnupg"
        self.gpg = gnupg.GPG(gnupghome=gpg_home)

    def download_file(self):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
        )

        download_path = os.path.join(cfg.IMPORT_DIR, self.file_path.split("/")[-1]) + ".gpg"

        try:
            with open(download_path, "wb") as f:
                s3.download_fileobj(os.environ.get("DOCS_BUCKET"), self.file_path + ".gpg", f)
                self.data_import.add_to_log(f"File downloaded to {download_path}")
                return download_path
        except Exception as e:
            self.data_import.fail("Failed to download file.")
            self.data_import.add_to_log(str(e))
            return False

    def decrypt_file(self, file_path):
        with open(file_path, "rb") as stream:
            decrypted_data = self.gpg.decrypt_file(stream, passphrase=os.environ.get("PASSPHRASE"))

        new_file_path = file_path.replace(".gpg", "")
        if decrypted_data.ok:
            with open(new_file_path, "wb") as decrypted_stream:
                decrypted_stream.write(decrypted_data.data)
                self.data_import.add_to_log(f"File decrypted to {new_file_path}")
                return new_file_path
        else:
            self.data_import.fail("Failed to decrypt file.")
            return False

    def check_integrity(self, file_path):
        return self.meta["sha256"] == hashlib.sha256(open(file_path, "rb").read()).hexdigest()
    
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
                    text = image_to_string(image, lang="ara")
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
            self.data_import.add_to_log(f"Parsing image file {filepath} using Tesseract.")
            text_content = image_to_string(filepath, lang="ara")
            return text_content
        except Exception as e:
            self.data_import.add_to_log("Failed to parse image file using Tesseract.")
            self.data_import.add_to_log(str(e))
            return None

    def upload(self, filepath: str, target: str) -> bool:
        """
        Copies file to media folder or S3 bucket.

        Args:
            - filepath: Filepath of the file to be copied.
            - target: File name in media.

        Returns:
            - True if successful, False otherwise.
        """

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

    def remove_file(self, file_path):
        try:
            os.remove(file_path)
            self.data_import.add_to_log(f"Removed file: {file_path}")
        except Exception as e:
            self.data_import.add_to_log(f"Failed to remove file: {file_path}")
            self.data_import.add_to_log(str(e))

    def process(self):
        """
        Processes a file by downloading, decrypting, extracting metadata, performing OCR or text extraction,
        and uploading it to a media directory or S3 bucket. The process includes the following steps:
        1. Download the file.
        2. Decrypt the downloaded file.
        3. Generate a new filename and determine the file path.
        4. Upload the decrypted file to the media directory or S3 bucket.
        5. Retrieve metadata from the file.
        6. Perform OCR on images or text extraction on PDFs if applicable.
        7. Bundle the extracted text and metadata.
        8. Generate a file hash.
        9. Create a bulletin with the metadata.
        10. Clean up by removing the downloaded and decrypted files.
        Returns:
            None
        """

        downloaded_path = self.download_file()
        if not downloaded_path:
            return

        decrypted_path = self.decrypt_file(downloaded_path)
        if not decrypted_path:
            return

        if not self.check_integrity(decrypted_path):
            self.data_import.add_to_log("Integrity check failed.")
            self.data_import.fail()
            self.remove_file(downloaded_path)
            self.remove_file(decrypted_path)
            return

        self.data_import.file_hash = get_file_hash(decrypted_path)
        self.data_import.add_to_log("File hash generated successfully.")

        # checking for existing media or pending or processing imports
        if media_check_duplicates(self.data_import.file_hash, self.data_import.id):
            self.data_import.add_to_log(f"File already exists {self.file_path}.")
            self.data_import.fail()
            self.remove_file(downloaded_path)
            self.remove_file(decrypted_path)
            return

        filename = os.path.basename(decrypted_path)
        self.data_import.add_to_log(f"Processing {filename}...")

        title, ext = os.path.splitext(filename)
        self.data_import.file_format = ext[1:]

        filename = Media.generate_file_name(filename)
        filepath = (Media.media_dir / filename).as_posix()

        # copy file to media dir or s3 bucket
        if not self.upload(decrypted_path, filepath):
            self.data_import.add_to_log("Unable to upload media file. Terminating.")
            self.data_import.fail()
            self.remove_file(downloaded_path)
            self.remove_file(decrypted_path)
            return

        info = exiflib.get_json(decrypted_path)[0]
        self.data_import.add_to_log("Metadata retrieved successfully.")

        info["etag"] = self.data_import.file_hash

        rotated = False
        text_content = None
        # ocr pictures
        if ext[1:] in cfg.OCR_EXT:
            parsed_text = self.parse_pic(decrypted_path) or ""
             
            if info.get('EXIF:Orientation') == 'Rotate 270 CW':
                with Image.open(decrypted_path) as im:
                    new_filepath = decrypted_path.replace(f"{ext}", f"_rotated{ext}")
                    im.rotate(180).save(new_filepath)
                parsed_text += "<br><br> Rotated Image: <br><br>"
                parsed_text += self.parse_pic(new_filepath)
                rotated = True
                new_filename = new_filepath.split("/")[-1]
                new_etag = get_file_hash(new_filepath)
                if not self.upload(new_filepath, new_filename):
                    self.data_import.add_to_log("Unable to upload rotated media file.")

            elif info.get('EXIF:Orientation') == 'Horizontal (normal)':
                with Image.open(decrypted_path) as im:
                    new_filepath = decrypted_path.replace(f"{ext}", f"_rotated{ext}")
                    im.rotate(-90).save(new_filepath)
                parsed_text += "<br><br> Rotated Image: <br><br>"
                parsed_text += self.parse_pic(new_filepath)
                rotated = True
                new_filename = new_filepath.split("/")[-1]
                new_etag = get_file_hash(new_filepath)
                if not self.upload(new_filepath, new_filename):
                    self.data_import.add_to_log("Unable to upload rotated media file.")

            if parsed_text:
                text_content = parsed_text
                self.data_import.add_to_log("Text parsed successfully.")

        # scan pdf for text
        elif ext[1:] == "pdf":
            parsed_text = self.parse_pdf(decrypted_path, True)

            if parsed_text:
                text_content = parsed_text
                self.data_import.add_to_log("Text parsed successfully.")

        if text_content:
            info["text_content"] = text_content

        # bundle title with json info
        info["bulletinTitle"] = title
        info["filename"] = filename
        # pass filepath for cleanup purposes
        info["filepath"] = filepath

        if rotated:
            info["new_filename"] = new_filename
            info["new_filepath"] = new_filepath
            info["new_etag"] = new_etag

        self.data_import.add_to_log("Metadata parsed successfully.")
        self.create_bulletin(info)

        self.remove_file(downloaded_path)
        self.remove_file(decrypted_path)
        if rotated:
            self.remove_file(new_filepath)

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
        bulletin.comments = (
            f"2025 DOCS ETL. \n\n Path: {self.file_path} \n\n Batch ID: {self.batch_id}."
        )
        bulletin.source_link = self.file_path

        # tags
        bulletin.tags = []
        bulletin.tags.append(self.file_path)

        if "core team documentation/" in self.file_path: 
            bulletin.tags.append("Core Team Documentation")
        else:
            bulletin.tags.append("MP Documentation")

        bulletin.originid = self.file_path

        if info.get("text_content"):
            bulletin.description = info.get("text_content")

        create = info.get("EXIF:CreateDate")
        if create:
            create_date = DateHelper.file_date_parse(create)
            if create_date:
                bulletin.documentation_date = create_date

        bulletin.tags.append(str(self.batch_id))
        serial = info.get("EXIF:SerialNumber")
        if serial:
            bulletin.tags.append(str(serial))

        # media for the original file
        org_media = Media()
        # mark as undeletable
        org_media.main = True
        org_media.title = bulletin.title

        org_media.media_file = info.get("filename")
        # handle mime type failure
        mime_type = info.get("File:MIMEType")

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
            new_media.media_file_type = "image/jpeg"
            new_media.etag = info.get("new_etag")
            bulletin.medias.append(new_media)

        bulletin.roles = []
        r = Role.query.filter(Role.name == "Docs").first()
        if r:
            bulletin.roles.append(r)

        user = User.query.get(1)

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
