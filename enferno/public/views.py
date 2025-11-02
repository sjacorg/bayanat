from flask import (
    request,
    redirect,
    Blueprint,
    send_from_directory,
    Response,
    jsonify,
    render_template,
)
import datetime
from typing import Optional
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db, limiter
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
@limiter.limit("15 per minute, 100 per hour")
def get_csrf_token() -> Response:
    """Get CSRF token for form submission."""
    token = generate_csrf()
    return jsonify({"csrf_token": token})


@bp_public.route("/maintenance")
def maintenance():
    """
    Display maintenance page. Only accessible when maintenance mode is active.

    Returns:
        Rendered maintenance template with 503 status code if maintenance is active,
        otherwise redirects to home page
    """
    from enferno.utils.maintenance import is_maintenance_mode, get_maintenance_details

    # Only show maintenance page if maintenance mode is actually enabled
    if not is_maintenance_mode():
        return redirect("/dashboard")

    details = get_maintenance_details()
    current_year = datetime.datetime.now().year
    return render_template("maintenance.html", details=details, current_year=current_year), 503


@bp_public.teardown_app_request
def shutdown_global_session(exception: Optional[Exception] = None) -> None:
    """Remove database session at the end of each request."""
    try:
        db.session.remove()
    except Exception as e:
        logger.error(e, exc_info=True)
