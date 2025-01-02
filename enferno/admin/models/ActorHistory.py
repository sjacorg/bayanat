import json
from typing import Any

from sqlalchemy import JSON

from enferno.admin.models.utils import check_history_access
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class ActorHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for actor revisions
    """

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("actor.id"), index=True)
    actor = db.relationship(
        "Actor",
        backref=db.backref("history", order_by="ActorHistory.updated_at"),
        foreign_keys=[actor_id],
    )
    data = db.Column(JSON)
    # user tracking
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="actor_revisions", foreign_keys=[user_id])

    @property
    def restricted_data(self):
        return {
            "comments": self.data.get("comments"),
            "status": self.data.get("status"),
        }

    # serialize
    @check_history_access
    def to_dict(self, full=False) -> dict[str, Any]:
        """Return a dictionary representation of the actor revision."""
        return {
            "id": self.id,
            "data": self.data if full else self.restricted_data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the actor revision."""
        return json.dumps(self.to_dict(), sort_keys=True)


# --------------------------------- Incident History + Indexers -------------------------------------
