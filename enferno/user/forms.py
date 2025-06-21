from flask_security.forms import RegisterForm, LoginForm
from flask_security.webauthn import WebAuthnRegisterForm
from wtforms import StringField
from wtforms.validators import ValidationError

from flask_wtf import RecaptchaField
from enferno.admin.validation.util import sanitize_string


class ExtendedRegisterForm(RegisterForm):
    name = StringField("Full Name")


class ExtendedLoginForm(LoginForm):
    recaptcha = RecaptchaField()


class SanitizedWebAuthnRegisterForm(WebAuthnRegisterForm):
    """Custom WebAuthn registration form with sanitized name field"""

    def validate_name(self, field):
        """Validate and sanitize the name field"""
        # Check for empty or None field data first
        if not field.data or not field.data.strip():
            raise ValidationError(
                "Device name cannot be empty or contain only HTML/special characters."
            )

        # Sanitize the field data
        sanitized_name = sanitize_string(field.data)
        field.data = sanitized_name

        # Ensure name is not empty after sanitization
        if not sanitized_name.strip():
            raise ValidationError(
                "Device name cannot be empty or contain only HTML/special characters."
            )

        # Ensure the sanitized name isn't too long for the database field
        if len(sanitized_name) > 64:
            raise ValidationError("Device name is too long (maximum 64 characters).")


class UserInfoForm:
    pass
