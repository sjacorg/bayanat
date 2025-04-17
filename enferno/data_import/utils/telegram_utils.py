import os

import boto3
from botocore.exceptions import ClientError

from enferno.admin.models import Bulletin, Activity, Source, Media
from enferno.user.models import User
from enferno.data_import.models import DataImport
from enferno.utils.data_helpers import media_check_duplicates
from enferno.utils.base import DatabaseException

from enferno.settings import Config as cfg
from sqlalchemy.orm.attributes import flag_modified


class TelegramImport:
    """
    A class to handle Telegram bot interactions.
    """

    def __init__(self, data_import_id):
        """
        Initialize the TelegramUtils class.

        Args:
            batch_id (str): The batch ID.
            meta (dict): Metadata for the batch.
            user_id (str): The user ID.
            data_import_id (str): The data import ID.
            file_path (str): The file path for the batch.
        """
        self.data_import = DataImport.query.get(data_import_id)
        self.batch_id = self.data_import.batch_id

        self.info = self.data_import.data.get("info")

        self.channel_metadata = self.info.get("channel_metadata")
        self.messages = self.info.get("messages")

        self.bucket = self.data_import.data.get("bucket")
        self.folder = self.data_import.data.get("folder")

        self.medias = []

    def check_file(self, s3_path):
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
                self.data_import.add_to_log(f"File not found: {s3_path}")
            else:
                self.data_import.add_to_log(f"Error checking file: {e}")
            return False, False

    def copy_file(self, s3_path, filename):
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                region_name=cfg.AWS_REGION,
            )

            self.data_import.add_to_log(
                f"Copying video file to {cfg.S3_BUCKET}/{filename} from {self.bucket + '/' + s3_path}"
            )
            s3.copy_object(
                Bucket=cfg.S3_BUCKET,
                CopySource=self.bucket + "/" + s3_path,
                Key=filename,
            )
            return True
        except ClientError as e:
            self.data_import.add_to_log(f"Failed to copy {s3_path}. {e}")
            return False

    def create_bulletin(self):
        """
        Create a bulletin from the data.
        """
        self.data_import.add_to_log(f"Creating bulletin from {self.messages[-1].get('id')}...")
        bulletin = Bulletin()
        bulletin.title = self.messages[-1].get("text")[:255]
        bulletin.description = self.messages[-1].get("text")
        bulletin.publish_date = self.messages[-1].get("date")
        bulletin.comments = f"Created via Telegram import - Batch: {self.batch_id}"
        bulletin.status = "Machine Created"
        bulletin.meta = self.info

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

            self.data_import.add_to_log(f"Created Bulletin {bulletin.id} successfully.")
            self.data_import.add_item(bulletin.id)
            self.data_import.success()
        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create Bulletin.")
            self.data_import.fail(e)

    def process(self):
        """
        Process the batch by copying the file and updating the database.
        """
        self.data_import.processing()
        self.data_import.add_to_log(f"Processing Telegram media {self.messages[-1].get('id')}...")

        for message in self.messages:
            s3_path = (
                self.folder + str(self.channel_metadata.get("id")) + "/" + message.get("media_path")
            )
            filename = s3_path.split("/")[-1]

            etag, mime_type = self.check_file(s3_path)

            if etag and mime_type:
                if media_check_duplicates(etag, self.data_import.id):
                    self.data_import.add_to_log(f"File {filename} already exists.")
                    continue
            else:
                self.data_import.add_to_log(f"File {s3_path} not found.")
                continue

            copied = self.copy_file(s3_path, filename)

            if not copied:
                self.data_import.add_to_log(f"Failed to copy {s3_path}.")
                continue

            self.medias.append(
                {
                    "media_path": message.get("media_path"),
                    "filename": filename,
                    "etag": etag,
                    "mime_type": mime_type,
                }
            )

        if self.medias:
            self.create_bulletin()
