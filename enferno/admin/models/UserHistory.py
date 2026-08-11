import json
from typing import Any

from sqlalchemy import JSON

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class UserHistory(db.Model, BaseMixin):
    """
    SQL Alchemy model for user account revisions.

    Snapshots account and permission state so admins can answer
    "when did this user get this permission, and who granted it".
    Access is restricted to Admin at the endpoint level.
    """

    id = db.Column(db.Integer, primary_key=True)
    # the user this revision describes. Users are hard deleted, and every user
    # carries at least one revision, so cascade or deletion becomes impossible.
    target_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_user = db.relationship(
        "User",
        backref=db.backref(
            "history",
            order_by="UserHistory.updated_at",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
        foreign_keys=[target_user_id],
    )
    data = db.Column(JSON)
    # user tracking, who made the change. Kept on their deletion so the trail
    # of what happened to other accounts survives.
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    user = db.relationship("User", backref="user_revisions", foreign_keys=[user_id])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the user revision."""
        return {
            "id": self.id,
            "data": self.data,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_compact() if self.user else None,
        }

    def to_json(self) -> str:
        """Return a JSON representation of the user revision."""
        return json.dumps(self.to_dict(), sort_keys=True)

    def __repr__(self):
        return "<UserHistory {} -- Target {}>".format(self.id, self.target_user_id)
