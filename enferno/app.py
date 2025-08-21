# -*- coding: utf-8 -*-

import pandas as pd
from flask import Flask, render_template, current_app, request
from flask_login import user_logged_in, user_logged_out
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security import current_user

from enferno.admin.constants import Constants
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
from enferno.admin.views import admin
from enferno.data_import.views import imports
from enferno.extensions import db, session, babel, rds, debug_toolbar, limiter
from enferno.public.views import bp_public
from enferno.setup.views import bp_setup
from enferno.settings import Config
from enferno.user.forms import (
    ExtendedRegisterForm,
    ExtendedLoginForm,
    SanitizedWebAuthnRegisterForm,
)
from enferno.user.models import User, Role
from enferno.user.models import WebAuthn
from enferno.user.views import bp_user
from enferno.utils.logging_utils import get_logger
from enferno.utils.rate_limit_utils import ratelimit_handler
from enferno.utils.maintenance import register_maintenance_middleware

logger = get_logger()


def get_locale():
    """
    Sets the system global language.

    Returns:
        System language from the current session.
    """
    default = current_app.config.get("BABEL_DEFAULT_LOCALE", "en")

    if getattr(current_user, "is_authenticated", False) and current_user.settings:
        return current_user.settings.get("language", default)

    return default


def create_app(config_object=Config):
    """
    Create a Flask application using the app factory pattern.

    Args:
        config_object: Configuration object to use.

    Returns:
        Flask application instance.
    """
    app = Flask(__name__)
    register_errorhandlers(app)
    app.config.from_object(config_object)
    register_constants(app)
    register_blueprints(app)
    register_extensions(app)
    register_shellcontext(app)
    register_commands(app)
    register_signals(app)
    register_maintenance_middleware(app)

    return app


def register_extensions(app):
    """
    Register Flask extensions.

    Args:
        app: Flask application instance
    """
    db.init_app(app)
    debug_toolbar.init_app(app)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role, webauthn_model=WebAuthn)

    # Initialize security options with common configurations
    security_options = {
        "register_form": ExtendedRegisterForm,
        "wan_register_form": SanitizedWebAuthnRegisterForm,
    }

    # Add the login form to the security options if reCAPTCHA is enabled
    if app.config.get("RECAPTCHA_ENABLED", False):
        security_options["login_form"] = ExtendedLoginForm

    # Initialize Flask-Security with the configured options
    security = Security(app, user_datastore, **security_options)

    session.init_app(app)
    babel.init_app(app, locale_selector=get_locale, default_domain="messages", default_locale="en")
    rds.init_app(app)
    limiter.init_app(app)


def register_signals(app):
    """
    Register signals for the application.

    Args:
        app: Flask application instance
    """

    @user_logged_in.connect_via(app)
    def _after_login_hook(sender, user, **extra):
        # clear login counter
        from flask import session

        if session.get("failed"):
            session.pop("failed")
            logger.info("login counter cleared")

        Activity.create(
            user, Activity.ACTION_LOGIN, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )

    @user_logged_out.connect_via(app)
    def _after_logout_hook(sender, user, **extra):
        Activity.create(
            user, Activity.ACTION_LOGOUT, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )


def register_blueprints(app):
    """
    Register Flask blueprints.

    Args:
        app: Flask application instance
    """
    if not app.config.get("SETUP_COMPLETE"):
        app.register_blueprint(bp_setup)  # Register the setup blueprint if setup is not complete
    app.register_blueprint(bp_public)
    app.register_blueprint(bp_user)
    app.register_blueprint(admin)
    app.register_blueprint(imports)

    if app.config.get("EXPORT_TOOL"):
        try:
            from enferno.export.views import export

            app.register_blueprint(export)
        except ImportError as e:
            app.logger.error(e)

    if app.config.get("DEDUP_TOOL"):
        try:
            from enferno.deduplication.views import deduplication

            app.register_blueprint(deduplication)
        except ImportError as e:
            app.logger.error(e)


def register_shellcontext(app):
    """
    Register shell context objects.

    Args:
        app: Flask application instance
    """

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
    """
    Register Click commands.

    Args:
        app: Flask application instance
    """
    app.cli.add_command(commands.create_db)
    app.cli.add_command(commands.import_data)
    app.cli.add_command(commands.install)
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.create)
    app.cli.add_command(commands.add_role)
    app.cli.add_command(commands.reset)
    app.cli.add_command(commands.i18n_cli)
    app.cli.add_command(commands.check_db_alignment)
    app.cli.add_command(commands.mark_migrations_applied)
    app.cli.add_command(commands.apply_migrations)
    app.cli.add_command(commands.generate_config)
    app.cli.add_command(commands.backup_db)
    app.cli.add_command(commands.restore_db)
    app.cli.add_command(commands.enable_maintenance)
    app.cli.add_command(commands.disable_maintenance)
    app.cli.add_command(commands.set_version)
    app.cli.add_command(commands.get_version)
    app.cli.add_command(commands.update_system)


def register_errorhandlers(app):
    """
    Register error handlers for the application.

    Args:
        app: Flask application instance
    """

    def render_error(error):
        error_code = getattr(error, "code", 500)
        return render_template(f"{error_code}.html"), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)

    app.errorhandler(429)(ratelimit_handler)

    app.errorhandler(Exception)(handle_uncaught_exception)


def handle_uncaught_exception(e):
    """
    Global uncaught error handler for the application.

    Args:
        e: exception object

    Returns:
        error message
    """
    from werkzeug.exceptions import HTTPException
    from flask import request, current_app
    from flask_security.decorators import current_user

    if isinstance(e, HTTPException) and e.code < 500:
        return e.get_response()

    logger.error(
        f"user_id: {current_user.id if hasattr(current_user, 'id') else None} endpoint: {request.path if request else None}",
        exc_info=True,
    )
    return "Internal Server Error", 500


def register_constants(app):
    app.config["CONSTANTS"] = Constants
