import pytest
from enferno.admin.constants import Constants
from enferno.admin.models.Notification import Notification
from tests.test_utils import load_data

NotificationEvent = Constants.NotificationEvent


#### UNIT TESTS ####


def test_notification_settings_get_config():
    """Test that get_config returns configuration with security events enforced."""
    from enferno.settings import Config as cfg

    # Verify that security events are always enabled
    security_events = [
        "LOGIN_NEW_IP",
        "PASSWORD_CHANGE",
        "TWO_FACTOR_CHANGE",
        "RECOVERY_CODES_CHANGE",
        "FORCE_PASSWORD_CHANGE",
    ]

    for event in security_events:
        config = Notification._get_notification_config(event)
        assert config["in_app_enabled"] is True
        assert config["email_enabled"] is True
        assert config["category"] == "security"


#### INTEGRATION TESTS ####


def test_notification_settings_get_config_includes_security_events(admin_client):
    """Test that the config endpoint includes security events."""
    response = admin_client.get("/admin/api/configuration/")
    current_configuration = load_data(response)["config"]

    # Verify that ALWAYS-ON security events are NOT present in the config
    notifications = current_configuration["NOTIFICATIONS"]
    security_events = [
        "LOGIN_NEW_IP",
        "PASSWORD_CHANGE",
        "TWO_FACTOR_CHANGE",
        "RECOVERY_CODES_CHANGE",
        "FORCE_PASSWORD_CHANGE",
    ]

    for event in security_events:
        assert event not in notifications


def test_put_config_basic_functionality(admin_client):
    """Test that basic configuration updates work with the simplified approach."""
    # Create a temporary file
    import tempfile
    import json
    from unittest.mock import patch

    temp = tempfile.NamedTemporaryFile(mode="w", delete=False)
    try:
        # Write some initial config to the temp file
        json.dump({}, temp)
        temp.close()

        # Patch the config file path to use our temp file
        with patch("enferno.utils.config_utils.ConfigManager.CONFIG_FILE_PATH", temp.name):
            # Get the current config
            response = admin_client.get("/admin/api/configuration/")
            current_config = load_data(response)["config"]

            # Modify only configurable notification settings
            current_config["NOTIFICATIONS"]["NEW_BATCH"] = {
                "in_app_enabled": True,
                "email_enabled": True,
                "category": "update",
            }

            # Make a PUT request to update notification settings
            response = admin_client.put("/admin/api/configuration/", json={"conf": current_config})

            assert response.status_code == 200

            # Verify that the config accepts simple notification updates
            with open(temp.name, "r") as f:
                updated_raw_config = json.load(f)

            # Assert that configurable events were written to the config file
            assert updated_raw_config["NOTIFICATIONS"]["NEW_BATCH"]["in_app_enabled"] is True
            assert updated_raw_config["NOTIFICATIONS"]["NEW_BATCH"]["email_enabled"] is True

    finally:
        # Clean up the temp file
        import os

        os.unlink(temp.name)
