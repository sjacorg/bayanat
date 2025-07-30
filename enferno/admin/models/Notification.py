from datetime import datetime
from enferno.user.models import Role, User
from enferno.admin.constants import Constants
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from flask import current_app
from sqlalchemy import select, func, case, and_
from sqlalchemy.orm import selectinload
from enferno.utils.notification_config import NOTIFICATIONS_CONFIG, ALWAYS_ON_SECURITY_EVENTS

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

    @classmethod
    def get_paginated_with_stats(cls, user_id, page=1, per_page=10, status=None, is_urgent=None):
        """
        Efficient query that combines pagination + stats in a single database call.
        Returns tuple: (paginated_results, unread_count, has_urgent_unread)
        """
        # Build base query with select() syntax
        stmt = select(cls).where(cls.user_id == user_id).order_by(cls.created_at.desc())

        # Apply filters efficiently
        filters = []
        if status == "read":
            filters.append(cls.read_status == True)
        elif status == "unread":
            filters.append(cls.read_status == False)

        if is_urgent is not None:
            filters.append(cls.is_urgent == (is_urgent.lower() == "true"))

        if filters:
            stmt = stmt.where(and_(*filters))

        # Execute paginated query
        paginated = db.paginate(stmt, page=page, per_page=per_page, count=True)

        # Get stats in single optimized query using aggregate functions
        stats_stmt = select(
            func.count(case((cls.read_status == False, 1))).label("unread_count"),
            func.count(case((and_(cls.read_status == False, cls.is_urgent == True), 1))).label(
                "urgent_unread_count"
            ),
        ).where(cls.user_id == user_id)

        stats = db.session.execute(stats_stmt).one()

        return paginated, stats.unread_count, stats.urgent_unread_count > 0

    @classmethod
    def mark_all_read_for_user(cls, user_id):
        """Efficiently mark all notifications as read for a user."""
        from sqlalchemy import update

        stmt = (
            update(cls)
            .where(and_(cls.user_id == user_id, cls.read_status == False))
            .values(read_status=True, read_at=datetime.now())
        )
        db.session.execute(stmt)
        db.session.commit()

    @classmethod
    def get_unread_count(cls, user_id):
        """Fast unread count using scalar query."""
        stmt = select(func.count()).where(and_(cls.user_id == user_id, cls.read_status == False))
        return db.session.scalar(stmt)

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


def get_notification_config(event):
    """
    Adapter function that converts centralized config format to expected format.
    Checks both configurable events and always-on security events.
    Converts: email_enabled -> email, category -> urgent (security=True, others=False)
    """
    if hasattr(event, "value"):
        event = event.value
    elif isinstance(event, str):
        event = event.upper()

    # Get dynamic notifications config from Flask Config (includes config.json values)
    notifications_config = current_app.config.get("NOTIFICATIONS", {})

    # Check always-on security events first, then configurable events
    config = ALWAYS_ON_SECURITY_EVENTS.get(event) or notifications_config.get(
        event, {"email_enabled": False, "category": "general"}
    )

    result = {
        "email": config.get("email_enabled", False) and config.get("in_app_enabled", True),
        "urgent": config.get("category") == "security",
    }

    logger.info(f"get_notification_config({event}) -> config: {config}, result: {result}")

    # Convert to expected format
    return result
