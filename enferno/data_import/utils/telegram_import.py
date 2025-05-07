import os

import boto3
from botocore.exceptions import ClientError

from enferno.admin.models import Bulletin, Activity, Source, Media
from enferno.user.models import User
from enferno.data_import.models import DataImport
from enferno.utils.data_helpers import media_check_duplicates
from enferno.utils.base import DatabaseException

from enferno.settings import Config as cfg


class TelegramImport:
    """
    A class to handle Telegram bot interactions.
    """

    def __init__(self, data_imports):
        """
        Initialize the TelegramUtils class.

        Args:
            batch_id (str): The batch ID.
            meta (dict): Metadata for the batch.
            user_id (str): The user ID.
            data_import_id (str): The data import ID.
            file_path (str): The file path for the batch.
        """
        self.data_imports = [DataImport.query.get(log_id) for log_id in data_imports]

        self.batch_id = self.data_imports[0].batch_id

        self.info = self.data_imports[0].data.get("info")

        self.channel_metadata = self.info.get("channel_metadata")
        self.bucket = self.data_imports[0].data.get("bucket")
        self.folder = self.data_imports[0].data.get("folder")

        self.medias = []

    def check_file(self, data_import, s3_path):
        """
        Check if the file exists in S3.

        Args:
            s3_path (str): The S3 path to the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        etag, mime_type = None, None
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                region_name=cfg.AWS_REGION,
            )
            request = s3.head_object(Bucket=self.bucket, Key=s3_path)
            etag = request["ETag"].strip('"')
            mime_type = request["ContentType"]
            return etag, mime_type
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                data_import.add_to_log(f"File not found: {s3_path}")
            else:
                data_import.add_to_log(f"Error checking file: {e}")
            return False, False

    def copy_file(self, data_import, s3_path, filename):
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                region_name=cfg.AWS_REGION,
            )

            data_import.add_to_log(
                f"Copying video file to {cfg.S3_BUCKET}/{filename} from {self.bucket + '/' + s3_path}"
            )
            s3.copy_object(
                Bucket=cfg.S3_BUCKET,
                CopySource=self.bucket + "/" + s3_path,
                Key=filename,
            )
            return True
        except ClientError as e:
            data_import.add_to_log(f"Failed to copy {s3_path}. {e}")
            return False

    def create_bulletin(self):
        """
        Create a bulletin from the data.
        """
        message = self.info.get("message")
        self.data_imports[0].add_to_log(f"Creating bulletin from{message.get("id")}...")

        bulletin = Bulletin()
        bulletin.title = message.get("text")[:255]
        bulletin.description = message.get("text")
        bulletin.publish_date = message.get("date")
        bulletin.comments = f"Created via Telegram import - Batch: {self.batch_id}"
        bulletin.status = "Machine Created"

        bulletin.source_link = (
            f"https://t.me/{self.channel_metadata.get('username')}/{message.get('id')}"
        )
        bulletin.originid = f"{self.channel_metadata.get('username')}/{message.get('id')}"

        parent = Source.query.filter(Source.title == "Telegram").first()
        if not parent:
            parent = Source()
            parent.title = "Telegram"
            parent.save()
        source = Source.query.filter(Source.etl_id == str(self.channel_metadata.get("id"))).first()

        if not source:
            source = Source()
            source.etl_id = self.channel_metadata.get("id")

            source.parent = parent

            source.title = self.channel_metadata.get("title")
            source.comments = f"""username: {self.channel_metadata.get("username")} \n\n
                                    date_created: {self.channel_metadata.get("date_created")} \n\n
                                    participants_count: {self.channel_metadata.get("participants_count")} \n\n       
                                    Description: {self.channel_metadata.get('description')}"""
            # source.meta = self.channel_metadata
            source.save()

        bulletin.sources.append(parent)
        bulletin.sources.append(source)

        for m in self.medias:
            media = Media()
            media.main = True
            media.title = m.get("filename")
            media.media_file = m.get("filename")
            media.etag = m.get("etag")
            media.media_file_type = m.get("mime_type")

            bulletin.medias.append(media)

        bulletin.meta = self.info
        bulletin.meta["medias"] = self.medias

        try:
            bulletin.save(raise_exception=True)
            bulletin.create_revision(user_id=1)
            user = User.query.get(1)
            # Record bulletin creation activity
            Activity.create(
                user,
                Activity.ACTION_CREATE,
                Activity.STATUS_SUCCESS,
                bulletin.to_mini(),
                "bulletin",
            )
            for data_import in self.data_imports:
                data_import.add_to_log(f"Created Bulletin {bulletin.id} successfully.")
                data_import.add_item(bulletin.id)
                data_import.success()
        except DatabaseException as e:
            for data_import in self.data_imports:
                data_import.add_to_log(f"Failed to create Bulletin: {e}")

    def process(self):
        """
        Process the batch by copying the file and updating the database.
        """
        for data_import in self.data_imports:
            data_import.processing()
            if len(self.data_imports) > 1:
                data_import.add_to_log(
                    f"Main Telegram group import ID: {self.data_imports[0].id}..."
                )

        for data_import in self.data_imports:
            message = data_import.data.get("info").get("message")
            data_import.add_to_log(f"Processing Telegram media {message.get('id')}...")

            filename = data_import.file.split("/")[-1]
            s3_path = data_import.file.replace(f"{self.bucket}/", "")

            data_import.add_to_log(f"Checking file {s3_path}...")

            etag, mime_type = self.check_file(data_import, s3_path)

            if etag and mime_type:
                originid = f"{self.channel_metadata.get('username')}/{message.get('id')}"
                if (
                    media_check_duplicates(etag, data_import.id)
                    or Bulletin.query.filter(Bulletin.originid == originid).first()
                ):
                    data_import.fail(f"File {filename} already exists.")
                    continue
            else:
                data_import.fail(f"File {s3_path} not found.")
                continue

            copied = self.copy_file(data_import, s3_path, filename)

            if not copied:
                data_import.fail(f"Failed to copy {s3_path}.")
                continue

            self.medias.append(
                {
                    "s3_path": s3_path,
                    "filename": filename,
                    "etag": etag,
                    "mime_type": mime_type,
                }
            )

        if self.medias:
            self.create_bulletin()
