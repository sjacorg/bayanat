from unittest.mock import patch
import pytest
from enferno.user.models import User
from enferno.admin.models import (
    AtobInfo,
    BtobInfo,
    AtoaInfo,
    ItobInfo,
    ItoaInfo,
    ItoiInfo,
    Country,
    MediaCategory,
    GeoLocationType,
    ClaimedViolation,
    Eventtype,
    PotentialViolation,
)


@pytest.fixture(scope="function")
def clean_imported_data(session_uninitialized):
    """
    Clean up the database after the tests are run.
    """
    items = [
        Eventtype,
        PotentialViolation,
        ClaimedViolation,
        AtobInfo,
        BtobInfo,
        AtoaInfo,
        ItobInfo,
        ItoaInfo,
        ItoiInfo,
        Country,
        MediaCategory,
        GeoLocationType,
    ]

    for item in items:
        session_uninitialized.query(item).delete()
    session_uninitialized.commit()


def test_setup_wizard_redirect(uninitialized_app, setup_db_uninitialized):
    """Test that the setup wizard is redirected to when the app is not initialized."""
    client = uninitialized_app.test_client()
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "setup_wizard" in response.location


def test_setup_wizard_admin_user_check(uninitialized_app, setup_db_uninitialized):
    """Test that the setup wizard admin user check works."""
    client = uninitialized_app.test_client()
    response = client.get("/api/check-admin")
    assert response.status_code == 200
    assert response.json == {"status": "not_found", "message": "No admin user found"}


def test_setup_wizard_create_admin_user(uninitialized_app, session_uninitialized):
    """Test that the setup wizard admin user creation works."""
    client = uninitialized_app.test_client()
    response = client.post(
        "/api/create-admin", json={"username": "testAdmin", "password": "password"}
    )
    assert response.status_code == 201
    assert response.json == {"message": "Admin user installed successfully"}

    admin = User.query.filter(User.username == "testAdmin").first()
    assert admin is not None
    assert admin.username == "testAdmin"


test_roles = [
    ("uninitialized_admin_client", 200),
    ("uninitialized_anonymous_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", test_roles)
def test_setup_wizard_check_data_imported(
    uninitialized_app, session_uninitialized, client_fixture, expected_status, request
):
    """Test that the setup wizard check data imported works."""
    client = request.getfixturevalue(client_fixture)
    response = client.get("/api/check-data-imported")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json == {
            "status": "not_imported",
            "message": "Default data has not been imported",
        }


@pytest.mark.parametrize("client_fixture, expected_status", test_roles)
def test_setup_wizard_import_data(
    clean_imported_data,
    uninitialized_app,
    session_uninitialized,
    client_fixture,
    expected_status,
    request,
):
    """Test that the setup wizard import data works."""
    client = request.getfixturevalue(client_fixture)
    assert session_uninitialized.query(Eventtype).first() is None
    response = client.post("/api/import-data")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert session_uninitialized.query(Eventtype).first() is not None


@pytest.mark.parametrize("client_fixture, expected_status", test_roles)
def test_setup_wizard_get_default_config(
    uninitialized_app, session_uninitialized, client_fixture, expected_status, request
):
    """Test that the setup wizard get default config works."""
    required_keys = [
        "FILESYSTEM_LOCAL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "S3_BUCKET",
        "AWS_REGION",
        "BABEL_DEFAULT_LOCALE",
        "ACCESS_CONTROL_RESTRICTIVE",
        "AC_USERS_CAN_RESTRICT_NEW",
        "ACTIVITIES_RETENTION",
        "EXPORT_DEFAULT_EXPIRY",
        "SESSION_RETENTION_PERIOD",
        "ETL_TOOL",
        "SHEET_IMPORT",
        "WEB_IMPORT",
        "EXPORT_TOOL",
        "GOOGLE_MAPS_API_KEY",
        "GEO_MAP_DEFAULT_CENTER",
        "SECURITY_TWO_FACTOR_REQUIRED",
        "SECURITY_PASSWORD_LENGTH_MIN",
        "SECURITY_ZXCVBN_MINIMUM_SCORE",
        "SESSION_RETENTION_PERIOD",
    ]
    client = request.getfixturevalue(client_fixture)
    response = client.get("/api/default-config")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert set(response.json.keys()) == set(required_keys)


@pytest.mark.parametrize("client_fixture, expected_status", test_roles)
def test_setup_wizard_complete_setup(
    uninitialized_app, session_uninitialized, client_fixture, expected_status, request
):
    """Test that the setup wizard complete setup works."""
    from tempfile import NamedTemporaryFile
    import json

    temp = NamedTemporaryFile("w", delete=False)
    try:
        json.dump({}, temp)
        temp.close()
        with patch("enferno.utils.config_utils.ConfigManager.CONFIG_FILE_PATH", temp.name):
            config = {
                "SECURITY_TWO_FACTOR_REQUIRED": True,
                "SECURITY_PASSWORD_LENGTH_MIN": 8,
                "SECURITY_ZXCVBN_MINIMUM_SCORE": 4,
                "SESSION_RETENTION_PERIOD": 1,
                "FILESYSTEM_LOCAL": True,
                "ACCESS_CONTROL_RESTRICTIVE": True,
                "AC_USERS_CAN_RESTRICT_NEW": True,
                "ETL_TOOL": True,
                "SHEET_IMPORT": True,
                "WEB_IMPORT": True,
                "BABEL_DEFAULT_LOCALE": "en",
                "GOOGLE_MAPS_API_KEY": "asdasdasd123sd54aasd135asd135asd135",
                "GEO_MAP_DEFAULT_CENTER": {"lat": 0, "lng": 0},
                "EXPORT_TOOL": True,
                "EXPORT_DEFAULT_EXPIRY": 1,
                "ACTIVITIES_RETENTION": 1,
            }
            client = request.getfixturevalue(client_fixture)
            response = client.put("/api/complete-setup/", json={"conf": config})
            assert response.status_code == expected_status
            if expected_status == 200:
                assert response.text == "Configuration Saved Successfully"
    finally:
        import os

        os.unlink(temp.name)


def test_setup_wizard_not_accessible_after_setup(setup_completed_app):
    """Test that the setup wizard is not accessible after setup."""
    client = setup_completed_app.test_client()
    response = client.get("/setup_wizard")
    assert response.status_code == 404
