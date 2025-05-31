from datetime import datetime as dt
import json
from typing import Any, Optional

import arrow
from flask import current_app, has_app_context
from sqlalchemy import JSON

from enferno.admin.models import Actor, Bulletin
from enferno.extensions import db
from enferno.utils.base import BaseMixin, DatabaseException
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class DataImport(db.Model, BaseMixin):
    """
    SQL Alchemy model for Import Log table
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_imports", foreign_keys=[user_id])
    table = db.Column(db.String, nullable=False)
    item_id = db.Column(db.Integer)
    file = db.Column(db.String)
    file_format = db.Column(db.String)
    file_hash = db.Column(db.String)
    batch_id = db.Column(db.String)
    status = db.Column(db.String, nullable=False, default="Pending")
    imported_at = db.Column(db.DateTime)
    data = db.Column(JSON)
    log = db.Column(db.Text)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = ""

    def to_dict(self) -> dict:
        """
        Import Log Serializer.
        """
        return {
            "id": self.id,
            "class": self.__tablename__,
            "table": self.table,
            "item_id": self.item_id,
            "user": self.user.to_compact(),
            "file": self.file,
            "file_format": self.file_format,
            "file_hash": self.file_hash,
            "batch_id": self.batch_id,
            "status": self.status,
            "data": self.data,
            "log": self.log,
            "updated_at": DateHelper.serialize_datetime(self.updated_at)
            if self.updated_at
            else None,
            "created_at": DateHelper.serialize_datetime(self.created_at)
            if self.created_at
            else None,
            "imported_at": DateHelper.serialize_datetime(self.imported_at)
            if self.imported_at
            else None,
        }

    def add_item(self, item_id: int) -> None:
        """
        Add item id to import log.

        Args:
            - item_id: Item id to be added to import log.

        Returns:
            None
        """
        self.item_id = item_id
        self.save()

    def get_item(self) -> dict:
        """Return the item associated with the import log."""
        if self.table == "bulletin":
            return Bulletin.query.get(self.item_id).to_compact()
        if self.table == "actor":
            return Actor.query.get(self.item_id).to_compact()

    def add_file(self, file: str) -> None:
        """
        Add file to import log.

        Args:
            - file: File to be added to import log.

        Returns:
            None
        """
        self.file = file
        self.save()

    def add_format(self, file_format: str) -> None:
        """
        Add file format to import log.

        Args:
            - file_format: File format to be added to import log.

        Returns:
            None
        """
        self.file_format = file_format
        self.save()

    def add_to_log(self, line: str) -> None:
        """
        Add line to import log.

        Args:
            - line: Line to be added to import log.

        Returns:
            None
        """
        current_time = arrow.utcnow().format("YYYY-MM-DD HH:mm:ss ZZ")
        if self.log is None:
            self.log = ""
        self.log += f"{current_time}: {line}\n"
        self.save()

    def processing(self) -> None:
        """Update the status of the import log to processing."""
        self.status = "Processing"
        self.save()

    def success(self) -> None:
        """Update the status of the import log to success."""
        self.status = "Ready"
        self.imported_at = dt.utcnow()
        self.save()

    def fail(self, exception: Optional[Any] = None) -> None:
        """Update the status of the import log to fail."""
        self.status = "Failed"
        if exception:
            self.add_to_log(str(exception))
        self.save()

    def save(self) -> None:
        """Save the import log to the database."""
        try:
            super().save()
        except DatabaseException as e:
            if has_app_context():
                logger.error(f"{e}")
            else:
                print(f"{e}")


class Mapping(db.Model, BaseMixin):
    """
    SQL Alchemy model for sheet import mappings
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="mappings", foreign_keys=[user_id])
    data = db.Column(JSON)

    # serialize data
    def to_dict(self) -> dict:
        """Return the mapping as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "data": self.data,
        }

    def to_json(self) -> str:
        """Return the mapping as a JSON string."""
        return json.dumps(self.to_dict())
