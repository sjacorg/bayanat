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
            "LOGIN_NEW_IP",
            "PASSWORD_CHANGE",
            "TWO_FACTOR_CHANGE",
            "RECOVERY_CODES_CHANGE",
            "FORCE_PASSWORD_CHANGE",
        ]:
            conf.pop(event)
        # Prune locked fields and locked information
        for event in conf:
            if conf[event]["email_locked"]:
                conf[event].pop("email_enabled")
            if conf[event]["in_app_locked"]:
                conf[event].pop("in_app_enabled")
            conf[event].pop("in_app_locked")
            conf[event].pop("email_locked")
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
        conf["LOGIN_NEW_IP"] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf["PASSWORD_CHANGE"] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf["TWO_FACTOR_CHANGE"] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf["RECOVERY_CODES_CHANGE"] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        conf["FORCE_PASSWORD_CHANGE"] = {
            "in_app_enabled": True,
            "in_app_locked": True,
            "email_enabled": True,
            "email_locked": True,
            "category": "security",
        }
        # Add missing events with default values
        for configurable_event in [
            "NEW_USER",
            "UPDATE_USER",
            "NEW_GROUP",
            "SYSTEM_SETTINGS_CHANGE",
            "LOGIN_NEW_COUNTRY",
            "UNAUTHORIZED_ACTION",
            "ADMIN_CREDENTIALS_CHANGE",
            "ITEM_DELETED",
            "NEW_EXPORT",
            "EXPORT_APPROVED",
            "NEW_BATCH",
            "BATCH_STATUS",
            "BULK_OPERATION_STATUS",
            "WEB_IMPORT_STATUS",
            "NEW_ASSIGNMENT",
            "REVIEW_NEEDED",
        ]:
            if configurable_event not in conf:
                conf[configurable_event] = defaults[configurable_event]

        conf["NEW_USER"]["in_app_enabled"] = True
        conf["NEW_USER"]["in_app_locked"] = True
        conf["NEW_USER"]["email_locked"] = False
        conf["UPDATE_USER"]["in_app_enabled"] = True
        conf["UPDATE_USER"]["in_app_locked"] = True
        conf["UPDATE_USER"]["email_locked"] = False
        conf["NEW_GROUP"]["in_app_enabled"] = True
        conf["NEW_GROUP"]["in_app_locked"] = True
        conf["NEW_GROUP"]["email_locked"] = False
        conf["SYSTEM_SETTINGS_CHANGE"]["in_app_enabled"] = True
        conf["SYSTEM_SETTINGS_CHANGE"]["in_app_locked"] = True
        conf["SYSTEM_SETTINGS_CHANGE"]["email_locked"] = False
        conf["LOGIN_NEW_COUNTRY"]["in_app_enabled"] = True
        conf["LOGIN_NEW_COUNTRY"]["in_app_locked"] = True
        conf["LOGIN_NEW_COUNTRY"]["email_locked"] = False
        conf["UNAUTHORIZED_ACTION"]["in_app_enabled"] = True
        conf["UNAUTHORIZED_ACTION"]["in_app_locked"] = True
        conf["UNAUTHORIZED_ACTION"]["email_locked"] = False
        conf["ADMIN_CREDENTIALS_CHANGE"]["in_app_enabled"] = True
        conf["ADMIN_CREDENTIALS_CHANGE"]["in_app_locked"] = True
        conf["ITEM_DELETED"]["in_app_enabled"] = True
        conf["ITEM_DELETED"]["in_app_locked"] = True
        conf["ITEM_DELETED"]["email_locked"] = False
        conf["NEW_EXPORT"]["in_app_enabled"] = True
        conf["NEW_EXPORT"]["in_app_locked"] = True
        conf["NEW_EXPORT"]["email_locked"] = False
        conf["EXPORT_APPROVED"]["in_app_enabled"] = True
        conf["EXPORT_APPROVED"]["in_app_locked"] = True
        conf["EXPORT_APPROVED"]["email_locked"] = False
        conf["NEW_BATCH"]["in_app_locked"] = False
        conf["NEW_BATCH"]["email_locked"] = False
        conf["BATCH_STATUS"]["in_app_locked"] = False
        conf["BATCH_STATUS"]["email_locked"] = False
        conf["BULK_OPERATION_STATUS"]["in_app_locked"] = False
        conf["BULK_OPERATION_STATUS"]["email_locked"] = False
        conf["WEB_IMPORT_STATUS"]["in_app_locked"] = False
        conf["WEB_IMPORT_STATUS"]["email_locked"] = False
        conf["NEW_ASSIGNMENT"]["in_app_locked"] = False
        conf["NEW_ASSIGNMENT"]["email_locked"] = False
        conf["REVIEW_NEEDED"]["in_app_locked"] = False
        conf["REVIEW_NEEDED"]["email_locked"] = False

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
