import pytest
from enferno.admin.constants import Constants
from enferno.utils.notification_settings import NotificationSettings
from tests.test_utils import load_data

NotificationEvent = Constants.NotificationEvent

# Default settings that are configurable by the user
DEFAULT_CONFIGURABLE_SETTINGS = {
    NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value: {
        "email_enabled": True,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.BATCH_STATUS.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.BULK_OPERATION_STATUS.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.EXPORT_APPROVED.value: {
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.ITEM_DELETED.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.LOGIN_NEW_COUNTRY.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_ASSIGNMENT.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.NEW_BATCH.value: {
        "email_enabled": False,
        "in_app_enabled": False,
        "category": "update",
    },
    NotificationEvent.NEW_EXPORT.value: {
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.NEW_GROUP.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_USER.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.REVIEW_NEEDED.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.SYSTEM_SETTINGS_CHANGE.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UNAUTHORIZED_ACTION.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UPDATE_USER.value: {
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.WEB_IMPORT_STATUS.value: {
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
}

# Default settings, decorated with app-managed read-only keys and fields
DECORATED_DEFAULT_SETTINGS = {
    NotificationEvent.LOGIN_NEW_IP.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    NotificationEvent.PASSWORD_CHANGE.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    NotificationEvent.TWO_FACTOR_CHANGE.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    NotificationEvent.RECOVERY_CODES_CHANGE.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    NotificationEvent.FORCE_PASSWORD_CHANGE.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_enabled": True,
        "email_locked": True,
        "category": "security",
    },
    NotificationEvent.NEW_USER.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UPDATE_USER.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_GROUP.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.SYSTEM_SETTINGS_CHANGE.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.LOGIN_NEW_COUNTRY.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.UNAUTHORIZED_ACTION.value: {
        "in_app_enabled": True,
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": True,
        "category": "security",
    },
    NotificationEvent.ADMIN_CREDENTIALS_CHANGE.value: {
        "in_app_locked": False,
        "email_locked": False,
        "email_enabled": True,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.ITEM_DELETED.value: {
        "in_app_locked": False,
        "email_locked": False,
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "security",
    },
    NotificationEvent.NEW_EXPORT.value: {
        "in_app_locked": True,
        "in_app_enabled": True,
        "email_enabled": False,
        "email_locked": False,
        "category": "update",
    },
    NotificationEvent.EXPORT_APPROVED.value: {
        "in_app_locked": True,
        "email_locked": False,
        "email_enabled": False,
        "in_app_enabled": True,
        "category": "update",
    },
    NotificationEvent.NEW_BATCH.value: {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": False,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.BATCH_STATUS.value: {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.BULK_OPERATION_STATUS.value: {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.WEB_IMPORT_STATUS.value: {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.NEW_ASSIGNMENT.value: {
        "in_app_locked": False,
        "email_locked": False,
        "in_app_enabled": True,
        "email_enabled": False,
        "category": "update",
    },
    NotificationEvent.REVIEW_NEEDED.value: {
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
