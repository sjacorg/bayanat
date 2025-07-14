from enferno.admin.models.Notification import Notification
from enferno.user.models import Role, User
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger
from enferno.utils.email_utils import EmailUtils
from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent
logger = get_logger()


def send_notification(notification: Notification) -> bool:
    """Send notification via appropriate delivery method."""
    if (
        notification.delivery_method == Notification.DELIVERY_METHOD_EMAIL
        and notification.user.email
    ):
        return EmailUtils.send_email(
            recipient=notification.user.email,
            subject=notification.title,
            body=f"{notification.title}\n\n{notification.message}",
        )
    elif notification.delivery_method == Notification.DELIVERY_METHOD_SMS:
        # TODO: Implement SMS delivery
        return False
    else:  # internal
        return True


class NotificationUtils:

    @staticmethod
    def _send_notification(
        user: User,
        title: str,
        message: str,
        type: str = Notification.TYPE_GENERAL,
        delivery_method: str = Notification.DELIVERY_METHOD_INTERNAL,
        is_urgent: bool = False,
    ) -> Notification:
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

        result = send_notification(notification)
        return notification, result

    @staticmethod
    def send_notification_to_user_for_event(
        event: str | NotificationEvent,
        user: User,
        title: str,
        message: str,
        category: str = Notification.TYPE_GENERAL,
        is_urgent: bool = False,
    ) -> bool:
        # get config
        from enferno.settings import Config as cfg

        config = cfg.NOTIFICATIONS

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
                user, title, message, category, method, is_urgent
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
        category: str = Notification.TYPE_GENERAL,
        is_urgent: bool = False,
    ) -> bool:
        # get config
        from enferno.settings import Config as cfg

        config = cfg.NOTIFICATIONS

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
                    admin, title, message, category, method, is_urgent
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
