"""
Security-related tests: rate limiting, setup wizard, input validation,
sanitized fields, username/email validation, config validation models,
and dynamic field search utils.
"""

import json
import os
import tempfile

import pytest
from pydantic import ValidationError
from unittest.mock import patch


class TestRateLimiting:
    """Test rate limiting on the CSRF endpoint."""

    def test_csrf_rate_limit(self):
        from enferno.app import create_app
        from enferno.settings import TestConfig as cfg

        fresh_app = create_app(cfg)
        with fresh_app.app_context():
            from enferno.extensions import limiter

            limiter.reset()

            client = fresh_app.test_client()
            # First 15 requests should succeed
            for i in range(15):
                resp = client.get("/csrf")
                if i == 0:
                    assert resp.status_code == 200
                    assert "csrf_token" in (resp.json or {})

            # 16th should be rate limited
            resp = client.get("/csrf")
            assert resp.status_code == 429


class TestSetupWizard:
    """Test the setup wizard flow."""

    def test_uninitialized_registers_setup_blueprint(self):
        """When SETUP_COMPLETE is None, the setup blueprint should be registered."""
        from enferno.app import create_app
        from enferno.settings import TestConfig as cfg

        with patch.object(cfg, "SETUP_COMPLETE", None):
            uninit_app = create_app(cfg)
            assert "setup" in uninit_app.blueprints

    def test_initialized_skips_setup_blueprint(self):
        """When SETUP_COMPLETE is True, setup blueprint should NOT be registered."""
        from enferno.app import create_app
        from enferno.settings import TestConfig as cfg

        with patch.object(cfg, "SETUP_COMPLETE", True):
            init_app = create_app(cfg)
            assert "setup" not in init_app.blueprints

    def test_setup_routes_exist_when_uninitialized(self):
        from enferno.app import create_app
        from enferno.settings import TestConfig as cfg

        with patch.object(cfg, "SETUP_COMPLETE", None):
            uninit_app = create_app(cfg)
            rules = [r.rule for r in uninit_app.url_map.iter_rules()]
            assert "/setup_wizard" in rules
            assert "/api/check-admin" in rules
            assert "/api/create-admin" in rules


class TestInputValidation:
    """Test WebAuthn device name validation."""

    def test_valid_plain_text(self):
        from enferno.utils.validation_utils import validate_webauthn_device_name

        validate_webauthn_device_name("My Phone")
        validate_webauthn_device_name("iPhone 15")

    def test_html_tags_rejected(self):
        from enferno.utils.validation_utils import validate_webauthn_device_name
        from wtforms.validators import ValidationError

        with pytest.raises(ValidationError, match="HTML tags"):
            validate_webauthn_device_name("<script>alert('xss')</script>")

    def test_html_entities_rejected(self):
        from enferno.utils.validation_utils import validate_webauthn_device_name
        from wtforms.validators import ValidationError

        with pytest.raises(ValidationError, match="HTML entities"):
            validate_webauthn_device_name("&lt;script&gt;")

    def test_too_long_rejected(self):
        from enferno.utils.validation_utils import validate_webauthn_device_name
        from wtforms.validators import ValidationError

        with pytest.raises(ValidationError, match="too long"):
            validate_webauthn_device_name("A" * 65)

    def test_empty_rejected(self):
        from enferno.utils.validation_utils import validate_webauthn_device_name
        from wtforms.validators import ValidationError

        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_webauthn_device_name("")


# =========================================================================
# SETUP WIZARD FULL FLOW (uses uninitialized app fixtures)
# =========================================================================


