from flask_security.forms import RegisterForm, LoginForm
from wtforms import StringField

from flask_wtf import RecaptchaField


class ExtendedRegisterForm(RegisterForm):
    name = StringField("Full Name")


class ExtendedLoginForm(LoginForm):
    recaptcha = RecaptchaField()


class UserInfoForm:
    pass
