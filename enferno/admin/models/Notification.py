from datetime import datetime
from typing import Any
from enferno.user.models import Role, User
from enferno.admin.constants import Constants
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db
from enferno.utils.base import BaseMixin
import json
from enferno.utils.email_utils import EmailUtils

NotificationEvent = Constants.NotificationEvent
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

    def send(self) -> bool:
        """Send notification via appropriate delivery method."""
        if self.delivery_method == Notification.DELIVERY_METHOD_EMAIL and self.user.email:
            return EmailUtils.send_email(
                recipient=self.user.email,
                subject=self.title,
                body=f"{self.title}\n\n{self.message}",
            )
        elif self.delivery_method == Notification.DELIVERY_METHOD_SMS:
            # TODO: Implement SMS delivery
            return False
        else:  # internal
            return True

    @staticmethod
    def create(
        user: User,
        title: str,
        message: str,
        type: str = TYPE_GENERAL,
        delivery_method: str = DELIVERY_METHOD_INTERNAL,
        is_urgent: bool = False,
    ) -> "Notification":
        # Simple validation
        valid_types = [
            Notification.TYPE_GENERAL,
            Notification.TYPE_UPDATE,
            Notification.TYPE_SECURITY,
        ]

        delivery_method = delivery_method.lower()
        type = type.lower()

        if type not in valid_types:
            raise ValueError(f"Invalid notification type. Must be one of {valid_types}")

        valid_delivery_methods = [
            Notification.DELIVERY_METHOD_EMAIL,
            Notification.DELIVERY_METHOD_SMS,
            Notification.DELIVERY_METHOD_INTERNAL,
        ]
        if delivery_method not in valid_delivery_methods:
            raise ValueError(f"Invalid delivery method. Must be one of {valid_delivery_methods}")

        # Create notification object
        notification = Notification(
            user=user,
            title=title,
            message=message,
            notification_type=type,
            delivery_method=delivery_method,
            is_urgent=is_urgent,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def send_notification_to_user_for_event(
        event: str | NotificationEvent,
        user: User,
        title: str,
        message: str,
        category: str = TYPE_GENERAL,
        is_urgent: bool = False,
    ) -> bool:
        """Send notification to user for event.

        Args:
            event: str | NotificationEvent
            user: User
            title: str
            message: str
            category: str
            is_urgent: bool

        Returns:
            bool: True if notification was sent, False otherwise
        """
        # get config
        from enferno.settings import Config as cfg

        config = cfg.NOTIFICATIONS

        if isinstance(event, str):
            event = event.upper()
        else:
            event = event.value

        if event not in config:
            raise ValueError(f"Event {event} not found in config")

        event_config = config[event]

        delivery_methods = []
        if cfg.MAIL_ENABLED and "email_enabled" in event_config and event_config["email_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_EMAIL)
        if "in_app_enabled" in event_config and event_config["in_app_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_INTERNAL)
        if "sms_enabled" in event_config and event_config["sms_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_SMS)

        # send notification
        results = []
        for method in delivery_methods:
            notification = Notification.create(
                user=user,
                title=title,
                message=message,
                type=category,
                delivery_method=method,
                is_urgent=is_urgent,
            )
            if result := notification.send():
                results.append(result)
            else:
                logger.warning(
                    f"Failed to send notification for event {event} to user {user.id} using method {method}"
                )
        if not any(results):
            logger.error(
                f"Failed to send notification for event {event} to user {user.id} using any method"
            )
        return any(results)

    @staticmethod
    def send_notification_to_admins_for_event(
        event: str | NotificationEvent,
        title: str,
        message: str,
        category: str = TYPE_GENERAL,
        is_urgent: bool = False,
    ) -> bool:
        """Send notification to admins for event.

        Args:
            event: str | NotificationEvent
            title: str
            message: str
            category: str
            is_urgent: bool

        Returns:
            bool: True if notifications were sent to all admins, False otherwise
        """
        # get config
        from enferno.settings import Config as cfg

        config = cfg.NOTIFICATIONS

        if isinstance(event, str):
            event = event.upper()
        else:
            event = event.value

        if event not in config:
            raise ValueError(f"Event {event} not found in config")

        event_config = config[event]

        # get delivery methods
        delivery_methods = []
        if cfg.MAIL_ENABLED and "email_enabled" in event_config and event_config["email_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_EMAIL)
        if "in_app_enabled" in event_config and event_config["in_app_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_INTERNAL)
        if "sms_enabled" in event_config and event_config["sms_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_SMS)

        # admins
        admins = User.query.filter(User.roles.any(Role.name == "Admin")).all()

        # send notification
        results = []
        for admin in admins:
            admin_results = []
            for method in delivery_methods:
                notification = Notification.create(
                    user=admin,
                    title=title,
                    message=message,
                    type=category,
                    delivery_method=method,
                    is_urgent=is_urgent,
                )
                if result := notification.send():
                    admin_results.append(result)
                else:
                    logger.warning(
                        f"Failed to send notification for event {event} to admin {admin.id} using method {method}"
                    )
            # consider success if at least one method was successful
            results.append(any(admin_results))

        if not any(results):
            logger.error(
                f"Failed to send notification for event {event} to admins using any method"
            )
            return False
        elif not all(results):
            logger.warning(f"Failed to send notification for event {event} to some admins")
        return any(results)
