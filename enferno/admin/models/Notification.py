from datetime import datetime
from enferno.user.models import Role, User
from enferno.admin.constants import Constants
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from flask import current_app

NotificationEvent = Constants.NotificationEvent
logger = get_logger()


class Notification(db.Model, BaseMixin):
    """Simplified notification model - single object with delivery method tracking"""

    # Notification types
    TYPE_GENERAL = "general"
    TYPE_UPDATE = "update"
    TYPE_SECURITY = "security"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", foreign_keys=[user_id], backref="notifications")
    title = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String, nullable=False, default=TYPE_GENERAL)
    read_status = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    is_urgent = db.Column(db.Boolean, default=False)

    # Email delivery tracking
    email_enabled = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    email_error = db.Column(db.Text)
    email_sent_at = db.Column(db.DateTime)

    # SMS delivery tracking (future use)
    sms_enabled = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    sms_error = db.Column(db.Text)

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

    def to_dict(self):
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

    @staticmethod
    def create_for_user(
        user, title, message, category=TYPE_GENERAL, is_urgent=False, send_email=False
    ):
        """Create notification for a specific user"""
        # Determine if email should be enabled
        email_enabled = (
            send_email and bool(user.email) and current_app.config.get("MAIL_ENABLED", False)
        )

        notification = Notification(
            user=user,
            title=title,
            message=message,
            notification_type=category,
            is_urgent=is_urgent,
            email_enabled=email_enabled,
        )
        db.session.add(notification)
        db.session.commit()

        # Queue email if enabled
        if email_enabled:
            from enferno.tasks import send_email_notification

            send_email_notification.delay(notification.id)

        return notification

    @staticmethod
    def create_for_admins(title, message, category=TYPE_SECURITY, is_urgent=False, send_email=True):
        """Create notifications for all admins"""
        admins = User.query.filter(User.roles.any(Role.name == "Admin")).all()
        notifications = []

        for admin in admins:
            notification = Notification.create_for_user(
                admin, title, message, category, is_urgent, send_email
            )
            notifications.append(notification)

        return notifications

    @staticmethod
    def send_notification_for_event(
        event, user, title, message, category=TYPE_GENERAL, is_urgent=False
    ):
        """Send notification to user based on event configuration"""
        config = get_notification_config(event)

        return Notification.create_for_user(
            user=user,
            title=title,
            message=message,
            category=category,
            is_urgent=is_urgent or config.get("urgent", False),
            send_email=config.get("email", False),
        )

    @staticmethod
    def send_admin_notification_for_event(
        event, title, message, category=TYPE_SECURITY, is_urgent=False
    ):
        """Send notification to all admins based on event configuration"""
        config = get_notification_config(event)

        return Notification.create_for_admins(
            title=title,
            message=message,
            category=category,
            is_urgent=is_urgent or config.get("urgent", False),
            send_email=config.get("email", True),  # Default to email for admin notifications
        )


# Simple notification configuration - replaces complex lookup logic
NOTIFICATION_CONFIGS = {
    # Security events (always email + urgent)
    NotificationEvent.LOGIN_NEW_IP.value: {"email": True, "urgent": True},
    NotificationEvent.PASSWORD_CHANGE.value: {"email": True, "urgent": True},
    NotificationEvent.TWO_FACTOR_CHANGE.value: {"email": True, "urgent": True},
    NotificationEvent.RECOVERY_CODES_CHANGE.value: {"email": True, "urgent": True},
    NotificationEvent.FORCE_PASSWORD_CHANGE.value: {"email": True, "urgent": True},
    # Admin security events (email enabled)
    NotificationEvent.NEW_USER.value: {"email": True, "urgent": False},
    NotificationEvent.UPDATE_USER.value: {"email": True, "urgent": False},
    NotificationEvent.NEW_GROUP.value: {"email": True, "urgent": False},
    NotificationEvent.SYSTEM_SETTINGS_CHANGE.value: {"email": True, "urgent": True},
    NotificationEvent.LOGIN_NEW_COUNTRY.value: {"email": True, "urgent": True},
    NotificationEvent.UNAUTHORIZED_ACTION.value: {"email": True, "urgent": True},
    NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value: {"email": True, "urgent": True},
    NotificationEvent.ITEM_DELETED.value: {"email": False, "urgent": False},
    # Export notifications (app only)
    NotificationEvent.NEW_EXPORT.value: {"email": False, "urgent": False},
    NotificationEvent.EXPORT_APPROVED.value: {"email": False, "urgent": False},
    # Import/batch operations (app only)
    NotificationEvent.NEW_BATCH.value: {"email": False, "urgent": False},
    NotificationEvent.BATCH_STATUS.value: {"email": False, "urgent": False},
    NotificationEvent.BULK_OPERATION_STATUS.value: {"email": False, "urgent": False},
    NotificationEvent.WEB_IMPORT_STATUS.value: {"email": False, "urgent": False},
    NotificationEvent.NEW_ASSIGNMENT.value: {"email": False, "urgent": False},
    NotificationEvent.REVIEW_NEEDED.value: {"email": False, "urgent": False},
}


def get_notification_config(event):
    """Simple notification configuration lookup"""
    if hasattr(event, "value"):
        event = event.value
    elif isinstance(event, str):
        event = event.upper()

    return NOTIFICATION_CONFIGS.get(event, {"email": False, "urgent": False})
