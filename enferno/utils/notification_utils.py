from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from enferno.admin.models.Notification import Notification
from enferno.user.models import User
from enferno.extensions import db
from pydantic import BaseModel, model_validator
from pydantic import ConfigDict
from enferno.utils.logging_utils import get_logger
from enferno.utils.email_utils import EmailUtils
from enferno.settings import Config as cfg

logger = get_logger()


class NotificationEvent(Enum):
    # Security Events - Always on for both internal and email
    LOGIN_NEW_IP = "login_new_ip"
    PASSWORD_CHANGE = "password_change"
    TWO_FACTOR_CHANGE = "two_factor_change"
    RECOVERY_CODES_CHANGE = "recovery_codes_change"
    FORCE_PASSWORD_CHANGE = "force_password_change"

    # Admin Events - Always on for internal, default on for email
    NEW_USER = "new_user"
    UPDATE_USER = "update_user"
    NEW_GROUP = "new_group"
    SYSTEM_SETTINGS_CHANGE = "system_settings_change"
    LOGIN_NEW_COUNTRY = "login_new_country"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    ADMIN_CREDENTIALS_CHANGE = "admin_credentials_change"
    ITEM_DELETED = "item_deleted"

    # Export Events - Always on for internal, default off for email
    NEW_EXPORT = "new_export"
    EXPORT_APPROVED = "export_approved"

    # Import Events - Default off for both
    NEW_BATCH = "new_batch"
    BATCH_STATUS = "batch_status"
    BULK_OPERATION_STATUS = "bulk_operation_status"
    WEB_IMPORT_STATUS = "web_import_status"

    # Assignment Events - Default on for internal, off for email
    NEW_ASSIGNMENT = "new_assignment"
    REVIEW_NEEDED = "review_needed"


@dataclass
class NotificationEventConfig:
    """Configuration for a notification event"""

    title_template: str
    message_template: str
    notification_type: str
    forced_delivery_methods: list[str] = []
    default_delivery_methods: list[str] = []
    is_urgent: bool = False


class NotificationDeliveryStrategy(ABC):
    @abstractmethod
    def send(self, notification: Notification) -> bool:
        raise NotImplementedError

    @abstractmethod
    def can_send(self, notification: Notification) -> bool:
        raise NotImplementedError


class EmailNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        if not self.can_send(notification):
            logger.error("User has no email address or email is disabled")
            return False

        return EmailUtils.send_email(
            recipient=notification.user.email,
            subject=notification.title,
            body=f"{notification.title}\n\n{notification.message}",
        )

    def can_send(self, notification: Notification) -> bool:
        return (
            bool(notification.user.email)
            and Notification.DELIVERY_METHOD_EMAIL in notification.delivery_methods
            and cfg.MAIL_ENABLED
        )


class SmsNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        # TODO: Implement SMS delivery
        raise NotImplementedError("SMS delivery is not implemented")

    def can_send(self, notification: Notification) -> bool:
        return False


class InternalNotificationDeliveryStrategy(NotificationDeliveryStrategy):
    def send(self, notification: Notification) -> bool:
        return True

    def can_send(self, notification: Notification) -> bool:
        return Notification.DELIVERY_METHOD_INTERNAL in notification.delivery_methods


