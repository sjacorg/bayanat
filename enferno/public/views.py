from flask import request, redirect, Blueprint, send_from_directory, Response
from typing import Optional
from enferno.utils.logging_utils import get_logger
from enferno.extensions import db

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


@bp_public.teardown_app_request
def shutdown_global_session(exception: Optional[Exception] = None) -> None:
    """Remove database session at the end of each request."""
    try:
        db.session.remove()
    except Exception as e:
        logger.error(e, exc_info=True)