class TestSetupWizardFullFlow:
    """Full setup wizard integration tests."""

    def test_redirect_to_setup(self, uninitialized_app, setup_db_uninitialized):
        client = uninitialized_app.test_client()
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert "setup_wizard" in resp.location

    def test_check_admin_not_found(self, uninitialized_app, setup_db_uninitialized):
        client = uninitialized_app.test_client()
        resp = client.get("/api/check-admin")
        assert resp.status_code == 200
        assert resp.json["data"] == {"status": "not_found"}
        assert resp.json["message"] == "No admin user found"

    def test_create_admin_user(self, uninitialized_app, session_uninitialized):
        from enferno.user.models import User

        client = uninitialized_app.test_client()
        resp = client.post(
            "/api/create-admin",
            json={"username": "testAdmin", "password": "password"},
        )
        assert resp.status_code == 201
        assert resp.json["message"] == "Admin user installed successfully"
        assert resp.json["data"]["item"]["username"] == "testAdmin"
        admin = User.query.filter(User.username == "testAdmin").first()
        assert admin is not None

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("uninitialized_admin_client", 200),
            ("uninitialized_anonymous_client", 403),
        ],
    )
    def test_check_data_imported(
        self,
        request,
        uninitialized_app,
        session_uninitialized,
        client_fixture,
        expected,
    ):
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/api/check-data-imported")
        assert resp.status_code == expected
        if expected == 200:
            assert resp.json["data"] == {"status": "not_imported"}

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("uninitialized_admin_client", 200),
            ("uninitialized_anonymous_client", 403),
        ],
    )
    def test_import_data(
        self,
        request,
        uninitialized_app,
        session_uninitialized,
        client_fixture,
        expected,
    ):
        from enferno.admin.models import Eventtype

        # Clean up imported data first
        items_to_clean = [
            Eventtype,
        ]
        for item_cls in items_to_clean:
            session_uninitialized.query(item_cls).delete()
        session_uninitialized.commit()

        assert session_uninitialized.query(Eventtype).first() is None
        client = request.getfixturevalue(client_fixture)
        resp = client.post("/api/import-data")
        assert resp.status_code == expected
        if expected == 200:
            assert session_uninitialized.query(Eventtype).first() is not None

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("uninitialized_admin_client", 200),
            ("uninitialized_anonymous_client", 403),
        ],
    )
    def test_get_default_config(
        self,
        request,
        uninitialized_app,
        session_uninitialized,
        client_fixture,
        expected,
    ):
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
        resp = client.get("/api/default-config")
        assert resp.status_code == expected
        if expected == 200:
            assert set(resp.json["data"].keys()) == set(required_keys)

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("uninitialized_admin_client", 200),
            ("uninitialized_anonymous_client", 403),
        ],
    )
    def test_complete_setup(
        self,
        request,
        uninitialized_app,
        session_uninitialized,
        client_fixture,
        expected,
    ):
        temp = tempfile.NamedTemporaryFile("w", delete=False)
        try:
            json.dump({}, temp)
            temp.close()
            with patch(
                "enferno.utils.config_utils.ConfigManager.CONFIG_FILE_PATH",
                temp.name,
            ):
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
                resp = client.put("/api/complete-setup/", json={"conf": config})
                assert resp.status_code == expected
                if expected == 200:
                    assert resp.json["message"] == "Configuration Saved Successfully"
        finally:
            os.unlink(temp.name)

    def test_not_accessible_after_setup(self, setup_completed_app):
        client = setup_completed_app.test_client()
        resp = client.get("/setup_wizard")
        assert resp.status_code == 404


# =========================================================================
# SANITIZED FIELD TESTS
# =========================================================================


class TestSanitizedField:
    def test_sanitized_field_is_str(self):
        from enferno.admin.validation.models import BulletinValidationModel
        from tests.factories import BulletinFactory

        bulletin = BulletinFactory()
        bulletin.description = "Hello, World!"
        model = BulletinValidationModel(**bulletin.to_dict())
        assert model.description == "Hello, World!"
        bulletin.description = 5
        with pytest.raises(ValidationError):
            BulletinValidationModel(**bulletin.to_dict())

    def test_sanitized_field_with_html(self):
        from enferno.admin.validation.models import BulletinValidationModel
        from tests.factories import BulletinFactory

        bulletin = BulletinFactory()
        bulletin.description = "<script>alert('Hello, World!');</script>"
        model = BulletinValidationModel(**bulletin.to_dict())
        assert model.description == "alert('Hello, World!');"

    def test_sanitized_field_with_allowed_tags(self):
        from enferno.admin.validation.models import BulletinValidationModel
        from tests.factories import BulletinFactory

        bulletin = BulletinFactory()
        bulletin.description = "<span>Hello, World!</span>"
        model = BulletinValidationModel(**bulletin.to_dict())
        assert model.description == "<span>Hello, World!</span>"


