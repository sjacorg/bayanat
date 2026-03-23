"""
Security-related tests: rate limiting, setup wizard, input validation.
These tests create their own app instances for proper isolation.
"""

import pytest
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
