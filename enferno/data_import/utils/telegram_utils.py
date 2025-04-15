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
        self.message = self.info.get("message")

        self.bucket = self.data_import.data.get("bucket")
        self.folder = self.data_import.data.get("folder")
        self.s3_path = self.folder + str(self.channel_metadata.get("id")) + "/" + self.message.get("media_path")
        self.filename = self.s3_path.split("/")[-1]

    def copy_file(self):
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                region_name=cfg.AWS_REGION,
            )

            self.etag = s3.head_object(Bucket=self.bucket, Key=self.s3_path)["ETag"].strip('"')
            self.data_import.add_to_log(f"ETag: {self.etag}")
            # Check for duplicates using centralized helper
            if media_check_duplicates(etag=self.etag, data_import_id=self.data_import.id):
                # log duplicate and fail
                self.data_import.add_to_log(f"Video already exists in database.")
                return False

            self.data_import.add_to_log(
                f"Copying video file to {cfg.S3_BUCKET}/{self.filename} from {self.bucket + '/' + self.s3_path}"
            )
            s3.copy_object(
                Bucket=cfg.S3_BUCKET,
                CopySource=self.bucket + '/' + self.s3_path,
                Key=self.filename,
            )
            return True
        except ClientError as e:
            self.data_import.add_to_log(f"Video file not found. {e}")
            return False

    def create_bulletin(self):
        """
        Create a bulletin from the data.
        """
        self.data_import.add_to_log(f"Creating bulletin from {self.message.get('media_path')}...")
        bulletin = Bulletin()
        bulletin.title = self.message.get("text")[:255]
        bulletin.description = self.message.get("text")
        bulletin.publish_date = self.message.get("date")
        bulletin.comments = f"Created via Telegram import - Batch: {self.batch_id}"
        bulletin.status = "Machine Created"
        bulletin.meta = self.info

        parent = Source.query.filter(Source.title == "Telegram").first()
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

        media = Media()
        media.main = True
        media.media_file = self.filename
        media.etag = self.etag
        ext = os.path.splitext(self.filename)[1]
        if ext == ".mp4":
            media.media_file_type = "video/mp4"
        elif ext in [".jpg", ".jpeg"]:
            media.media_file_type = "image/jpeg"
        else:
            media.media_file_type = "other"
        
        bulletin.medias.append(media)
        
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
        self.data_import.add_to_log(f"Processing Telegram media {self.message.get('media_path')}...")

        if not self.copy_file():
            self.data_import.fail()
            return
        
        self.create_bulletin()
