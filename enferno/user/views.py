import json
import os
from typing import Any, Literal, Optional

import requests
from flask import Blueprint, request, session, redirect, g, Response, current_app
from flask.templating import render_template
from flask_security import auth_required, login_user, current_user
from flask_security.forms import LoginForm
from oauthlib.oauth2 import WebApplicationClient
from sqlalchemy.orm.attributes import flag_modified

from enferno.admin.constants import Constants
from enferno.settings import Config as cfg
from enferno.user.forms import ExtendedLoginForm
from enferno.user.models import User, Session
from enferno.admin.models.Notification import Notification
from flask_security.signals import password_changed, user_authenticated, tf_profile_changed

bp_user = Blueprint("users", __name__, static_folder="../static")

client = WebApplicationClient(cfg.GOOGLE_CLIENT_ID)


@bp_user.before_app_request
def before_request() -> None:
    """
    Attach user object to global context, display custom captcha form after certain failed attempts
    """
    g.user = current_user

    if session.get("failed", 0) > 1 and cfg.RECAPTCHA_ENABLED:
        current_app.extensions["security"].login_form = ExtendedLoginForm
    else:
        current_app.extensions["security"].login_form = LoginForm


@bp_user.after_app_request
def after_app_request(response) -> Response:
    """
    Record failed login attempts into the session
    """
    if request.path == "/login" and request.method == "POST":
        # failed login
        if not g.identity.id:
            session["failed"] = session.get("failed", 0) + 1

    return response


def get_google_provider_cfg() -> Any:
    """
    helper method.

    Returns:
        - returns openid json configurations
    """
    return requests.get(cfg.GOOGLE_DISCOVERY_URL).json()


@bp_user.route("/auth")
def auth() -> Response:
    """
    Endpoint to authorize with Google OpenID.

    Returns:
        - redirects to Google's authorization endpoint, if Google Auth is enabled and configured properly.
    """
    if not cfg.GOOGLE_OAUTH_ENABLED or not cfg.GOOGLE_CLIENT_ALLOWED_DOMAIN:
        return "Google Auth is not enabled or configured properly", 417

    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@bp_user.route("/auth/callback")
def auth_callback() -> Response:
    """
    Open ID callback endpoint.
    """
    if not cfg.GOOGLE_OAUTH_ENABLED or not cfg.GOOGLE_CLIENT_ALLOWED_DOMAIN:
        return "Google Auth is not enabled or configured properly", 417

    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(cfg.GOOGLE_CLIENT_ID, cfg.GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that we have tokens (yay) let's find and hit URL
    # from Google that gives you user's profile information,
    # including their Google Profile Image and Email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # We want to make sure their email is verified.
    # The user authenticated with Google, authorized our
    # app, and now we've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        # picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["name"]
    else:
        return "User email not available or not verified by Google.", 400

    # check if email belongs to the allowed domain
    if not users_email.split("@")[-1] == cfg.GOOGLE_CLIENT_ALLOWED_DOMAIN:
        return "User email rejected!", 403

    # secure login by restricting access to only matching users who already have an account
    # Check if the user with the provided email exists in the database
    u = User.query.filter(User.email == users_email).first()
    if u is None:
        # User with the provided email does not exist
        return "User not found. Ask an administrator to create an account for you.", 404

    # Update the user's Google ID if it doesn't exist
    if u.google_id is None:
        u.google_id = unique_id
        u.save()

    login_user(u)
    return redirect(cfg.SECURITY_POST_LOGIN_VIEW)


@bp_user.route("/dashboard/")
@auth_required("session")
def account() -> str:
    """
    Main dashboard endpoint.
    """
    return render_template("dashboard.html")


@bp_user.route("/settings/")
@auth_required("session")
def settings() -> str:
    """Endpoint for user settings."""
    return render_template("settings.html")


@bp_user.route("/settings/save", methods=["PUT"])
@auth_required("session")
def save_settings() -> Response:
    """API Endpoint to save user settings."""
    json = request.json.get("settings")
    dark = json.get("dark")
    user_id = current_user.id
    user = User.query.get(user_id)
    if not user:
        return "Problem loading user", 417
    user.settings = {"dark": dark}
    lang = json.get("language")
    user.settings["language"] = lang
    user.settings["setupCompleted"] = json.get("setupCompleted")
    flag_modified(user, "settings")
    user.save()
    return "Settings Saved", 200


@bp_user.route("/settings/load", methods=["GET"])
@auth_required("session")
def load_settings() -> Response:
    """API Endpoint to load user settings, in json format."""
    user_id = current_user.id

    user = User.query.get(user_id)

    if not user:
        return "Problem loading user ", 417

    settings = user.settings or {}

    return Response(json.dumps(settings), content_type="Application/json"), 200


@password_changed.connect
def after_password_change(sender, user) -> None:
    """Reset the security reset key after password change, send notification to user"""
    user.unset_security_reset_key()
    Notification.send_notification_to_user_for_event(
        Constants.NotificationEvent.PASSWORD_CHANGE,
        user,
        "Password Changed",
        "Your password has been changed.",
    )


@bp_user.before_app_request
def before_app_request() -> Optional[Response]:
    """
    Global check for forced password reset flag.

    Returns:
        - redirects to the password change page if the user is authenticated and has a security reset key set.
    """
    if current_user.is_authenticated and current_user.security_reset_key:
        if not any(request.path.startswith(p) for p in ("/change", "/static", "/logout")):
            return redirect("/change")


@user_authenticated.connect
def user_authenticated_handler(app, user, authn_via, **extra_args) -> None:
    session_data = {
        "user_id": user.id,
        "session_token": session.sid,
        "ip_address": request.remote_addr,
        "meta": {
            "browser": request.user_agent.browser,
            "browser_version": request.user_agent.version,
            "os": request.user_agent.platform,
            "device": request.user_agent.string,  # Full user-agent string
        },
    }
    # Create a new Session object and add it to the database
    new_session = Session(**session_data)
    new_session.save()

    # Check if logged in from a different IP address
    # TODO: Confirm if these fields are being updated correctly prior to this step
    if current_user.current_login_ip != current_user.last_login_ip:
        Notification.send_notification_to_user_for_event(
            Constants.NotificationEvent.LOGIN_NEW_IP,
            current_user,
            "Login from Different IP",
            f"You have logged in from a different IP address than your last login. If this was you, please ignore this message. If this was not you, please change your password immediately.",
        )
    # TODO: Check the login country and send notification to all admins if it's not the same as the user's country

    # Check if multiple sessions are disabled
    if current_app.config.get("DISABLE_MULTIPLE_SESSIONS", False):
        user.logout_other_sessions()


@tf_profile_changed.connect
def after_tf_profile_change(sender, user, **extra_args) -> None:
    Notification.send_notification_to_user_for_event(
        Constants.NotificationEvent.TWO_FACTOR_CHANGE,
        user,
        "Two-Factor Profile Changed",
        "Your two-factor profile has been changed. Please verify your new profile.",
    )
