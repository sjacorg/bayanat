from enferno.admin.constants import Constants

NotificationEvent = Constants.NotificationEvent


class NotificationSettings:
    @staticmethod
    def get_config() -> dict:
        """Get notification configuration with security events always enabled."""
        from enferno.settings import manager

        config = manager.get_config("NOTIFICATIONS")

        # Security events are always enabled and override any user config
        security_events = [
            NotificationEvent.LOGIN_NEW_IP.value,
            NotificationEvent.PASSWORD_CHANGE.value,
            NotificationEvent.TWO_FACTOR_CHANGE.value,
            NotificationEvent.RECOVERY_CODES_CHANGE.value,
            NotificationEvent.FORCE_PASSWORD_CHANGE.value,
        ]

        for event in security_events:
            config[event] = {"in_app_enabled": True, "email_enabled": True, "category": "security"}

        return config