# =========================================================================
# USERNAME / EMAIL VALIDATION
# =========================================================================


class TestUsernameValidation:
    def test_valid_usernames(self):
        from enferno.utils.validation_utils import validate_username_constraints

        valid = [
            "user123",
            "testuser",
            "myusername",
            "USER123",
            "TestUser123",
        ]
        for username in valid:
            validate_username_constraints(username)

    def test_invalid_unicode_usernames(self):
        from enferno.utils.validation_utils import validate_username_constraints

        invalid = [
            "用户123",
            "пользователь",
            "مستخدم",
            "üser123",
        ]
        for username in invalid:
            with pytest.raises(ValueError, match="Username can only contain letters and numbers"):
                validate_username_constraints(username)

    def test_invalid_special_chars(self):
        from enferno.utils.validation_utils import validate_username_constraints

        invalid = [
            "user@example",
            "test.user",
            "user+name",
            "user_name",
            "user-name",
            "user name",
        ]
        for username in invalid:
            with pytest.raises(ValueError):
                validate_username_constraints(username)

    def test_empty_username(self):
        from enferno.utils.validation_utils import validate_username_constraints

        with pytest.raises(ValueError, match="Username cannot be empty"):
            validate_username_constraints("")
        with pytest.raises(ValueError, match="Username cannot be empty"):
            validate_username_constraints("   ")

    def test_whitespace_username(self):
        from enferno.utils.validation_utils import validate_username_constraints

        with pytest.raises(
            ValueError,
            match="Username cannot contain leading or trailing whitespace",
        ):
            validate_username_constraints(" user123")
        with pytest.raises(
            ValueError,
            match="Username cannot contain leading or trailing whitespace",
        ):
            validate_username_constraints("user123 ")

    @pytest.mark.parametrize(
        "url,username,error_message,field,is_checkuser",
        [
            (
                "/admin/api/checkuser/",
                "a",
                "String should have at least 4 characters",
                "item",
                True,
            ),
            (
                "/admin/api/user/",
                "a",
                "String should have at least 4 characters",
                "item.username",
                False,
            ),
            (
                "/admin/api/checkuser/",
                "a" * 256,
                "Username is too long (maximum 32 characters)",
                "item",
                True,
            ),
            (
                "/admin/api/user/",
                "a" * 256,
                "Username is too long (maximum 32 characters)",
                "item.username",
                False,
            ),
        ],
    )
    def test_username_length_validation(
        self,
        request,
        session,
        url,
        username,
        error_message,
        field,
        is_checkuser,
    ):
        client = request.getfixturevalue("admin_client")
        if is_checkuser:
            payload = username
        else:
            payload = {
                "username": username,
                "email": "test@example.com",
                "name": "Test User",
                "active": True,
            }
        resp = client.post(url, json={"item": payload})
        assert resp.status_code == 400
        assert "errors" in resp.json
        assert field in resp.json["errors"]
        assert error_message in resp.json["errors"][field]


class TestEmailValidation:
    def test_valid_emails(self):
        from enferno.utils.validation_utils import validate_email_format

        valid = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.net",
            "test123@test-domain.com",
        ]
        for email in valid:
            result = validate_email_format(email).normalized
            assert "@" in result

    def test_invalid_emails(self):
        from enferno.utils.validation_utils import validate_email_format
        from wtforms.validators import ValidationError as WTFValidationError

        invalid = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
        ]
        for email in invalid:
            with pytest.raises(WTFValidationError, match="Invalid email format"):
                validate_email_format(email)

    def test_empty_email(self):
        from enferno.utils.validation_utils import validate_email_format
        from wtforms.validators import ValidationError as WTFValidationError

        with pytest.raises(WTFValidationError, match="Email cannot be empty"):
            validate_email_format("")
        with pytest.raises(WTFValidationError, match="Email cannot be empty"):
            validate_email_format("   ")

    def test_email_normalization(self):
        from enferno.utils.validation_utils import validate_email_format

        email = "  Test.Email@EXAMPLE.COM  "
        result = validate_email_format(email).normalized
        assert result.endswith("@example.com")


