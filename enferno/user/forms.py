from flask_security.forms import RegisterForm, LoginForm
from flask_security.webauthn import WebAuthnRegisterForm
from wtforms import StringField
from wtforms.validators import ValidationError

from flask_wtf import RecaptchaField
from enferno.utils.validation_utils import validate_plain_text_field


class ExtendedRegisterForm(RegisterForm):
    name = StringField("Full Name")


class ExtendedLoginForm(LoginForm):
    recaptcha = RecaptchaField()


class SanitizedWebAuthnRegisterForm(WebAuthnRegisterForm):
    """Custom WebAuthn registration form with plain text validation for device names"""

    def validate_name(self, field):
        """Validate the name field to ensure it contains only plain text"""
        # Use the new validation utility that rejects HTML instead of sanitizing
        validate_plain_text_field(field.data, "Device name", max_length=64)


class UserInfoForm:
    pass
