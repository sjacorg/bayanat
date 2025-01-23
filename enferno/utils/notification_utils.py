from abc import ABC, abstractmethod
from enum import Enum
from enferno.admin.models.Notification import Notification
from enferno.user.models import User
from enferno.extensions import db
from enferno.utils.notification_settings import NotificationSettings
from pydantic import BaseModel, model_validator
from pydantic import ConfigDict
from enferno.utils.logging_utils import get_logger
from enferno.utils.email_utils import EmailUtils

logger = get_logger()


class NotificationEvent(Enum):
    """
    Notification events that are used in the app.
    """

    LOGIN_NEW_IP = "LOGIN_NEW_IP"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    TWO_FACTOR_CHANGE = "TWO_FACTOR_CHANGE"
    RECOVERY_CODES_CHANGE = "RECOVERY_CODES_CHANGE"
    FORCE_PASSWORD_CHANGE = "FORCE_PASSWORD_CHANGE"
    NEW_USER = "NEW_USER"
    UPDATE_USER = "UPDATE_USER"
    NEW_GROUP = "NEW_GROUP"
    SYSTEM_SETTINGS_CHANGE = "SYSTEM_SETTINGS_CHANGE"
    LOGIN_NEW_COUNTRY = "LOGIN_NEW_COUNTRY"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    ADMIN_CREDENTIALS_CHANGE = "ADMIN_CREDENTIALS_CHANGE"
    ITEM_DELETED = "ITEM_DELETED"
    NEW_EXPORT = "NEW_EXPORT"
    EXPORT_APPROVED = "EXPORT_APPROVED"
    NEW_BATCH = "NEW_BATCH"
    BATCH_STATUS = "BATCH_STATUS"
    BULK_OPERATION_STATUS = "BULK_OPERATION_STATUS"
    WEB_IMPORT_STATUS = "WEB_IMPORT_STATUS"
    NEW_ASSIGNMENT = "NEW_ASSIGNMENT"
    REVIEW_NEEDED = "REVIEW_NEEDED"


class NotificationDeliveryStrategy(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        raise NotImplementedError


class EmailNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        if not notification.user.email:
            logger.error("User has no email address")
            return False

        return EmailUtils.send_email(
            recipient=notification.user.email,
            subject=notification.title,
            body=f"{notification.title}\n\n{notification.message}",
        )


class SmsNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        # TODO: Implement SMS delivery
        raise NotImplementedError("SMS delivery is not implemented")


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
    def _send_notification(
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
        return notification, result

    @staticmethod
    def send_notification_for_event(
        event: str | NotificationEvent,
        user: User,
        title: str,
        message: str,
        is_urgent: bool = False,
    ) -> bool:
        # get config
        from enferno.settings import Config as cfg

        config = NotificationSettings.get_config()

        if isinstance(event, str):
            event = event.upper()
        else:
            event = event.value

        if event not in config:
            raise ValueError(f"Event {event} not found in config")

        # get event config
        event_config = config[event]

        # get delivery methods
        delivery_methods = []
        if cfg.MAIL_ENABLED and event_config["email_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_EMAIL)
        if event_config["in_app_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_INTERNAL)
        if event_config["sms_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_SMS)

        # send notification
        results = []
        for method in delivery_methods:
            _, result = NotificationUtils._send_notification(
                user, title, message, event_config["category"], method, is_urgent
            )
            results.append(result)
            if not result:
                logger.warning(
                    f"Failed to send notification for event {event} to user {user.id} using method {method}"
                )
        if not any(results):
            logger.error(
                f"Failed to send notification for event {event} to user {user.id} using any method"
            )
        return any(results)
