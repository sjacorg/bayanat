import pytest
from pydantic import ValidationError

from enferno.admin.validation.models import (
    BulletinValidationModel,
    DefaultMapCenterModel,
    FullConfigValidationModel,
    UserValidationModel,
)


class TestStringValidations:
    def test_min_length_validation(self):
        """Test that fields with min_length=1 reject empty strings"""

        # Test BulletinValidationModel title constraint
        with pytest.raises(ValidationError) as exc_info:
            BulletinValidationModel(
                title="",  # Empty string should fail
                comments="Valid comment",
                source_link="http://example.com",
            )
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test UserValidationModel username constraint
        with pytest.raises(ValidationError) as exc_info:
            UserValidationModel(
                username="", name="Valid Name", active=True  # Empty string should fail
            )
        assert "String should have at least 1 character" in str(exc_info.value)


class TestNumericValidations:
    def test_map_center_constraints(self):
        """Test that DefaultMapCenterModel enforces valid lat/lng ranges"""

        # Test valid coordinates
        model = DefaultMapCenterModel(lat=45.0, lng=90.0)
        assert model.lat == 45.0
        assert model.lng == 90.0

        # Test invalid latitude
        with pytest.raises(ValidationError) as exc_info:
            DefaultMapCenterModel(lat=91.0, lng=0.0)  # Latitude > 90
        assert "Input should be less than or equal to 90" in str(exc_info.value)

        # Test invalid longitude
        with pytest.raises(ValidationError) as exc_info:
            DefaultMapCenterModel(lat=0.0, lng=181.0)  # Longitude > 180
        assert "Input should be less than or equal to 180" in str(exc_info.value)


class TestListValidations:
    def test_config_list_constraints(self):
        """Test that list item constraints are enforced in FullConfigValidationModel"""

        # Base valid configuration with all required fields
        base_config = {
            # Required security settings
            "SECURITY_TWO_FACTOR_REQUIRED": True,
            "SECURITY_PASSWORD_LENGTH_MIN": 8,
            "SECURITY_ZXCVBN_MINIMUM_SCORE": 3,
            "SESSION_RETENTION_PERIOD": 30,
            "SECURITY_FRESHNESS": 60,
            "SECURITY_FRESHNESS_GRACE_PERIOD": 10,
            # Required system settings
            "FILESYSTEM_LOCAL": True,
            "ACCESS_CONTROL_RESTRICTIVE": True,
            "AC_USERS_CAN_RESTRICT_NEW": False,
            "ETL_TOOL": False,
            "SHEET_IMPORT": False,
            "WEB_IMPORT": False,
            "BABEL_DEFAULT_LOCALE": "en",
            "OCR_ENABLED": False,
            "LOCATIONS_INCLUDE_POSTAL_CODE": False,
            "GOOGLE_MAPS_API_KEY": "lorem ipsum dolor sit amet. consectetur adipiscing elit.",
            # Required authentication settings
            "DISABLE_MULTIPLE_SESSIONS": False,
            "RECAPTCHA_ENABLED": False,
            "GOOGLE_OAUTH_ENABLED": False,
            "GOOGLE_DISCOVERY_URL": "https://accounts.google.com/.well-known/openid-configuration",
            # Required tool settings
            "MEDIA_UPLOAD_MAX_FILE_SIZE": 1.0,
            "ETL_PATH_IMPORT": False,
            "DEDUP_TOOL": False,
            "MAPS_API_ENDPOINT": "https://maps.example.com",
            "EXPORT_TOOL": True,
            "EXPORT_DEFAULT_EXPIRY": 7,
            "ACTIVITIES_RETENTION": 30,
            "GEO_MAP_DEFAULT_CENTER": {"lat": 0, "lng": 0},
            "ADV_ANALYSIS": False,
            # Required activity settings
            "ACTIVITIES": {"APPROVE": False},
            # Test-specific settings
            "ITEMS_PER_PAGE_OPTIONS": [10, 20, 30],
            "VIDEO_RATES": [0.5, 1.0, 1.5],
            "TRANSCRIPTION_ENABLED": False,
        }

        # Test valid configuration
        config = FullConfigValidationModel(**base_config)
        assert config.ITEMS_PER_PAGE_OPTIONS == [10, 20, 30]
        assert config.VIDEO_RATES == [0.5, 1.0, 1.5]

        # Test invalid items per page options (negative value)
        invalid_page_config = base_config.copy()
        invalid_page_config["ITEMS_PER_PAGE_OPTIONS"] = [-10, 20, 30]
        with pytest.raises(ValidationError) as exc_info:
            FullConfigValidationModel(**invalid_page_config)
        assert "All items per page options must be greater than 0" in str(exc_info.value)

        # Test invalid video rates (zero value)
        invalid_rates_config = base_config.copy()
        invalid_rates_config["VIDEO_RATES"] = [0.0, 1.0, 1.5]
        with pytest.raises(ValidationError) as exc_info:
            FullConfigValidationModel(**invalid_rates_config)
        assert "All video rates must be greater than 0" in str(exc_info.value)
