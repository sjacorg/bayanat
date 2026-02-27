# -*- coding: utf-8 -*-

import pandas as pd
from urllib.parse import urlparse
from flask import Flask, render_template, current_app
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
from enferno.extensions import db, session, babel, rds, debug_toolbar, mail, limiter, talisman
from enferno.public.views import bp_public
from enferno.setup.views import bp_setup
from enferno.settings import Config
from enferno.user.forms import (
    ExtendedMfRecoveryCodesForm,
    ExtendedChangePasswordForm,
    ExtendedRegisterForm,
    ExtendedLoginForm,
    SanitizedWebAuthnRegisterForm,
)
from enferno.user.models import User, Role
from enferno.user.models import WebAuthn
from enferno.user.views import bp_user
from enferno.utils.logging_utils import get_logger
from enferno.utils.rate_limit_utils import ratelimit_handler

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
    return app


def register_extensions(app):
    """
    Register Flask extensions.

    Args:
        app: Flask application instance
    """
    db.init_app(app)
    # Skip debug toolbar when CSP is enabled (they conflict)
    if not app.config.get("CSP_ENABLED", False):
        debug_toolbar.init_app(app)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role, webauthn_model=WebAuthn)

    # Initialize security options with common configurations
    security_options = {
        "register_form": ExtendedRegisterForm,
        "wan_register_form": SanitizedWebAuthnRegisterForm,
        "mf_recovery_codes_form": ExtendedMfRecoveryCodesForm,
        "change_password_form": ExtendedChangePasswordForm,
    }

    # Add the login form to the security options if reCAPTCHA is enabled
    if app.config.get("RECAPTCHA_ENABLED", False):
        security_options["login_form"] = ExtendedLoginForm

    # Initialize Flask-Security with the configured options
    security = Security(app, user_datastore, **security_options)

    session.init_app(app)
    babel.init_app(app, locale_selector=get_locale, default_domain="messages", default_locale="en")
    rds.init_app(app)
    mail.init_app(app)

    # Configure limiter storage with the correct config
    limiter.storage_uri = app.config["REDIS_URL"]
    limiter.init_app(app)

    # Initialize Talisman with security headers
    register_talisman(app)


def register_talisman(app):
    """
    Register Flask-Talisman for security headers including CSP.

    Args:
        app: Flask application instance
    """
    # Build CSP policy
    csp = {
        "default-src": "'self'",
        "script-src": ["'self'", "'unsafe-eval'"],  # Vue requires it to compile templates
        "style-src": ["'self'", "'unsafe-inline'"],  # Vuetify requires unsafe-inline for styles
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "media-src": ["'self'", "blob:"],
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
    }

    # Add map tile servers to img-src and connect-src
    maps_endpoint = app.config.get("MAPS_API_ENDPOINT", "")
    _maps_host = urlparse(maps_endpoint).hostname or ""
    if _maps_host.endswith("openstreetmap.org") or _maps_host.endswith("tile.osm.org"):
        csp["img-src"].append("https://tile.osm.org")
        csp["img-src"].append("https://*.tile.osm.org")
        csp["img-src"].append("https://tile.openstreetmap.org")
        csp["img-src"].append("https://*.tile.openstreetmap.org")
        csp["connect-src"].append("https://tile.openstreetmap.org")
        csp["connect-src"].append("https://*.tile.openstreetmap.org")
        csp["connect-src"].append("https://tile.osm.org")
        csp["connect-src"].append("https://*.tile.osm.org")

    # Add Google Maps if configured
    if app.config.get("GOOGLE_MAPS_API_KEY"):
        csp["img-src"].extend(
            [
                "https://*.google.com",
                "https://*.googleapis.com",
                "https://*.gstatic.com",
            ]
        )
        csp["connect-src"].extend(
            [
                "https://*.google.com",
                "https://*.googleapis.com",
            ]
        )
        csp["script-src"].append("https://maps.googleapis.com")

    # Add Google OAuth if enabled
    if app.config.get("GOOGLE_OAUTH_ENABLED"):
        csp["connect-src"].append("https://accounts.google.com")
        csp["img-src"].append("https://accounts.google.com")

    # Add S3 bucket to CSP when using S3 storage
    if not app.config.get("FILESYSTEM_LOCAL"):
        s3_region = app.config.get("AWS_REGION", "us-east-1")
        s3_bucket = app.config.get("S3_BUCKET", "")
        s3_origins = [
            f"https://{s3_bucket}.s3.amazonaws.com",
            f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com",
        ]
        for origin in s3_origins:
            csp["img-src"].append(origin)
            csp["media-src"].append(origin)
            csp["connect-src"].append(origin)

    # Check if CSP should be enabled
    csp_enabled = app.config.get("CSP_ENABLED", True)
    csp_report_uri = app.config.get("CSP_REPORT_URI")
    # Report-only mode requires a report URI
    csp_report_only = app.config.get("CSP_REPORT_ONLY", False) and csp_report_uri

    talisman.init_app(
        app,
        # CSP settings
        content_security_policy=csp if csp_enabled else None,
        content_security_policy_nonce_in=["script-src"],  # Add nonce to script-src
        content_security_policy_report_only=csp_report_only,
        content_security_policy_report_uri=csp_report_uri if csp_report_only else None,
        # Other security headers
        force_https=app.config.get("FORCE_HTTPS", False),  # Don't force in dev
        force_https_permanent=False,
        frame_options="DENY",
        strict_transport_security=app.config.get("FORCE_HTTPS", False),
        strict_transport_security_max_age=31536000,  # 1 year
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=False,
        referrer_policy="strict-origin-when-cross-origin",
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", True),
        session_cookie_http_only=True,
    )


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
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.create_db)
    app.cli.add_command(commands.import_data)
    app.cli.add_command(commands.install)
    app.cli.add_command(commands.create)
    app.cli.add_command(commands.add_role)
    app.cli.add_command(commands.reset)
    app.cli.add_command(commands.reset_all_passwords)
    app.cli.add_command(commands.i18n_cli)
    app.cli.add_command(commands.check_db_alignment)
    app.cli.add_command(commands.generate_config)
    app.cli.add_command(commands.ocr_cli)


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

    # Avoid triggering DB access on failed transactions when logging user id
    try:
        uid = current_user.get_id() if current_user else None
    except Exception:
        uid = None

    logger.error(
        f"user_id: {uid} endpoint: {request.path if request else None}",
        exc_info=True,
    )
    return "Internal Server Error", 500


def register_constants(app):
    app.config["CONSTANTS"] = Constants