class NotificationService:
    def __init__(self):
        self._strategies = {
            Notification.DELIVERY_METHOD_EMAIL: EmailNotificationDeliveryStrategy(),
            Notification.DELIVERY_METHOD_SMS: SmsNotificationDeliveryStrategy(),
            Notification.DELIVERY_METHOD_INTERNAL: InternalNotificationDeliveryStrategy(),
        }
        self._initialize_event_configs()

    def _initialize_event_configs(self):
        self._event_configs = {
            NotificationEvent.LOGIN_NEW_IP: NotificationEventConfig(
                title_template="New IP Address",
                message_template="A new IP address has been detected for your account.",
                notification_type=Notification.TYPE_SECURITY,
                forced_delivery_methods=[
                    Notification.DELIVERY_METHOD_INTERNAL,
                    Notification.DELIVERY_METHOD_EMAIL,
                ],
                default_delivery_methods=[],
                is_urgent=True,
            ),
            NotificationEvent.PASSWORD_CHANGE: NotificationEventConfig(
                title_template="Password Changed",
                message_template="Your password has been changed.",
                notification_type=Notification.TYPE_SECURITY,
                forced_delivery_methods=[
                    Notification.DELIVERY_METHOD_INTERNAL,
                    Notification.DELIVERY_METHOD_EMAIL,
                ],
                default_delivery_methods=[],
                is_urgent=True,
            ),
            NotificationEvent.TWO_FACTOR_CHANGE: NotificationEventConfig(
                title_template="Two-Factor Authentication Changed",
                message_template="Your two-factor authentication method has been changed.",
                notification_type=Notification.TYPE_SECURITY,
                forced_delivery_methods=[
                    Notification.DELIVERY_METHOD_INTERNAL,
                    Notification.DELIVERY_METHOD_EMAIL,
                ],
                default_delivery_methods=[],
                is_urgent=True,
            ),
            NotificationEvent.RECOVERY_CODES_CHANGE: NotificationEventConfig(
                title_template="Recovery Codes Changed",
                message_template="Your recovery codes have been changed.",
                notification_type=Notification.TYPE_SECURITY,
                forced_delivery_methods=[
                    Notification.DELIVERY_METHOD_INTERNAL,
                    Notification.DELIVERY_METHOD_EMAIL,
                ],
                default_delivery_methods=[],
                is_urgent=True,
            ),
            NotificationEvent.FORCE_PASSWORD_CHANGE: NotificationEventConfig(
                title_template="Password Change Required",
                message_template="A password change is required for your account.",
                notification_type=Notification.TYPE_SECURITY,
                forced_delivery_methods=[
                    Notification.DELIVERY_METHOD_INTERNAL,
                    Notification.DELIVERY_METHOD_EMAIL,
                ],
                default_delivery_methods=[],
                is_urgent=True,
            ),
            NotificationEvent.NEW_USER: NotificationEventConfig(
                title_template="New User",
                message_template="A new user has been created: {user_email}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.UPDATE_USER: NotificationEventConfig(
                title_template="User Updated",
                message_template="A user has been updated: {user_email}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.NEW_GROUP: NotificationEventConfig(
                title_template="New Group",
                message_template="A new group has been created: {group_name}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.SYSTEM_SETTINGS_CHANGE: NotificationEventConfig(
                title_template="System Settings Changed",
                message_template="The system settings have been changed.",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.LOGIN_NEW_COUNTRY: NotificationEventConfig(
                title_template="New Country",
                message_template="A login from a new country ({country_name}) has been detected for {user_email}.",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.UNAUTHORIZED_ACTION: NotificationEventConfig(
                title_template="Unauthorized Action",
                message_template="An unauthorized action has been detected for {user_email}.",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.ADMIN_CREDENTIALS_CHANGE: NotificationEventConfig(
                title_template="Admin Credentials Changed",
                message_template="The admin credentials have been changed.",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.ITEM_DELETED: NotificationEventConfig(
                title_template="Item Deleted",
                message_template="An item has been deleted: {item_name}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[Notification.DELIVERY_METHOD_EMAIL],
                is_urgent=False,
            ),
            NotificationEvent.NEW_EXPORT: NotificationEventConfig(
                title_template="New Export",
                message_template="A new export has been created: {export_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.EXPORT_APPROVED: NotificationEventConfig(
                title_template="Export Approved",
                message_template="An export has been approved: {export_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.NEW_BATCH: NotificationEventConfig(
                title_template="New Batch",
                message_template="A new batch has been created: {batch_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.BATCH_STATUS: NotificationEventConfig(
                title_template="Batch Status",
                message_template="The status of a batch has been updated: {batch_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.BULK_OPERATION_STATUS: NotificationEventConfig(
                title_template="Bulk Operation Status",
                message_template="The status of a bulk operation has been updated: {bulk_operation_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.WEB_IMPORT_STATUS: NotificationEventConfig(
                title_template="Web Import Status",
                message_template="The status of a web import has been updated: {web_import_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[],
                is_urgent=False,
            ),
            NotificationEvent.NEW_ASSIGNMENT: NotificationEventConfig(
                title_template="New Assignment",
                message_template="A new assignment has been created: {assignment_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                is_urgent=False,
            ),
            NotificationEvent.REVIEW_NEEDED: NotificationEventConfig(
                title_template="Review Needed",
                message_template="A review is needed for the following assignment: {assignment_id}",
                notification_type=Notification.TYPE_UPDATE,
                forced_delivery_methods=[],
                default_delivery_methods=[Notification.DELIVERY_METHOD_INTERNAL],
                is_urgent=False,
            ),
        }

    def _create_notification(
        self,
        user: User,
        title: str,
        message: str,
        notification_type: str = Notification.TYPE_GENERAL,
        delivery_methods: list[str] = None,
        is_urgent: bool = False,
    ) -> Optional[Notification]:
        """
        Creates and sends a notification through specified delivery methods.

        Args:
            user: The target user
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            delivery_methods: List of delivery methods to use
            is_urgent: Whether the notification is urgent
        """
        if not delivery_methods:
            delivery_methods = [Notification.DELIVERY_METHOD_INTERNAL]

        # Validate delivery methods
        delivery_methods = [method.lower() for method in delivery_methods]
        invalid_methods = [method for method in delivery_methods if method not in self._strategies]
        if invalid_methods:
            raise ValueError(f"Invalid delivery methods: {invalid_methods}")

        # Create notification
        notification = Notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            delivery_methods=delivery_methods,
            is_urgent=is_urgent,
        )

        db.session.add(notification)
        db.session.commit()

        # Attempt delivery through each method
        delivery_results = []
        for method in delivery_methods:
            strategy = self._strategies.get(method)
            if strategy and strategy.can_send(notification):
                success = strategy.send(notification)
                delivery_results.append(success)
                if not success:
                    logger.error(f"Failed to deliver notification via {method}")
            else:
                logger.warning(f"Skipping delivery method {method}: delivery not possible")
                delivery_results.append(False)

        # Log if all deliveries failed
        if not any(delivery_results) and delivery_results:
            logger.error(f"All delivery methods failed for notification {notification.id}")

        return notification

    def create_notification_for_event(
        self,
        event: NotificationEvent,
        user: User,
        template_data: dict = None,
        override_delivery_methods: list[str] = None,
    ) -> Optional[Notification]:
        """
        Creates a notification based on a predefined event.

        Args:
            event: The notification event
            user: Target user
            template_data: Data to format the title and message templates
            override_delivery_methods: Optional override of configurable delivery methods
                                    (does not affect forced delivery methods)
        """
        config = self._event_configs.get(event)
        if not config:
            raise ValueError(f"No configuration found for event: {event.value}")

        template_data = template_data or {}

        # Combine forced methods with either overridden or default methods
        delivery_methods = config.forced_delivery_methods.copy()

        # Add configurable methods (either override or default)
        configurable_methods = (
            override_delivery_methods
            if override_delivery_methods is not None
            else config.default_delivery_methods
        )

        # Only add configurable methods that aren't already forced
        delivery_methods.extend(
            [
                method
                for method in configurable_methods
                if method not in config.forced_delivery_methods
            ]
        )

        if not delivery_methods:
            logger.debug(f"No delivery methods specified for event {event.value}")
            return None

        try:
            title = config.title_template.format(**template_data)
            message = config.message_template.format(**template_data)
        except KeyError as e:
            logger.error(f"Missing template data for event {event.value}: {e}")
            raise ValueError(f"Missing required template data: {e}")

        return self._create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=config.notification_type,
            delivery_methods=delivery_methods,
            is_urgent=config.is_urgent,
        )

    def register_delivery_strategy(self, method: str, strategy: NotificationDeliveryStrategy):
        self._strategies[method.lower()] = strategy

    def register_event_config(self, event: NotificationEvent, config: NotificationEventConfig):
        self._event_configs[event] = config

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        Marks a notification as read for a specific user.

        Args:
            notification_id: ID of the notification
            user_id: ID of the user who owns the notification

        Returns:
            bool: True if successful, False otherwise
        """
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()

        if notification:
            notification.mark_as_read()
            return True
        return False
