import os
from typing import Optional

from flask import Blueprint, Response, jsonify, redirect, request, send_from_directory
from flask_wtf.csrf import generate_csrf
from sqlalchemy import text

from enferno.extensions import db, limiter, rds
from enferno.utils.logging_utils import get_logger

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


@bp_public.route("/health")
@limiter.exempt
def health() -> Response:
    """Readiness probe used by the bayanat updater. Touches DB and Redis."""
    try:
        db.session.execute(text("SELECT 1"))
        rds.ping()
    except Exception as e:
        logger.error(f"health check failed: {e}")
        return jsonify({"status": "error", "error": str(e)[:120]}), 503
    version = os.environ.get("BAYANAT_VERSION") or _read_version_from_pyproject()
    return jsonify({"status": "ok", "version": version})


def _read_version_from_pyproject() -> Optional[str]:
    try:
        import tomllib

        with open("pyproject.toml", "rb") as fh:
            return tomllib.load(fh).get("project", {}).get("version")
    except Exception:
        return None


@bp_public.teardown_app_request
def shutdown_global_session(exception: Optional[Exception] = None) -> None:
    """Remove database session at the end of each request."""
    try:
        db.session.remove()
    except Exception as e:
        logger.error(e, exc_info=True)
