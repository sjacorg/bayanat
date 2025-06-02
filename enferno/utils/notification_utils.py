from abc import ABC, abstractmethod
from enferno.admin.models.Notification import Notification
from enferno.user.models import Role, User
from enferno.extensions import db
from enferno.utils.notification_settings import NotificationSettings
from pydantic import BaseModel, model_validator
from pydantic import ConfigDict
from enferno.utils.logging_utils import get_logger
from enferno.utils.email_utils import EmailUtils
from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent
logger = get_logger()


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
    def send_notification_to_user_for_event(
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
        if cfg.MAIL_ENABLED and "email_enabled" in event_config and event_config["email_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_EMAIL)
        if "in_app_enabled" in event_config and event_config["in_app_enabled"]:
            delivery_methods.append(Notification.DELIVERY_METHOD_INTERNAL)
        if "sms_enabled" in event_config and event_config["sms_enabled"]:
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

    @staticmethod
    def send_notification_to_admins_for_event(
        event: str | NotificationEvent,
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
                _, result = NotificationUtils._send_notification(
                    admin, title, message, event_config["category"], method, is_urgent
                )
                admin_results.append(result)
                if not result:
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
