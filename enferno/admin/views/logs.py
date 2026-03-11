from __future__ import annotations

import os
from datetime import datetime

from flask import Response, request, current_app, json, send_from_directory
from flask.templating import render_template
from flask_security.decorators import roles_required
from werkzeug.utils import safe_join, secure_filename

from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_log_filenames, get_logger
from . import admin

logger = get_logger()

# Logging


@admin.route("/logs/")
@roles_required("Admin")
def logs() -> str:
    """
    Endpoint to render the logs backend page.

    Returns:
        - html page of the logs backend.
    """
    return render_template("admin/system-logs.html")


@admin.route("/api/logfiles/")
@roles_required("Admin")
def api_logfiles() -> str:
    """Endpoint to return a dict containing list of log file names and
    the date of the current open log."""
    files = get_log_filenames()
    # read the current log file's first line and extract the date
    log_dir = current_app.config.get("LOG_DIR")
    log_file = current_app.config.get("LOG_FILE")
    log_path = os.path.join(log_dir, log_file)
    date = None
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            timestamp = json.loads(f.readline().strip())["timestamp"]
            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    return HTTPResponse.success(data={"files": files, "date": date})


@admin.route("/api/logs/")
@roles_required("Admin")
def api_logs() -> Response:
    """Endpoint to return the content of the log file."""
    filename = request.args.get("filename", current_app.config.get("LOG_FILE"))
    log_file = secure_filename(filename)
    log_dir = current_app.config.get("LOG_DIR")
    if os.path.exists(safe_join(log_dir, log_file)):
        try:
            return send_from_directory(os.path.abspath(log_dir), log_file)
        except Exception as e:
            logger.error(f"Error sending log file: {e}", exc_info=True)
            return HTTPResponse.error("Error sending log file", status=500)
    else:
        return HTTPResponse.not_found("Log file not found")
