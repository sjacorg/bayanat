from flask import request, redirect, Blueprint, send_from_directory, Response, jsonify
from typing import Optional
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db
from flask_wtf.csrf import generate_csrf

bp_public = Blueprint("public", __name__, static_folder="../static")

logger = get_logger()


@bp_public.route("/")
def index() -> Response:
    """Redirect root URL to dashboard."""
    return redirect("/dashboard")


@bp_public.route("/robots.txt")
def static_from_root() -> Response:
    """Serve robots.txt from static folder."""
    return send_from_directory(bp_public.static_folder, request.path[1:])


@bp_public.route("/csrf")
def get_csrf_token() -> Response:
    """Get CSRF token for form submission."""
    token = generate_csrf()
    return jsonify({"csrf_token": token})


@bp_public.teardown_app_request
def shutdown_global_session(exception: Optional[Exception] = None) -> None:
    """Remove database session at the end of each request."""
    try:
        db.session.remove()
    except Exception as e:
        logger.error(e, exc_info=True)
