import json
from tempfile import NamedTemporaryFile
from typing import Any

import pandas as pd
import werkzeug

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from sqlalchemy import text

logger = get_logger()


class ClaimedViolation(db.Model, BaseMixin):
    """
    SQL Alchemy model for claimed violations
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    title_ar = db.Column(db.String)

    # serialize
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the claimed violation."""
        return {"id": self.id, "title": self.title, "title_tr": self.title_ar}

    def to_json(self) -> str:
        """Return a JSON representation of the claimed violation."""
        return json.dumps(self.to_dict())

    # populate from json dict
    def from_json(self, json: dict[str, Any]) -> "ClaimedViolation":
        """
        Populate the object from a json dictionary.

        Args:
            - json: the json dictionary.

        Returns:
            - the updated object.
        """
        self.title = json["title"]
        self.title_ar = json["title_tr"] if "title_tr" in json else ""
        return self

    # import csv data into db items
    @staticmethod
    def import_csv(file_storage: werkzeug.datastructures.FileStorage) -> str:
        """
        Import CSV data into the database.

        Args:
            - file_storage: the file storage.

        Returns:
            - an empty string on success.
        """
        tmp = NamedTemporaryFile().name
        file_storage.save(tmp)
        df = pd.read_csv(tmp)
        df.title_ar = df.title_ar.fillna("")
        db.session.bulk_insert_mappings(ClaimedViolation, df.to_dict(orient="records"))
        db.session.commit()

        # reset id sequence counter
        max_id = db.session.execute(text("select max(id)+1 from claimed_violation")).scalar()
        db.session.execute(
            text("alter sequence claimed_violation_id_seq restart with :m"), {"m": max_id}
        )
        db.session.commit()
        logger.info("Claimed Violation imported successfully.")
        return ""
