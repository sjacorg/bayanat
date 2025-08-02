import pytest
from wtforms.validators import ValidationError

from enferno.utils.validation_utils import validate_webauthn_device_name
from enferno.user.forms import SanitizedWebAuthnRegisterForm


class TestPlainTextValidation:
    """Test the plain text validation utility function"""

    def test_valid_plain_text(self):
        """Test that valid plain text passes validation"""
        # These should all pass without raising exceptions
        validate_webauthn_device_name("My Phone")
        validate_webauthn_device_name("iPhone 15")
        validate_webauthn_device_name("Work Laptop")
        validate_webauthn_device_name("  Tablet  ")  # whitespace should be normalized

    def test_empty_field_rejection(self):
        """Test that empty fields are rejected"""
        with pytest.raises(ValidationError, match="Webauthn device name cannot be empty"):
            validate_webauthn_device_name("")

        with pytest.raises(ValidationError, match="Webauthn device name cannot be empty"):
            validate_webauthn_device_name("   ")  # only whitespace

        with pytest.raises(ValidationError, match="Webauthn device name cannot be empty"):
            validate_webauthn_device_name(None)

    def test_html_tags_rejection(self):
        """Test that HTML tags are rejected"""
        html_test_cases = [
            "My <script>alert('xss')</script> Phone",
            "Device <div>content</div>",
            "Phone<!--comment-->",
            "My <div>Phone</div>",
            "Phone<svg onload=alert()>",
            "<b>Bold Device</b>",
            "Device<br/>Name",
        ]

        for test_case in html_test_cases:
            with pytest.raises(ValidationError, match="HTML tags are not allowed"):
                validate_webauthn_device_name(test_case)

    def test_html_entities_rejection(self):
        """Test that HTML entities are rejected"""
        entity_test_cases = [
            "Device &lt;script&gt;",
            "&amp;Device&amp;",
            "Phone&nbsp;Name",
            "Device&quot;Name&quot;",
        ]

        for test_case in entity_test_cases:
            with pytest.raises(ValidationError, match="HTML entities are not allowed"):
                validate_webauthn_device_name(test_case)

    def test_length_validation(self):
        """Test that overly long strings are rejected"""
        # Test with default max length (64)
        long_string = "A" * 65
        with pytest.raises(ValidationError, match="is too long"):
            validate_webauthn_device_name(long_string)

        # Test that strings at the limit are accepted
        exactly_64_chars = "A" * 64
        validate_webauthn_device_name(exactly_64_chars)  # Should not raise


class TestWebAuthnFormValidation:
    """Test the WebAuthn registration form validation method directly"""

    def test_form_validation_method_with_valid_input(self):
        """Test that the form validation method accepts valid device names"""

        # Mock a field object
        class MockField:
            def __init__(self, data):
                self.data = data

        # Test the validation method directly without form initialization
        field = MockField("My Valid Device")
        form_instance = SanitizedWebAuthnRegisterForm.__new__(SanitizedWebAuthnRegisterForm)
        # Should not raise any exception
        form_instance.validate_name(field)

    def test_form_validation_method_with_html_input(self):
        """Test that the form validation method rejects HTML in device names"""

        class MockField:
            def __init__(self, data):
                self.data = data

        field = MockField("My <script>alert('xss')</script> Device")
        form_instance = SanitizedWebAuthnRegisterForm.__new__(SanitizedWebAuthnRegisterForm)
        with pytest.raises(ValidationError, match="HTML tags are not allowed"):
            form_instance.validate_name(field)

    def test_form_validation_method_with_entities(self):
        """Test that the form validation method rejects HTML entities"""

        class MockField:
            def __init__(self, data):
                self.data = data

        field = MockField("Device &lt;name&gt;")
        form_instance = SanitizedWebAuthnRegisterForm.__new__(SanitizedWebAuthnRegisterForm)
        with pytest.raises(ValidationError, match="HTML entities are not allowed"):
            form_instance.validate_name(field)
