import json

import boto3

from enferno.admin.models import Bulletin
from enferno.data_import.models import DataImport
from enferno.data_import.utils.media_import import MediaImport
from enferno.utils.data_helpers import media_check_duplicates

from enferno.settings import Config as cfg
from sqlalchemy.orm.attributes import flag_modified


class YTImport(MediaImport):

    def __init__(self, batch_id, data_import_id, meta):
        
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
        )
        self.meta = meta
        self.batch_id = batch_id
        self.data_import = DataImport.query.get(data_import_id)
        self.user_id = self.data_import.user_id

    def get_meta(self):
        self.data_import.add_to_log(f"Getting meta from {self.meta.get('bucket')}/{self.meta.get('meta_file')}")
        try:
            res = self.s3.get_object(Bucket=self.meta.get("bucket"), Key=self.meta.get("meta_file"))
            meta = json.loads(res["Body"].read())
            self.data_import.add_to_log(f"Successfully processed metadata.")
            return meta
        except Exception as e:
            self.data_import.add_to_log(f"Problem getting metadata: {e}")
            self.data_import.fail()
            return False
    
    def get_checksums(self):
        self.data_import.add_to_log(f"Getting checksums from {self.meta.get('bucket')}/{self.meta.get('checksum_file')}")
        try:
            res = self.s3.get_object(Bucket=self.meta.get("bucket"), Key=self.meta.get("checksum_file"))
            checksums = res["Body"].read().decode("utf-8").split("\n")
            checksums = [x.split() for x in checksums if x]
            checksums = {x[1]: x[0] for x in checksums}
            self.data_import.add_to_log(f"Successfully processed checksums.")
            return checksums
        except Exception as e:
            self.data_import.add_to_log(f"Problem getting checksums: {e}")
            self.data_import.fail()
            return False

    def process(self):
        self.data_import.processing()
        self.data_import.add_to_log(f"Processing web import {self.meta.get("id")}...")

        info = self.get_meta()
        info["checksums"] = self.get_checksums()

        if not info:
            self.data_import.add_to_log("Meta file not found.")
            self.data_import.fail()
            return

        filename = self.meta.get("id") + ".mp4"
        try:
            filepath = self.meta.get("bucket") + '/' + self.meta.get("video_file")
            self.data_import.add_to_log(f"Copying video file to {cfg.S3_BUCKET}/{filename} from {filepath}")
            self.s3.copy_object(
                Bucket=cfg.S3_BUCKET, CopySource=filepath, Key=filename
            )
        except Exception as e:
            self.data_import.add_to_log(f"Problem copying video file. {e}")
            self.data_import.fail()
            return

        info["etag"] = self.meta.get("etag")
        info["filepath"] = filepath
        info["bulletinTitle"] = info.get("title", self.meta.get("id"))

        # Bundle info for bulletin creation
        info["filename"] = filename
        info["source_url"] = info.get("webpage_url", "https://www.youtube.com/watch?v=" + self.meta.get("id"))
        info["File:MIMEType"] = "video/mp4"

        # Check for duplicates using centralized helper
        if (
            media_check_duplicates(etag=info["etag"], data_import_id=self.data_import.id)
            or Bulletin.query.filter(Bulletin.originid == self.meta.get("id")).first()
        ):
            # log duplicate and fail
            self.data_import.add_to_log(f"Video already exists in database.")
            self.data_import.fail()
            return

        # language = self.meta.get("transcription_language")
        # transcription = self.transcribe_video(info["filepath"], language)

        # if transcription:
        #     info["transcription"] = transcription

        self.data_import.data["info"] = info
        flag_modified(self.data_import, "data")
        self.data_import.add_to_log("Metadata parsed successfully.")
        self.create_bulletin(info)
