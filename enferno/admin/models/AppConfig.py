from typing import Any

from sqlalchemy import JSON

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class AppConfig(db.Model, BaseMixin):
    """Global Application Settings. (SQL Alchemy model)"""

    # Secret fields that should not be stored in revision history
    SECRET_FIELDS = {
        "RECAPTCHA_PRIVATE_KEY",
        "GOOGLE_CLIENT_SECRET",
        "AWS_SECRET_ACCESS_KEY",
        "MAIL_PASSWORD",
        "YTDLP_COOKIES",
        "GOOGLE_MAPS_API_KEY",
        "GOOGLE_VISION_API_KEY",
    }

    id = db.Column(db.Integer, primary_key=True)
    config = db.Column(JSON, nullable=False)

    # add user reference
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_configs", foreign_keys=[user_id])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the app config with secrets excluded."""
        # Create a copy of config and remove secret fields
        sanitized_config = {
            key: value for key, value in self.config.items() if key not in self.SECRET_FIELDS
        }

        return {
            "id": self.id,
            "config": sanitized_config,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_dict() if self.user else {},
        }
