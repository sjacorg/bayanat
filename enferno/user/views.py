import json
import os

import requests
from flask import Blueprint, request, session, redirect, flash, g, Response, current_app
from flask.templating import render_template
from flask_security import login_required, login_user, current_user
from flask_security.utils import hash_password, verify_password
from oauthlib.oauth2 import WebApplicationClient

from enferno.settings import ProdConfig, DevConfig
from enferno.user.models import User
from enferno.user.forms import ExtendedLoginForm
from flask_security.forms import LoginForm

bp_user = Blueprint('users', __name__, static_folder='../static')

if os.environ.get("FLASK_DEBUG") == '0':
    cfg = ProdConfig
else:
    cfg = DevConfig

client = WebApplicationClient(cfg.GOOGLE_CLIENT_ID)


@bp_user.before_app_request
def before_request():
    """
    Attach user object to global context, display custom captcha form after certain failed attempts
    """
    g.user = current_user

    if session.get('failed',0) > 1 and cfg.RECAPTCHA_ENABLED:
        current_app.extensions['security'].login_form = ExtendedLoginForm
    else:
        current_app.extensions['security'].login_form = LoginForm

@bp_user.after_app_request
def after_app_request(response):
    """
    Record failed login attempts into the session
    """
    if request.path == '/login' and request.method == 'POST':
        #failed login
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
        #picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["name"]
    else:
        return "User email not available or not verified by Google.", 400
    if not users_email.endswith('syriaaccountability.org'):
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
@login_required
def account():
    """
    Main dashboard endpoint.
    """
    return render_template('dashboard.html')


@bp_user.route('/settings/')
@login_required
def settings():
    """Endpoint for user settings."""
    return render_template('settings.html')

@bp_user.route('/settings/save',methods=['PUT'])
@login_required
def save_settings():
    """API Endpoint to save user settings."""
    json = request.json.get('settings')
    dark = json.get('dark')
    user_id = current_user.id
    user = User.query.get(user_id)
    if not user:
        return 'Problem loading user', 417
    user.settings = {'dark': dark}
    user.save()
    return 'Settings Saved', 200

@bp_user.route('/settings/load',methods=['GET'])
@login_required
def load_settings():
    """API Endpoint to load user settings, in json format. """
    user_id = current_user.id

    user = User.query.get(user_id)

    if not user:
        return 'Problem loading user ', 417

    settings = user.settings or {}

    dark = settings.get('dark', 0)

    return Response(json.dumps({'dark':dark }), content_type='Application/json'), 200

@bp_user.route('/change-password/', methods=['GET', 'POST'])
@login_required
def change_password():
    """API Endpoint to handle user password change"""
    if request.method == 'POST':
        user = User.query.get(current_user.id)
        oldpass = request.form.get("oldpass")
        if not verify_password(oldpass, user.password):
            flash('Wrong password entered.')
        else:
            password = request.form.get('password')
            if password != '':
                user.password = hash_password(password)
                user.save()
                flash('Password changed successfully. ')
                return redirect('/dashboard')
    return render_template('change-password.html')


