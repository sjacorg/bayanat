import json
from typing import Any

from sqlalchemy import JSON

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class LocationHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for location revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), index=True)
    location = db.relationship(
        "Location",
        backref=db.backref("history", order_by="LocationHistory.updated_at"),
        foreign_keys=[location_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="location_revisions", foreign_keys=[user_id])

    # serialize
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the location revision."""
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the location revision."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def __repr__(self):
        return "<LocationHistory {} -- Target {}>".format(self.id, self.location_id)
