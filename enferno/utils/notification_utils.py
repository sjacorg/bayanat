from abc import ABC, abstractmethod
from enferno.admin.models.Notification import Notification
from enferno.user.models import User
from enferno.extensions import db
from pydantic import BaseModel, model_validator
from pydantic import ConfigDict
from enferno.utils.logging_utils import get_logger
from flask import render_template_string
from enferno.extensions import mail
from flask_mail import Message
import logging

logger = get_logger()

# Configure Flask-Mail's logger to use our custom logger
mail_logger = logging.getLogger("flask_mail")
mail_logger.parent = logger
mail_logger.propagate = True


class NotificationDeliveryStrategy(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        raise NotImplementedError


class EmailNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        try:
            # TODO: Support custom templates/jinja2 templates

            if not notification.user.email:
                logger.error("User has no email address")
                return False

            # Create the email message
            msg = Message(
                subject=notification.title,
                recipients=[notification.user.email],
                # Plain text version
                body=f"{notification.title}\n\n{notification.message}",
            )

            # Send the email
            mail.send(msg)
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}", exc_info=True)
            return False


class SmsNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        # TODO: Implement SMS delivery
        return True


class InternalNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        return True


class NotificationData(BaseModel):
    user: User
    title: str
    message: str
    type: str = Notification.TYPE_GENERAL
    delivery_method: str = Notification.DELIVERY_METHOD_INTERNAL
    is_urgent: bool = False

    @model_validator(mode="after")
    def validate_fields(self) -> "NotificationData":
        # Validate type
        valid_types = [
            Notification.TYPE_GENERAL,
            Notification.TYPE_UPDATE,
            Notification.TYPE_SECURITY,
        ]

        self.delivery_method = self.delivery_method.lower()
        self.type = self.type.lower()

        if self.type not in valid_types:
            raise ValueError(f"Invalid notification type. Must be one of {valid_types}")

        # Validate delivery method
        if self.delivery_method not in NotificationUtils._strategies.keys():
            raise ValueError(
                f"Invalid delivery method. Must be one of {NotificationUtils._strategies.keys()}"
            )

        return self

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Needed for the User model


class NotificationUtils:
    _strategies = {
        Notification.DELIVERY_METHOD_EMAIL: EmailNotificationDeliveryStrategy(),
        Notification.DELIVERY_METHOD_SMS: SmsNotificationDeliveryStrategy(),
        Notification.DELIVERY_METHOD_INTERNAL: InternalNotificationDeliveryStrategy(),
    }

    @staticmethod
    def send_notification(
        user: User,
        title: str,
        message: str,
        type: str = Notification.TYPE_GENERAL,
        delivery_method: str = Notification.DELIVERY_METHOD_INTERNAL,
        is_urgent: bool = False,
    ) -> Notification:
        # Validate all inputs using Pydantic
        notification_data = NotificationData(
            user=user,
            title=title,
            message=message,
            type=type,
            delivery_method=delivery_method,
            is_urgent=is_urgent,
        )

        # Create notification object
        notification = Notification(
            user=notification_data.user,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.type,
            delivery_method=notification_data.delivery_method,
            is_urgent=notification_data.is_urgent,
        )
        db.session.add(notification)
        db.session.commit()

        strategy = NotificationUtils._strategies.get(notification_data.delivery_method)
        result = strategy.send(notification)
        if not result:
            raise Exception("Failed to send notification")

        return notification
