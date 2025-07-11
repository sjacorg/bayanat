from datetime import datetime
from typing import Any
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db
from enferno.utils.base import BaseMixin
import json

logger = get_logger()


class Notification(db.Model, BaseMixin):
    TYPE_GENERAL = "general"
    TYPE_UPDATE = "update"
    TYPE_SECURITY = "security"

    DELIVERY_METHOD_EMAIL = "email"
    DELIVERY_METHOD_SMS = "sms"
    DELIVERY_METHOD_INTERNAL = "internal"

    # Status constants for API filtering
    STATUS_READ = "read"
    STATUS_UNREAD = "unread"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", foreign_keys=[user_id], backref="user_notifications")
    title = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String, nullable=False, default=TYPE_GENERAL)
    read_status = db.Column(db.Boolean, default=False)
    delivery_method = db.Column(db.String, nullable=False, default=DELIVERY_METHOD_INTERNAL)
    read_at = db.Column(db.DateTime)
    is_urgent = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.Index("ix_notification_user_read", "user_id", "read_status"),
        db.Index("ix_notification_user_type", "user_id", "notification_type"),
    )

    def mark_as_read(self):
        """Marks the notification as read and sets the read timestamp."""
        if not self.read_status:
            self.read_status = True
            self.read_at = datetime.now()
            self.save()

    def to_dict(self) -> dict[str, Any]:
        """Converts notification object to a dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.notification_type,
            "read_status": self.read_status,
            "read_at": DateHelper.serialize_datetime(self.read_at) if self.read_at else None,
            "is_urgent": self.is_urgent,
            "created_at": (
                DateHelper.serialize_datetime(self.created_at) if self.created_at else None
            ),
            "updated_at": (
                DateHelper.serialize_datetime(self.updated_at) if self.updated_at else None
            ),
        }

    def to_json(self) -> str:
        """Converts notification object to a JSON string."""
        return json.dumps(self.to_dict())
