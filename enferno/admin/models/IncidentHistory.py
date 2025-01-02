import json
from typing import Any

from sqlalchemy import JSON

from enferno.admin.models.utils import check_history_access
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class IncidentHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for incident revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incident.id"), index=True)
    incident = db.relationship(
        "Incident",
        backref=db.backref("history", order_by="IncidentHistory.updated_at"),
        foreign_keys=[incident_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="incident_revisions", foreign_keys=[user_id])

    @property
    def restricted_data(self):
        return {
            "comments": self.data.get("comments"),
            "status": self.data.get("status"),
        }

    # serialize
    @check_history_access
    def to_dict(self, full=False) -> dict[str, Any]:
        """Return a dictionary representation of the incident revision."""
        return {
            "id": self.id,
            "data": self.data if full else self.restricted_data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the incident revision."""
        return json.dumps(self.to_dict(), sort_keys=True)
