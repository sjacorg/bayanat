# -*- coding: utf-8 -*-

import pandas as pd
from flask import Flask, render_template, current_app
from flask_security import current_user
from flask_login import user_logged_in, user_logged_out
from flask_security import Security, SQLAlchemyUserDatastore

import enferno.commands as commands
from enferno.admin.models import (
    Bulletin,
    Label,
    Source,
    Location,
    Event,
    Eventtype,
    Media,
    Btob,
    Actor,
    Atoa,
    Atob,
    Incident,
    Itoa,
    Itob,
    Itoi,
    BulletinHistory,
    Activity,
    Settings,
    GeoLocation,
)
from enferno.user.models import WebAuthn
from enferno.admin.views import admin
from enferno.data_import.views import imports
from enferno.extensions import cache, db, session, babel, rds, debug_toolbar
from enferno.public.views import bp_public
from enferno.settings import Config
from enferno.user.forms import ExtendedRegisterForm, ExtendedLoginForm
from enferno.user.models import User, Role
from enferno.user.views import bp_user


def get_locale():
    """
    Sets the system global language.
    :return: system language from the current session.
    """
    default = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")

    if getattr(current_user, "is_authenticated", False) and current_user.settings:
        return current_user.settings.get("language", default)

    return default


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_blueprints(app)
    register_extensions(app)

    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    register_signals(app)
    return app


def register_extensions(app):
    cache.init_app(app)
    db.init_app(app)
    debug_toolbar.init_app(app)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role, webauthn_model=WebAuthn)

    # Initialize security options with common configurations
    security_options = {
        "register_form": ExtendedRegisterForm,
    }

    # Add the login form to the security options if reCAPTCHA is enabled
    if app.config.get("RECAPTCHA_ENABLED", False):
        security_options["login_form"] = ExtendedLoginForm

    # Initialize Flask-Security with the configured options
    security = Security(app, user_datastore, **security_options)

    session.init_app(app)
    babel.init_app(app, locale_selector=get_locale, default_domain="messages", default_locale="en")
    rds.init_app(app)

    return None


def register_signals(app):
    @user_logged_in.connect_via(app)
    def _after_login_hook(sender, user, **extra):
        # clear login counter
        from flask import session

        if session.get("failed"):
            session.pop("failed")
            print("login counter cleared")

        Activity.create(
            user, Activity.ACTION_LOGIN, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )

    @user_logged_out.connect_via(app)
    def _after_logout_hook(sender, user, **extra):
        Activity.create(
            user, Activity.ACTION_LOGOUT, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )


def register_blueprints(app):
    app.register_blueprint(bp_public)
    app.register_blueprint(bp_user)
    app.register_blueprint(admin)
    app.register_blueprint(imports)

    if app.config.get("EXPORT_TOOL"):
        try:
            from enferno.export.views import export

            app.register_blueprint(export)
        except ImportError as e:
            print(e)

    if app.config.get("DEDUP_TOOL"):
        try:
            from enferno.deduplication.views import deduplication

            app.register_blueprint(deduplication)
        except ImportError as e:
            print(e)

    return None


def register_errorhandlers(app):
    def render_error(error):
        error_code = getattr(error, "code", 500)
        return render_template("{0}.html".format(error_code)), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """Register shell context objects."""

    def shell_context():
        """Shell context objects."""
        return {
            "db": db,
            "pd": pd,
            "User": User,
            "Role": Role,
            "Label": Label,
            "Bulletin": Bulletin,
            "BulletinHistory": BulletinHistory,
            "Location": Location,
            "GeoLocation": GeoLocation,
            "Source": Source,
            "Eventtype": Eventtype,
            "Event": Event,
            "Media": Media,
            "Btob": Btob,
            "Atoa": Atoa,
            "Atob": Atob,
            "Actor": Actor,
            "Incident": Incident,
            "Itoi": Itoi,
            "Itob": Itob,
            "Itoa": Itoa,
            "Activity": Activity,
            "Settings": Settings,
            "rds": rds,
        }

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""

    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.create_db)
    app.cli.add_command(commands.import_data)
    app.cli.add_command(commands.install)
    app.cli.add_command(commands.create)
    app.cli.add_command(commands.add_role)
    app.cli.add_command(commands.reset)
    app.cli.add_command(commands.i18n_cli)
    app.cli.add_command(commands.check_db_alignment)
