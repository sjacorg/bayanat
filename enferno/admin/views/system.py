from __future__ import annotations

from typing import Any

from flask import Response, request
from flask.templating import render_template
from flask_babel import gettext
from flask_security.decorators import auth_required, current_user, roles_required

from enferno.admin.constants import Constants
from enferno.admin.models import (
    AppConfig,
    AtobInfo,
    AtoaInfo,
    BtobInfo,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    WorkflowStatus,
)
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import ConfigRequestModel
from enferno.utils.config_utils import ConfigManager
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
from . import admin, PER_PAGE


@admin.get("/system-administration/")
@auth_required(within=15, grace=0)
@roles_required("Admin")
def system_admin() -> str:
    """Endpoint for system administration."""
    return render_template("admin/system-administration.html")


@admin.get("/api/appconfig/")
@roles_required("Admin")
def api_app_config() -> Response:
    """
    Endpoint to get paged results of application configurations.

    Returns:
        - application configurations in JSON format.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    result = AppConfig.query.order_by(-AppConfig.id).paginate(
        page=page, per_page=per_page, count=True
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.get("/api/configuration/defaults/")
@roles_required("Admin")
def api_config_defaults() -> Response:
    """Returns default app configurations."""
    response = {
        "config": ConfigManager.get_all_default_configs(),
        "labels": dict(ConfigManager.CONFIG_LABELS),
    }
    return HTTPResponse.success(data=response)


@admin.get("/api/configuration/")
@roles_required("Admin")
def api_config() -> str:
    """Returns serialized app configurations."""
    response = {"config": ConfigManager.serialize(), "labels": dict(ConfigManager.CONFIG_LABELS)}
    return HTTPResponse.success(data=response)


@admin.put("/api/configuration/")
@roles_required("Admin")
@validate_with(ConfigRequestModel)
def api_config_write(
    validated_data: dict,
) -> Response:
    """
    Writes app configurations.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    conf = validated_data.get("conf")

    if ConfigManager.write_config(conf):
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.SYSTEM_SETTINGS_CHANGE,
            "System Settings Changed",
            f"System settings have been updated by {current_user.username} successfully.",
        )
        return HTTPResponse.success(
            message="Configuration saved. Secrets excluded from revision history."
        )
    else:
        return HTTPResponse.error("Unable to Save Configuration", status=500)


@admin.post("/api/reload/")
@roles_required("Admin")
def api_app_reload() -> Response:
    """
    Reloads Flask via uWSGI touch-reload and restarts Celery via systemd.
    In dev mode, config is saved but reload must be done manually.
    """
    from enferno.tasks.maintenance import reload_app, restart_celery

    reloaded = reload_app()
    restart_celery()
    if reloaded:
        return HTTPResponse.success(message="Reloading Bayanat")
    return HTTPResponse.success(message="Configuration saved. Please restart Bayanat manually.")


@admin.app_template_filter("to_config")
def to_config(items: list) -> list[dict[str, Any]]:
    """
    Filter to get translated config items.

    Args:
        - items: list of config items.

    Returns:
        - translated config items.
    """
    output = [{"en": item, "tr": gettext(item)} for item in items]
    return output


@admin.app_template_filter("get_data")
def get_data(table: str) -> list[dict[str, Any]] | list[dict[str, dict[str, Any | str]]] | None:
    """
    Filter to get data from an info/status table.

    Args:
        - table: table name. (atob, atoa, itoa, btob, itob, itoi, workflow_status)

    Returns:
        - data from the table.
    """
    if table == "atob":
        items = AtobInfo.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    if table == "atoa":
        items = AtoaInfo.query.all()
        items_list = [
            {
                "en": {"text": item.title or "", "revtext": item.reverse_title or ""},
                "tr": {"text": item.title_tr or "", "revtext": item.reverse_title_tr or ""},
            }
            for item in items
        ]
        return items_list

    if table == "itoa":
        items = ItoaInfo.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    if table == "btob":
        items = BtobInfo.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    if table == "itob":
        items = ItobInfo.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    if table == "itoi":
        items = ItoiInfo.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    if table == "workflow_status":
        items = WorkflowStatus.query.all()
        return [{"en": item.title, "tr": item.title_tr or ""} for item in items]

    return None


import json
import subprocess
from pathlib import Path

from enferno.extensions import rds
from enferno.tasks.maintenance import UPDATE_CACHE_KEY, _current_version

UPDATE_STATE_FILE = "/opt/bayanat/state/update.json"
TERMINAL_PHASES = {"SUCCESS", "ROLLED_BACK", "NEEDS_INTERVENTION", "IDLE"}


def _idle_status(current):
    return {
        "phase": "IDLE",
        "phase_label": "No update in progress",
        "running": False,
        "target": None,
        "previous": None,
        "snapshot": None,
        "started_at": None,
        "updated_at": None,
        "progress_text": None,
        "error": None,
        "current": current,
    }


@admin.get("/api/updates/available")
@roles_required("Admin")
def api_updates_available() -> Response:
    """Return the latest cached GitHub release info."""
    raw = rds.get(UPDATE_CACHE_KEY)
    cached = {}
    if raw:
        try:
            cached = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
        except Exception:
            cached = {}
    payload = {
        "current": _current_version(),
        "latest": cached.get("latest"),
        "release_notes_url": cached.get("release_notes_url"),
        "checked_at": cached.get("checked_at"),
    }
    return HTTPResponse.success(data=payload)


@admin.post("/api/updates/start")
@roles_required("Admin")
def api_updates_start() -> Response:
    """Launch `bayanat update` out-of-process via the sudoers-granted wrapper."""
    try:
        subprocess.run(
            ["sudo", "-n", "/usr/local/sbin/bayanat-start-update"],
            check=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return HTTPResponse.error("Update start timed out", status=504)
    except subprocess.CalledProcessError as e:
        return HTTPResponse.error(f"Failed to start update: {e}", status=500)
    return HTTPResponse.success(data={"status": "started"})


@admin.get("/api/updates/status")
@roles_required("Admin")
def api_updates_status() -> Response:
    """Return the current update state (from the CLI-written JSON file)."""
    current = _current_version()
    path = Path(UPDATE_STATE_FILE)
    if not path.exists():
        return HTTPResponse.success(data=_idle_status(current))
    try:
        state = json.loads(path.read_text())
    except Exception:
        return HTTPResponse.success(data=_idle_status(current))
    state["running"] = state.get("phase") not in TERMINAL_PHASES
    state["current"] = current
    return HTTPResponse.success(data=state)