# =========================================================================
# VALIDATION MODELS - LIST CONSTRAINTS
# =========================================================================


class TestValidationModels:
    def test_config_list_constraints(self):
        from enferno.admin.validation.models import FullConfigValidationModel

        base_config = {
            "SECURITY_TWO_FACTOR_REQUIRED": True,
            "SECURITY_PASSWORD_LENGTH_MIN": 8,
            "SECURITY_ZXCVBN_MINIMUM_SCORE": 3,
            "SESSION_RETENTION_PERIOD": 30,
            "SECURITY_FRESHNESS": 60,
            "SECURITY_FRESHNESS_GRACE_PERIOD": 10,
            "FILESYSTEM_LOCAL": True,
            "ACCESS_CONTROL_RESTRICTIVE": True,
            "AC_USERS_CAN_RESTRICT_NEW": False,
            "ETL_TOOL": False,
            "SHEET_IMPORT": False,
            "WEB_IMPORT": False,
            "BABEL_DEFAULT_LOCALE": "en",
            "OCR_ENABLED": False,
            "LOCATIONS_INCLUDE_POSTAL_CODE": False,
            "GOOGLE_MAPS_API_KEY": "AIzaSyA_fake_test_key_1234567890ab",
            "DISABLE_MULTIPLE_SESSIONS": False,
            "RECAPTCHA_ENABLED": False,
            "GOOGLE_OAUTH_ENABLED": False,
            "GOOGLE_DISCOVERY_URL": "https://accounts.google.com/.well-known/openid-configuration",
            "MEDIA_UPLOAD_MAX_FILE_SIZE": 1.0,
            "ETL_PATH_IMPORT": False,
            "DEDUP_TOOL": False,
            "MAPS_API_ENDPOINT": "https://maps.example.com",
            "EXPORT_TOOL": True,
            "EXPORT_DEFAULT_EXPIRY": 7,
            "ACTIVITIES_RETENTION": 30,
            "GEO_MAP_DEFAULT_CENTER": {"lat": 0, "lng": 0},
            "ADV_ANALYSIS": False,
            "ACTIVITIES": {"APPROVE": False},
            "ITEMS_PER_PAGE_OPTIONS": [10, 20, 30],
            "VIDEO_RATES": [0.5, 1.0, 1.5],
            "MAIL_ENABLED": False,
            "TRANSCRIPTION_ENABLED": False,
        }

        config = FullConfigValidationModel(**base_config)
        assert config.ITEMS_PER_PAGE_OPTIONS == [10, 20, 30]
        assert config.VIDEO_RATES == [0.5, 1.0, 1.5]

        # Negative items per page
        invalid = base_config.copy()
        invalid["ITEMS_PER_PAGE_OPTIONS"] = [-10, 20, 30]
        with pytest.raises(ValidationError) as exc_info:
            FullConfigValidationModel(**invalid)
        assert "All items per page options must be greater than 0" in str(exc_info.value)

        # Zero video rate
        invalid2 = base_config.copy()
        invalid2["VIDEO_RATES"] = [0.0, 1.0, 1.5]
        with pytest.raises(ValidationError) as exc_info:
            FullConfigValidationModel(**invalid2)
        assert "All video rates must be greater than 0" in str(exc_info.value)


# =========================================================================
# SEARCH UTILS - DYNAMIC FIELD TESTS
# =========================================================================


