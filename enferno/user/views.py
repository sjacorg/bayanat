import json
import os

import requests
from flask import Blueprint, request, session, redirect, g, Response, current_app
from flask.templating import render_template
from flask_security import auth_required, login_user, current_user
from flask_security.forms import LoginForm
from oauthlib.oauth2 import WebApplicationClient
from sqlalchemy.orm.attributes import flag_modified

from enferno.settings import Config as cfg
from enferno.user.forms import ExtendedLoginForm
from enferno.user.models import User
from flask_security.signals import password_changed
bp_user = Blueprint('users', __name__, static_folder='../static')

client = WebApplicationClient(cfg.GOOGLE_CLIENT_ID)


@bp_user.before_app_request
def before_request():
    """
    Attach user object to global context, display custom captcha form after certain failed attempts
    """
    g.user = current_user

    if session.get('failed', 0) > 1 and cfg.RECAPTCHA_ENABLED:
        current_app.extensions['security'].login_form = ExtendedLoginForm
    else:
        current_app.extensions['security'].login_form = LoginForm


@bp_user.after_app_request
def after_app_request(response):
    """
    Record failed login attempts into the session
    """
    if request.path == '/login' and request.method == 'POST':
        # failed login
        if not g.identity.id:
            session['failed'] = session.get('failed', 0) + 1

    return response


def get_google_provider_cfg():
    """
    helper method
    :return: returns openid json configurations
    """
    return requests.get(cfg.GOOGLE_DISCOVERY_URL).json()


@bp_user.route('/auth')
def auth():
    """
    Endpoint to authorize with Google OpenID
    if successful a user is loaded/created and logged in. otherwise, returns an error.
    """
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


@bp_user.route('/auth/callback')
def auth_callback():
    """
    Open ID callback endpoint.


    :return:
    """
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
    if not users_email.endswith(current_app.config.get('GOOGLE_CLIENT_ALLOWED_DOMAIN')):
        return "User email rejected!  ", 403

    # Create a user in our db with the information provided
    # by Google
    u = User.query.filter(User.google_id == unique_id).first()
    if u is None:
        u = User()
        u.email = users_email
        u.google_id = unique_id
        u.name = users_name
        u.active = True
        u.password = os.urandom(32).hex()
        u.save()

    login_user(u)
    return redirect(cfg.SECURITY_POST_LOGIN_VIEW)


@bp_user.route('/dashboard/')
@auth_required('session')
def account():
    """
    Main dashboard endpoint.
    """
    return render_template('dashboard.html')


@bp_user.route('/settings/')
@auth_required('session')
def settings():
    """Endpoint for user settings."""
    return render_template('settings.html')

@bp_user.route('/settings/save',methods=['PUT'])
@auth_required('session')
def save_settings():
    """API Endpoint to save user settings."""
    json = request.json.get('settings')
    dark = json.get('dark')
    user_id = current_user.id
    user = User.query.get(user_id)
    if not user:
        return 'Problem loading user', 417
    user.settings = {'dark': dark}
    lang = json.get('language')
    user.settings['language'] = lang
    flag_modified(user, 'settings')
    user.save()
    return 'Settings Saved', 200

@bp_user.route('/settings/load',methods=['GET'])
@auth_required('session')
def load_settings():
    """API Endpoint to load user settings, in json format. """
    user_id = current_user.id

    user = User.query.get(user_id)

    if not user:
        return 'Problem loading user ', 417

    settings = user.settings or {}

    return Response(json.dumps(settings), content_type='Application/json'), 200
@password_changed.connect
def after_password_change(sender, user):
    user.unset_security_reset_key()


@bp_user.before_app_request
def before_app_request():
    """
    Global check for forced password reset flag
    :return: None
    """
    if current_user.is_authenticated and current_user.security_reset_key:
        if not any(request.path.startswith(p) for p in ('/change', '/static', '/logout')):
            return redirect('/change')
