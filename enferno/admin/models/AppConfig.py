from typing import Any

from sqlalchemy import JSON

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class AppConfig(db.Model, BaseMixin):
    """Global Application Settings. (SQL Alchemy model)"""

    id = db.Column(db.Integer, primary_key=True)
    config = db.Column(JSON, nullable=False)

    # add user reference
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_configs", foreign_keys=[user_id])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the app config."""
        return {
            "id": self.id,
            "config": self.config,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_dict() if self.user else {},
        }
