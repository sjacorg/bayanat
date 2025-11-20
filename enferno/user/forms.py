from flask_security.forms import RegisterForm, LoginForm, ChangePasswordForm
from flask_security import MfRecoveryCodesForm
from flask_security.decorators import current_user
from flask_security.webauthn import WebAuthnRegisterForm
from wtforms import StringField
from wtforms.validators import ValidationError

from enferno.admin.constants import Constants
from enferno.admin.models import Notification
from enferno.admin.models.Activity import Activity
from enferno.extensions import db
from enferno.user.models import User
from enferno.utils.logging_utils import get_logger
from enferno.utils.validation_utils import validate_password_policy, validate_webauthn_device_name
from flask_wtf import RecaptchaField

logger = get_logger()


class ExtendedRegisterForm(RegisterForm):
    name = StringField("Full Name")

    def validate_password(self, field):
        try:
            validate_password_policy(field.data)
        except ValueError as e:
            raise ValidationError(str(e))


class ExtendedLoginForm(LoginForm):
    recaptcha = RecaptchaField()

    def validate(self, **kwargs):
        # Log and notify admins when user without role attempts login
        if self.username.data:
            user = db.session.execute(
                db.select(User).filter(User.username == self.username.data)
            ).scalar_one_or_none()

            # Active user with no roles - will be blocked by is_active property
            if user and user.active and not user.roles:
                logger.warning(f"User {user.username} blocked - no system role")

                Activity.create(
                    user_id=user.id,
                    action="Login blocked - no system role",
                    details=f"User attempted login without assigned role",
                )

                Notification.send_admin_notification_for_event(
                    Constants.NotificationEvent.GENERAL,
                    "User Login Blocked - No System Role",
                    f"{user.username} attempted login without assigned role. Please assign appropriate role.",
                )

        return super().validate(**kwargs)


class SanitizedWebAuthnRegisterForm(WebAuthnRegisterForm):
    """Custom WebAuthn registration form with plain text validation for device names"""

    def validate_name(self, field):
        """Validate the name field to ensure it contains only plain text"""
        # Use the new validation utility that rejects HTML instead of sanitizing
        validate_webauthn_device_name(field.data)


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
