import json
from tempfile import NamedTemporaryFile
from typing import Any, Optional

import pandas as pd
import werkzeug
from sqlalchemy import text

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Eventtype(db.Model, BaseMixin):
    """
    SQL Alchemy model for event types
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)
    for_actor = db.Column(db.Boolean, default=False)
    for_bulletin = db.Column(db.Boolean, default=False)
    comments = db.Column(db.String)

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the event type."""
        return {
            "id": self.id,
            "title": self.title,
            "title_ar": self.title_ar or None,
            "for_actor": self.for_actor,
            "for_bulletin": self.for_bulletin,
            "comments": self.comments,
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_json(self) -> str:
        """Return a JSON representation of the event type."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Eventtype":
        """
        Create an event type object from a json dictionary.

        Args:
            - json: the json dictionary to create the event type from.

        Returns:
            - the event type object.
        """
        self.title = json.get("title", self.title)
        self.title_ar = json.get("title_ar", self.title_ar)
        self.for_actor = json.get("for_actor", self.for_actor)
        self.for_bulletin = json.get("for_bulletin", self.for_bulletin)
        self.comments = json.get("comments", self.comments)

        return self

    @staticmethod
    def find_by_title(title: str) -> Optional["Eventtype"]:
        """Return the first event type with the given title."""
        # search
        return Eventtype.query.filter(Eventtype.title.ilike(title.strip())).first()

    # imports data from csv
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Imports Eventtype data from a CSV file.

        Args:
            - file_storage: the file storage object containing the CSV data.

        Returns:
            - empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        df.comments = df.comments.fillna("")
        db.session.bulk_insert_mappings(Eventtype, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute(text("select max(id)+1 from eventtype")).scalar()
        db.session.execute(text("alter sequence eventtype_id_seq restart with :m"), {"m": max_id})
        db.session.commit()
        return ""
