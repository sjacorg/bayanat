"""
Notification configuration - single source of truth for notification settings.
This module prevents circular imports between settings.py and config_utils.py.
"""

from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent

# Notification configuration - centralized and reusable
NOTIFICATIONS_CONFIG = {
    # Configurable events
    NotificationEvent.NEW_USER.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UPDATE_USER.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_GROUP.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.SYSTEM_SETTINGS_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.LOGIN_NEW_COUNTRY.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UNAUTHORIZED_ACTION.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value: {
        "email_enabled": True,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.ITEM_DELETED.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_EXPORT.value: {
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.EXPORT_APPROVED.value: {
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.NEW_BATCH.value: {
        "in_app_enabled": False,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.BATCH_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.BULK_OPERATION_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.WEB_IMPORT_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.NEW_ASSIGNMENT.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.REVIEW_NEEDED.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
}
