from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent


class NotificationSettings:
    _config = None

    @staticmethod
    def _init_config() -> dict:
        """
        Initialize the notification config with values from the config file
        and append/override with read-only settings managed by the app.
        """
        from enferno.settings import manager

        conf = manager.get_config("NOTIFICATIONS")
        conf = NotificationSettings._enforce_locked_settings(conf)
        return conf

    @staticmethod
    def prune_read_only_settings(conf: dict | None = None) -> dict:
        """
        Prune app-managed read-only fields from a notification config dictionary.
        If no config is provided, generates a valid default config without app-managed read-only fields.
        """
        conf = NotificationSettings._enforce_locked_settings(conf)

        # Prune read-only settings
        # Prune security events
        for event in [
            NotificationEvent.LOGIN_NEW_IP.value,
            NotificationEvent.PASSWORD_CHANGE.value,
            NotificationEvent.TWO_FACTOR_CHANGE.value,
            NotificationEvent.RECOVERY_CODES_CHANGE.value,
            NotificationEvent.FORCE_PASSWORD_CHANGE.value,
        ]:
            conf.pop(event)
        # Prune locked fields and locked information
        for event in conf:
            if event not in NotificationEvent.__members__:
                continue
            if conf[event]["email_locked"]:
                conf[event].pop("email_enabled")
            if conf[event]["in_app_locked"]:
                conf[event].pop("in_app_enabled")
            conf[event].pop("email_locked")
            conf[event].pop("in_app_locked")
        return conf

    @staticmethod
    def _enforce_locked_settings(conf: dict | None = None) -> dict:
        """
        Enforces app-managed read-only settings on a notification config dictionary.
        If no config is provided, generates a valid default config with app-managed read-only fields.
        """
        from enferno.settings import manager

        if not conf:
            conf = {}
        defaults = manager.get_default_config("NOTIFICATIONS")
        # Always-On Security Events
        # Override these in all cases
        conf[NotificationEvent.LOGIN_NEW_IP.value] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf[NotificationEvent.PASSWORD_CHANGE.value] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf[NotificationEvent.TWO_FACTOR_CHANGE.value] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf[NotificationEvent.RECOVERY_CODES_CHANGE.value] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf[NotificationEvent.FORCE_PASSWORD_CHANGE.value] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        # Add missing events with default values
        for configurable_event in [
            NotificationEvent.NEW_USER.value,
            NotificationEvent.UPDATE_USER.value,
            NotificationEvent.NEW_GROUP.value,
            NotificationEvent.SYSTEM_SETTINGS_CHANGE.value,
            NotificationEvent.LOGIN_NEW_COUNTRY.value,
            NotificationEvent.UNAUTHORIZED_ACTION.value,
            NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value,
            NotificationEvent.ITEM_DELETED.value,
            NotificationEvent.NEW_EXPORT.value,
            NotificationEvent.EXPORT_APPROVED.value,
            NotificationEvent.NEW_BATCH.value,
            NotificationEvent.BATCH_STATUS.value,
            NotificationEvent.BULK_OPERATION_STATUS.value,
            NotificationEvent.WEB_IMPORT_STATUS.value,
            NotificationEvent.NEW_ASSIGNMENT.value,
            NotificationEvent.REVIEW_NEEDED.value,
        ]:
            if configurable_event not in conf:
                conf[configurable_event] = defaults[configurable_event]

        conf[NotificationEvent.NEW_USER.value]["in_app_enabled"] = True
        conf[NotificationEvent.NEW_USER.value]["in_app_locked"] = True
        conf[NotificationEvent.NEW_USER.value]["email_locked"] = False
        conf[NotificationEvent.UPDATE_USER.value]["in_app_enabled"] = True
        conf[NotificationEvent.UPDATE_USER.value]["in_app_locked"] = True
        conf[NotificationEvent.UPDATE_USER.value]["email_locked"] = False
        conf[NotificationEvent.NEW_GROUP.value]["in_app_enabled"] = True
        conf[NotificationEvent.NEW_GROUP.value]["in_app_locked"] = True
        conf[NotificationEvent.NEW_GROUP.value]["email_locked"] = False
        conf[NotificationEvent.SYSTEM_SETTINGS_CHANGE.value]["in_app_enabled"] = True
        conf[NotificationEvent.SYSTEM_SETTINGS_CHANGE.value]["in_app_locked"] = True
        conf[NotificationEvent.SYSTEM_SETTINGS_CHANGE.value]["email_locked"] = False
        conf[NotificationEvent.LOGIN_NEW_COUNTRY.value]["in_app_enabled"] = True
        conf[NotificationEvent.LOGIN_NEW_COUNTRY.value]["in_app_locked"] = True
        conf[NotificationEvent.LOGIN_NEW_COUNTRY.value]["email_locked"] = False
        conf[NotificationEvent.UNAUTHORIZED_ACTION.value]["in_app_enabled"] = True
        conf[NotificationEvent.UNAUTHORIZED_ACTION.value]["in_app_locked"] = True
        conf[NotificationEvent.UNAUTHORIZED_ACTION.value]["email_locked"] = False
        conf[NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value]["in_app_locked"] = False
        conf[NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value]["email_locked"] = False
        conf[NotificationEvent.ITEM_DELETED.value]["in_app_locked"] = False
        conf[NotificationEvent.ITEM_DELETED.value]["email_locked"] = False
        conf[NotificationEvent.NEW_EXPORT.value]["in_app_enabled"] = True
        conf[NotificationEvent.NEW_EXPORT.value]["in_app_locked"] = True
        conf[NotificationEvent.NEW_EXPORT.value]["email_locked"] = False
        conf[NotificationEvent.EXPORT_APPROVED.value]["in_app_enabled"] = True
        conf[NotificationEvent.EXPORT_APPROVED.value]["in_app_locked"] = True
        conf[NotificationEvent.EXPORT_APPROVED.value]["email_locked"] = False
        conf[NotificationEvent.NEW_BATCH.value]["in_app_locked"] = False
        conf[NotificationEvent.NEW_BATCH.value]["email_locked"] = False
        conf[NotificationEvent.BATCH_STATUS.value]["in_app_locked"] = False
        conf[NotificationEvent.BATCH_STATUS.value]["email_locked"] = False
        conf[NotificationEvent.BULK_OPERATION_STATUS.value]["in_app_locked"] = False
        conf[NotificationEvent.BULK_OPERATION_STATUS.value]["email_locked"] = False
        conf[NotificationEvent.WEB_IMPORT_STATUS.value]["in_app_locked"] = False
        conf[NotificationEvent.WEB_IMPORT_STATUS.value]["email_locked"] = False
        conf[NotificationEvent.NEW_ASSIGNMENT.value]["in_app_locked"] = False
        conf[NotificationEvent.NEW_ASSIGNMENT.value]["email_locked"] = False
        conf[NotificationEvent.REVIEW_NEEDED.value]["in_app_locked"] = False
        conf[NotificationEvent.REVIEW_NEEDED.value]["email_locked"] = False

        return conf

    @staticmethod
    def get_config() -> dict:
        """
        Get the current notification configuration. Returned dictionary includes app-managed read-only fields,
        which are not intended to be modified by the user (this configuration should not be written to file).
        Use `get_pruned_config()` to get a dictionary without app-managed read-only fields or use
        `prune_read_only_settings()` with the returned dictionary.
        """
        if not NotificationSettings._config:
            NotificationSettings._config = NotificationSettings._init_config()
        return NotificationSettings._config

    @staticmethod
    def get_default_config() -> dict:
        """
        Get the default notification configuration. Returned dictionary includes app-managed read-only fields,
        which are not intended to be modified by the user (this configuration should not be written to file).
        Use `get_pruned_default_config()` to get a dictionary without app-managed read-only fields or use
        `prune_read_only_settings()` with the returned dictionary.
        """
        return NotificationSettings._enforce_locked_settings()

    @staticmethod
    def get_pruned_default_config() -> dict:
        """
        Get the default notification configuration with read-only settings pruned.
        This configuration can be written to user-facing configuration files.
        """
        return NotificationSettings.prune_read_only_settings()

    @staticmethod
    def get_pruned_config() -> dict:
        """
        Get the current notification configuration with read-only settings pruned.
        This configuration can be written to user-facing configuration files.
        """
        return NotificationSettings.prune_read_only_settings(NotificationSettings.get_config())
