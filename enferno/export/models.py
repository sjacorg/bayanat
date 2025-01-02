import os

from datetime import datetime as dt
from pathlib import Path
from typing import Any, Union

import arrow
from flask import current_app
from sqlalchemy import ARRAY
from flask_security.decorators import current_user

from enferno.extensions import db
from enferno.settings import Config as cfg

from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from itsdangerous import URLSafeSerializer

from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Export(db.Model, BaseMixin):
    export_dir = Path("enferno/exports")
    export_file_name = "export"
    signer = URLSafeSerializer(cfg.SECRET_KEY)
    """
    SQL Alchemy model for export table.
    """
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    requester = db.relationship("User", backref="user_exports", foreign_keys=[requester_id])
    items = db.Column(ARRAY(db.Integer))
    table = db.Column(db.String, nullable=False)
    file_format = db.Column(db.String, nullable=False)
    include_media = db.Column(db.Boolean, default=False)
    file_id = db.Column(db.String)
    ref = db.Column(ARRAY(db.String))
    comment = db.Column(db.Text)
    status = db.Column(db.String, nullable=False, default="Pending")
    approver_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    approver = db.relationship("User", backref="approved_exports", foreign_keys=[approver_id])
    expires_on = db.Column(db.DateTime)

    @property
    def unique_id(self):
        return Export.signer.dumps(self.id)

    @staticmethod
    def decrypt_unique_id(key: Union[str, bytes]) -> Any:
        """
        Static method to decrypt unique id.

        Args:
            - key: unique id.

        Returns:
            - export request id.
        """
        return Export.signer.loads(key)

    @property
    def expired(self):
        if self.expires_on:
            return dt.utcnow() > self.expires_on
        else:
            return True

    def from_json(self, table: str, json: dict) -> "Export":
        """
        Export Deserializer.

        Args:
            - table: str for the table the export is for
            - json: json request data

        Returns:
            - Export object
        """
        cfg = json.get("config")
        items = json.get("items")

        self.requester = current_user
        self.table = table
        self.items = items
        self.ref = cfg.get("ref") if "ref" in cfg else []
        self.comment = cfg.get("comment")
        self.file_format = cfg.get("format")
        self.include_media = cfg.get("includeMedia")

        return self

    def to_dict(self) -> dict:
        """
        Export Serializer.
        """
        return {
            "id": self.id,
            "class": self.__tablename__,
            "table": self.table,
            "requester": self.requester.to_compact(),
            "approver": self.approver.to_compact() if self.approver else None,
            "include_media": self.include_media,
            "file_format": self.file_format,
            "status": self.status,
            "comment": self.comment,
            "ref": self.ref or None,
            "file_id": self.file_id,
            "expires_on": DateHelper.serialize_datetime(self.expires_on)
            if self.expires_on
            else None,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
            "created_at": DateHelper.serialize_datetime(self.created_at)
            if self.created_at
            else None,
            "expired": self.expired,
            "uid": self.unique_id,
            "items": self.items,
        }

    def approve(self) -> "Export":
        """
        Method to approve Export requests.
        """
        self.status = "Processing"
        # set download expiry
        self.expires_on = dt.utcnow() + cfg.EXPORT_DEFAULT_EXPIRY
        self.approver = current_user

        return self

    def reject(self) -> "Export":
        """
        Method to reject Export requests.
        """
        self.status = "Rejected"

        return self

    def set_expiry(self, date) -> "Export":
        """
        Method to change expiry date/time
        """
        try:
            expires_on = arrow.get(date)
        except Exception as e:
            logger.error(f"Error saving export #{self.id}: \n {e}")

        if expires_on > arrow.utcnow():
            self.expires_on = expires_on.format("YYYY-MM-DDTHH:mm")

        return self

    @staticmethod
    def generate_export_dir() -> str:
        """
        Static method to generate export directory.

        Returns:
            - export directory
        """
        dir_id = f'export_{dt.utcnow().strftime("%Y%m%d-%H%M%S")}'
        Path(Export.export_dir / dir_id).mkdir(parents=True, exist_ok=True)
        return dir_id

    @staticmethod
    def generate_export_file() -> tuple[Path, str]:
        """
        static method to generate export file.

        Returns:
            - export file path, export directory
        """
        # Create unique directory
        dir_id = Export.generate_export_dir()
        return Export.export_dir / dir_id / Export.export_file_name, dir_id
