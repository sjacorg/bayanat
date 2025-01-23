import pytest

from enferno.utils.notification_settings import NotificationSettings
from tests.test_utils import load_data

# Default settings that are configurable by the user
DEFAULT_CONFIGURABLE_SETTINGS = {
    "ADMIN_CREDENTIALS_CHANGE": {
        "email_enabled": True,
        "in_app_enabled": True,
        "category": "security",
    },
    "BATCH_STATUS": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    "BULK_OPERATION_STATUS": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    "EXPORT_APPROVED": {
        "email_enabled": False,
        "category": "update",
    },
    "ITEM_DELETED": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "security",
    },
    "LOGIN_NEW_COUNTRY": {
        "email_enabled": True,
        "category": "security",
    },
    "NEW_ASSIGNMENT": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    "NEW_BATCH": {
        "email_enabled": False,
        "in_app_enabled": False,
        "category": "update",
    },
    "NEW_EXPORT": {
        "email_enabled": False,
        "category": "update",
    },
    "NEW_GROUP": {
        "email_enabled": True,
        "category": "security",
    },
    "NEW_USER": {
        "email_enabled": True,
        "category": "security",
    },
    "REVIEW_NEEDED": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    "SYSTEM_SETTINGS_CHANGE": {
        "email_enabled": True,
        "category": "security",
    },
    "UNAUTHORIZED_ACTION": {
        "email_enabled": True,
        "category": "security",
    },
    "UPDATE_USER": {
        "email_enabled": True,
        "category": "security",
    },
    "WEB_IMPORT_STATUS": {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
}

# Default settings, decorated with app-managed read-only keys and fields
DECORATED_DEFAULT_SETTINGS = {
    "LOGIN_NEW_IP": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    "PASSWORD_CHANGE": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    "TWO_FACTOR_CHANGE": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    "RECOVERY_CODES_CHANGE": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    "FORCE_PASSWORD_CHANGE": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    "NEW_USER": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "UPDATE_USER": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "NEW_GROUP": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "SYSTEM_SETTINGS_CHANGE": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "LOGIN_NEW_COUNTRY": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "UNAUTHORIZED_ACTION": {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    "ADMIN_CREDENTIALS_CHANGE": {
        "in_app_locked": False,
        "email_locked": False,
        "email_enabled": True,
        "in_app_enabled": True,
        "category": "security",
    },
    "ITEM_DELETED": {
        "in_app_locked": False,
        "email_locked": False,
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "security",
    },
    "NEW_EXPORT": {
        "in_app_locked": True,
        "in_app_enabled": True,
        "email_enabled": False,
        "email_locked": False,
        "category": "update",
    },
    "EXPORT_APPROVED": {
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    "NEW_BATCH": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": False,
        "email_enabled": False,
        "category": "update",
    },
    "BATCH_STATUS": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    "BULK_OPERATION_STATUS": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    "WEB_IMPORT_STATUS": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    "NEW_ASSIGNMENT": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    "REVIEW_NEEDED": {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
}

#### UNIT TESTS ####


def test_notification_settings_get_default_config():
    assert NotificationSettings.get_default_config() == DECORATED_DEFAULT_SETTINGS


def test_notification_settings_get_pruned_default_config():
    assert NotificationSettings.get_pruned_default_config() == DEFAULT_CONFIGURABLE_SETTINGS


def test_notification_settings_prune_custom_config():
    custom_config = DECORATED_DEFAULT_SETTINGS.copy()
    custom_event_config = {
        "in_app_enabled": True,
        "email_enabled": True,
        "category": "general",
    }
    custom_config["CUSTOM_EVENT"] = custom_event_config

    # Prune the custom config. Should only remove app-managed read-only fields.
    pruned_config = NotificationSettings.prune_read_only_settings(custom_config)

    # Check that the pruned config is equal to the default config with the custom event added.
    default_config = DEFAULT_CONFIGURABLE_SETTINGS.copy()
    default_config["CUSTOM_EVENT"] = custom_event_config
    assert pruned_config == default_config


def test_notification_settings_prune_custom_config_with_modified_read_only_fields():
    custom_config = DECORATED_DEFAULT_SETTINGS.copy()

    # Modify read-only fields to be non-default values.
    custom_config["LOGIN_NEW_IP"]["in_app_enabled"] = False
    custom_config["LOGIN_NEW_IP"]["email_enabled"] = False

    # Modify read-only fields along with configurable fields to be non-default values.
    custom_config["LOGIN_NEW_COUNTRY"]["in_app_enabled"] = False
    custom_config["LOGIN_NEW_COUNTRY"]["email_enabled"] = False

    # Prune the custom config. Should only remove app-managed read-only fields and
    # restore read-only fields to their forced values.
    pruned_config = NotificationSettings.prune_read_only_settings(custom_config)

    # Check that the pruned config restored read-only fields to their default values.
    # LOGIN_NEW_IP should have been removed because it was not configurable.
    assert "LOGIN_NEW_IP" not in pruned_config

    # LOGIN_NEW_COUNTRY in_app_enabled should have been pruned because it was read-only.
    assert "in_app_enabled" not in pruned_config["LOGIN_NEW_COUNTRY"]

    # LOGIN_NEW_COUNTRY email_enabled should retain its non-default value.
    assert pruned_config["LOGIN_NEW_COUNTRY"]["email_enabled"] == False


#### INTEGRATION TESTS ####


def test_notification_settings_decorate_app_config(admin_client):
    response = admin_client.get("/admin/api/configuration/")
    current_configuration = load_data(response)["config"]
    assert current_configuration["NOTIFICATIONS"] == NotificationSettings.get_config()


def test_put_config_with_read_only_fields(admin_client):
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

            # Modify read-only and configurable fields to be non-default values.
            current_config["NOTIFICATIONS"]["LOGIN_NEW_IP"]["in_app_enabled"] = False
            current_config["NOTIFICATIONS"]["LOGIN_NEW_IP"]["email_enabled"] = False
            current_config["NOTIFICATIONS"]["LOGIN_NEW_COUNTRY"]["in_app_enabled"] = False
            current_config["NOTIFICATIONS"]["LOGIN_NEW_COUNTRY"]["email_enabled"] = False
            current_config["NOTIFICATIONS"]["CUSTOM_EVENT"] = {
                "in_app_enabled": True,
                "email_enabled": True,
                "category": "general",
            }

            # Make a PUT request to update notification settings
            response = admin_client.put("/admin/api/configuration/", json={"conf": current_config})

            assert response.status_code == 200

            # Check that the config was updated correctly
            # Read directly from the config file as app restart is required for the new config to take effect.
            with open(temp.name, "r") as f:
                updated_raw_config = json.load(f)

            # Assert that read-only items were not written to the config file.
            assert "LOGIN_NEW_IP" not in updated_raw_config["NOTIFICATIONS"]

            # Assert that configurable fields were written to the config file.
            assert (
                updated_raw_config["NOTIFICATIONS"]["LOGIN_NEW_COUNTRY"]["email_enabled"] == False
            )
            assert "in_app_enabled" not in updated_raw_config["NOTIFICATIONS"]["LOGIN_NEW_COUNTRY"]

            # Assert that custom events were written to the config file.
            assert updated_raw_config["NOTIFICATIONS"]["CUSTOM_EVENT"]["in_app_enabled"] == True
            assert updated_raw_config["NOTIFICATIONS"]["CUSTOM_EVENT"]["email_enabled"] == True

    finally:
        # Clean up the temp file
        import os

        os.unlink(temp.name)
