"""
Notification configuration - single source of truth for notification settings.
This module prevents circular imports between settings.py and config_utils.py.
"""

from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent

# Always-on security events (not configurable by admins)
ALWAYS_ON_SECURITY_EVENTS = {
    NotificationEvent.LOGIN_NEW_IP.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.PASSWORD_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.TWO_FACTOR_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.RECOVERY_CODES_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.FORCE_PASSWORD_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
}

# Configurable notification events
NOTIFICATIONS_CONFIG = {
    # Admin security events
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
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.EXPORT_APPROVED.value: {
        "email_enabled": False,
        "in_app_enabled": True,
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