class TestDynamicFieldSearch:
    @staticmethod
    def _mock_db(fields, monkeypatch):
        from types import SimpleNamespace

        query_result = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(all=lambda: fields))
        sess = SimpleNamespace(query=lambda *a, **k: query_result)
        monkeypatch.setattr("enferno.utils.search_utils.db", SimpleNamespace(session=sess))

    @staticmethod
    def _make_field(name, field_type):
        from types import SimpleNamespace

        return SimpleNamespace(name=name, field_type=field_type, active=True, searchable=True)

    def test_select_field_any_operator(self, monkeypatch):
        from enferno.admin.models.DynamicField import DynamicField
        from enferno.utils.search_utils import SearchUtils
        from sqlalchemy.dialects import postgresql

        field = self._make_field("test_select", DynamicField.SELECT)
        self._mock_db([field], monkeypatch)

        conditions = []
        utils = SearchUtils([], "bulletin")
        utils._apply_dynamic_field_filters(
            conditions,
            {"dyn": [{"name": field.name, "op": "any", "value": [1, 2]}]},
            "bulletin",
        )
        assert len(conditions) == 1
        sql = str(
            conditions[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "&&" in sql
        assert "ARRAY['1', '2']" in sql

    def test_text_field_contains_coerces_numeric(self, monkeypatch):
        from enferno.admin.models.DynamicField import DynamicField
        from enferno.utils.search_utils import SearchUtils
        from sqlalchemy.dialects import postgresql

        field = self._make_field("test_text", DynamicField.TEXT)
        self._mock_db([field], monkeypatch)

        conditions = []
        utils = SearchUtils([], "bulletin")
        utils._apply_dynamic_field_filters(
            conditions,
            {
                "dyn": [
                    {
                        "name": field.name,
                        "op": "contains",
                        "value": 42,
                    }
                ]
            },
            "bulletin",
        )
        assert len(conditions) == 1
        compiled = conditions[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled)
        assert "%42%" in sql
        assert "ILIKE" in sql.upper()


# =========================================================================
# DYNAMIC FIELD MODEL TESTS
# =========================================================================


class TestDynamicField:
    def test_create_text_field(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        field = DynamicField(
            name="test_simple_text",
            title="Test Simple Text",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )
        field.save()
        saved = DynamicField.query.filter_by(name="test_simple_text").first()
        assert saved is not None
        assert saved.field_type == DynamicField.TEXT
        assert saved.entity_type == "bulletin"
        session.delete(field)
        session.commit()

    def test_field_validation(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        with pytest.raises(ValueError, match="Field name must be a valid Python identifier"):
            DynamicField(
                name="invalid-name",
                title="Invalid",
                entity_type="bulletin",
                field_type=DynamicField.TEXT,
            )
        with pytest.raises(ValueError, match="Field name 'id' is reserved"):
            DynamicField(
                name="id",
                title="Reserved",
                entity_type="bulletin",
                field_type=DynamicField.TEXT,
            )

    def test_different_field_types(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        configs = [
            (DynamicField.TEXT, DynamicField.UIComponent.INPUT, "test_text"),
            (
                DynamicField.LONG_TEXT,
                DynamicField.UIComponent.TEXTAREA,
                "test_long_text",
            ),
            (
                DynamicField.NUMBER,
                DynamicField.UIComponent.NUMBER_INPUT,
                "test_number",
            ),
            (
                DynamicField.SELECT,
                DynamicField.UIComponent.DROPDOWN,
                "test_select",
                [{"label": "Option 1", "value": "opt1"}],
            ),
            (
                DynamicField.DATETIME,
                DynamicField.UIComponent.DATE_PICKER,
                "test_datetime",
            ),
        ]
        created = []
        for c in configs:
            if len(c) == 4:
                ft, ui, name, opts = c
            else:
                ft, ui, name = c
                opts = []
            f = DynamicField(
                name=name,
                title=f"Test {name}",
                entity_type="bulletin",
                field_type=ft,
                ui_component=ui,
                options=opts,
            )
            f.save()
            created.append(f)
            assert f.field_type == ft
            assert f.ui_component == ui
        for f in created:
            session.delete(f)
        session.commit()

    def test_field_options(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        field = DynamicField(
            name="test_options_dropdown",
            title="Test Options Dropdown",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            options=[
                {"label": "Option 1", "value": "opt1"},
                {"label": "Option 2", "value": "opt2"},
            ],
        )
        field.save()
        session.commit()
        saved = DynamicField.query.filter_by(name="test_options_dropdown").first()
        assert len(saved.options) == 2
        assert saved.options[0]["label"] == "Option 1"
        assert saved.options[0].get("id") == 1
        assert saved.options[1].get("id") == 2
        session.delete(field)
        session.commit()

    def test_field_configuration(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        field = DynamicField(
            name="test_field_config",
            title="Test Field Config",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
            schema_config={"required": True, "default": "test"},
            ui_config={"help_text": "Enter text", "width": "w-100"},
            validation_config={"max_length": 100},
        )
        field.save()
        session.commit()
        saved = DynamicField.query.filter_by(name="test_field_config").first()
        assert saved.schema_config["required"] is True
        assert saved.ui_config["help_text"] == "Enter text"
        assert saved.validation_config["max_length"] == 100
        session.delete(field)
        session.commit()

    def test_field_uniqueness_constraint(self, session):
        from enferno.admin.models.DynamicField import DynamicField
        from enferno.utils.base import DatabaseException

        f1 = DynamicField(
            name="test_unique_name",
            title="Test Unique 1",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )
        f1.save()
        session.commit()

        f2 = DynamicField(
            name="test_unique_name",
            title="Test Unique 2",
            entity_type="bulletin",
            field_type=DynamicField.TEXT,
            ui_component=DynamicField.UIComponent.INPUT,
        )
        with pytest.raises(DatabaseException):
            super(DynamicField, f2).save(raise_exception=True)
        session.delete(f1)
        session.commit()

    def test_get_valid_components(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        assert DynamicField.UIComponent.INPUT in DynamicField.get_valid_components(
            DynamicField.TEXT
        )
        assert DynamicField.UIComponent.TEXTAREA in DynamicField.get_valid_components(
            DynamicField.LONG_TEXT
        )
        assert DynamicField.UIComponent.NUMBER_INPUT in DynamicField.get_valid_components(
            DynamicField.NUMBER
        )
        assert DynamicField.UIComponent.DROPDOWN in DynamicField.get_valid_components(
            DynamicField.SELECT
        )
        assert DynamicField.UIComponent.DATE_PICKER in DynamicField.get_valid_components(
            DynamicField.DATETIME
        )
        assert DynamicField.get_valid_components("invalid_type") == []

    def test_option_id_generation(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        field = DynamicField(
            name="test_option_ids",
            title="Test Option IDs",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            options=[
                {"label": "Option A", "value": "opt_a"},
                {"label": "Option B", "value": "opt_b"},
            ],
        )
        assert field.options[0].get("id") is None
        assert field.options[1].get("id") is None

        field.save()
        assert field.options[0].get("id") == 1
        assert field.options[1].get("id") == 2

        field.options.append({"label": "Option C", "value": "opt_c"})
        field.ensure_option_ids()
        assert field.options[2].get("id") == 3

        del field.options[1]
        field.options.append({"label": "Option D", "value": "opt_d"})
        field.ensure_option_ids()
        assert field.options[0].get("id") == 1
        assert field.options[1].get("id") == 3
        assert field.options[2].get("id") == 4

        session.delete(field)
        session.commit()

    def test_allow_multiple_config(self, session):
        from enferno.admin.models.DynamicField import DynamicField

        single = DynamicField(
            name="test_single_select",
            title="Test Single Select",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            schema_config={"allow_multiple": False},
            options=[{"label": "Option 1", "value": "opt1"}],
        )
        single.save()

        multi = DynamicField(
            name="test_multi_select",
            title="Test Multi Select",
            entity_type="bulletin",
            field_type=DynamicField.SELECT,
            ui_component=DynamicField.UIComponent.DROPDOWN,
            schema_config={"allow_multiple": True},
            options=[{"label": "Option 1", "value": "opt1"}],
        )
        multi.save()

        assert single.field_type == DynamicField.SELECT
        assert multi.field_type == DynamicField.SELECT
        assert single.schema_config.get("allow_multiple") is False
        assert multi.schema_config.get("allow_multiple") is True

        session.delete(single)
        session.delete(multi)
        session.commit()
