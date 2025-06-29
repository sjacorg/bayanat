import pytest
from wtforms.validators import ValidationError

from enferno.utils.validation_utils import validate_plain_text_field
from enferno.user.forms import SanitizedWebAuthnRegisterForm


class TestPlainTextValidation:
    """Test the plain text validation utility function"""

    def test_valid_plain_text(self):
        """Test that valid plain text passes validation"""
        # These should all pass without raising exceptions
        validate_plain_text_field("My Phone", "Device name")
        validate_plain_text_field("iPhone 15", "Device name")
        validate_plain_text_field("Work Laptop", "Device name")
        validate_plain_text_field("  Tablet  ", "Device name")  # whitespace should be normalized

    def test_empty_field_rejection(self):
        """Test that empty fields are rejected"""
        with pytest.raises(ValidationError, match="Device name cannot be empty"):
            validate_plain_text_field("", "Device name")

        with pytest.raises(ValidationError, match="Device name cannot be empty"):
            validate_plain_text_field("   ", "Device name")  # only whitespace

        with pytest.raises(ValidationError, match="Device name cannot be empty"):
            validate_plain_text_field(None, "Device name")

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
            with pytest.raises(ValidationError, match="cannot contain HTML tags"):
                validate_plain_text_field(test_case, "Device name")

    def test_html_entities_rejection(self):
        """Test that HTML entities are rejected"""
        entity_test_cases = [
            "Device &lt;script&gt;",
            "&amp;Device&amp;",
            "Phone&nbsp;Name",
            "Device&quot;Name&quot;",
        ]

        for test_case in entity_test_cases:
            with pytest.raises(ValidationError, match="cannot contain HTML entities"):
                validate_plain_text_field(test_case, "Device name")

    def test_length_validation(self):
        """Test that overly long strings are rejected"""
        # Test with default max length (64)
        long_string = "A" * 65
        with pytest.raises(ValidationError, match="is too long"):
            validate_plain_text_field(long_string, "Device name")

        # Test with custom max length
        with pytest.raises(ValidationError, match="is too long"):
            validate_plain_text_field("Too long", "Test field", max_length=5)

        # Test that strings at the limit are accepted
        exactly_64_chars = "A" * 64
        validate_plain_text_field(exactly_64_chars, "Device name")  # Should not raise


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
        with pytest.raises(ValidationError, match="cannot contain HTML tags"):
            form_instance.validate_name(field)

    def test_form_validation_method_with_entities(self):
        """Test that the form validation method rejects HTML entities"""

        class MockField:
            def __init__(self, data):
                self.data = data

        field = MockField("Device &lt;name&gt;")
        form_instance = SanitizedWebAuthnRegisterForm.__new__(SanitizedWebAuthnRegisterForm)
        with pytest.raises(ValidationError, match="cannot contain HTML entities"):
            form_instance.validate_name(field)
