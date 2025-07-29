from flask_security.forms import RegisterForm, LoginForm, ChangePasswordForm
from flask_security import MfRecoveryCodesForm
from flask_security.decorators import current_user
from flask_security.webauthn import WebAuthnRegisterForm
from wtforms import StringField
from wtforms.validators import ValidationError
from enferno.admin.models import Notification
from enferno.admin.constants import Constants
from flask_wtf import RecaptchaField
from enferno.utils.validation_utils import validate_password_policy, validate_plain_text_field


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
        validate_plain_text_field(field.data, "Device name", max_length=64)


class UserInfoForm:
    pass


class ExtendedMfRecoveryCodesForm(MfRecoveryCodesForm):
    def validate(self, **kwargs):
        if super().validate(**kwargs):
            Notification.send_notification_for_event(
                user=current_user,
                event=Constants.NotificationEvent.RECOVERY_CODES_CHANGE,
                title="Multi-Factor Recovery Codes Changed",
                message="Your multi-factor recovery codes have been generated.",
                category="security",
            )
            return True
        return False


class ExtendedChangePasswordForm(ChangePasswordForm):
    def validate_new_password(self, field):
        try:
            validate_password_policy(field.data)
        except ValueError as e:
            raise ValidationError(str(e))
