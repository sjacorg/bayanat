from flask_security.forms import RegisterForm, LoginForm, ChangePasswordForm
from flask_security.webauthn import WebAuthnRegisterForm
from wtforms import StringField
from wtforms.validators import ValidationError

from flask_wtf import RecaptchaField
from enferno.utils.validation_utils import validate_password_policy, validate_webauthn_device_name


class ExtendedRegisterForm(RegisterForm):
    name = StringField("Full Name")

    def validate_password(self, field):
        try:
            validate_password_policy(field.data)
        except ValueError as e:
            raise ValidationError(str(e))


class ExtendedLoginForm(LoginForm):
    recaptcha = RecaptchaField()


class SanitizedWebAuthnRegisterForm(WebAuthnRegisterForm):
    """Custom WebAuthn registration form with plain text validation for device names"""

    def validate_name(self, field):
        """Validate the name field to ensure it contains only plain text"""
        # Use the new validation utility that rejects HTML instead of sanitizing
        validate_webauthn_device_name(field.data)


class UserInfoForm:
    pass


class ExtendedChangePasswordForm(ChangePasswordForm):
    def validate_new_password(self, field):
        try:
            validate_password_policy(field.data)
        except ValueError as e:
            raise ValidationError(str(e))
