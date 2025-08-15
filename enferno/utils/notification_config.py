"""
Notification configuration - single source of truth for notification settings.
This module prevents circular imports between settings.py and config_utils.py.
"""

from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent
NotificationCategories = Constants.NotificationCategories

# Always-on security events (not configurable by admins)
ALWAYS_ON_SECURITY_EVENTS = {
    NotificationEvent.LOGIN_NEW_IP.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.PASSWORD_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.TWO_FACTOR_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.RECOVERY_CODES_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.FORCE_PASSWORD_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
}

# Configurable notification events
NOTIFICATIONS_DEFAULT_CONFIG = {
    # Admin security events
    NotificationEvent.NEW_USER.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.UPDATE_USER.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.NEW_GROUP.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.SYSTEM_SETTINGS_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.LOGIN_NEW_COUNTRY.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.UNAUTHORIZED_ACTION.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value: {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.ITEM_DELETED.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.SECURITY.value,
    },
    NotificationEvent.NEW_EXPORT.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.EXPORT_APPROVED.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.NEW_BATCH.value: {
        "in_app_enabled": False,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.BATCH_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.BULK_OPERATION_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.WEB_IMPORT_STATUS.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.NEW_ASSIGNMENT.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
    NotificationEvent.REVIEW_NEEDED.value: {
        "in_app_enabled": True,
        "email_enabled": False,
        "category": Constants.NotificationCategories.UPDATE.value,
    },
}
