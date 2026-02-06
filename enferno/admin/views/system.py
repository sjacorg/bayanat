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
    from flask import current_app

    conf = validated_data.get("conf")

    if ConfigManager.write_config(conf):
        # Force immediate reload in ConfigManager singleton
        ConfigManager.instance().force_reload()

        # Check if any static keys changed
        static_changed = ConfigManager.detect_static_changes(current_app)

        # Sync Celery worker config
        from enferno.tasks import refresh_celery_config

        refresh_celery_config.delay()

        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.SYSTEM_SETTINGS_CHANGE,
            "System Settings Changed",
            f"System settings have been updated by {current_user.username} successfully.",
        )

        msg = "Configuration saved and applied."
        if static_changed:
            labels = [ConfigManager.CONFIG_LABELS.get(k, k) for k in static_changed]
            msg += " Restart required for: " + ", ".join(sorted(labels))

        return HTTPResponse.success(
            message=msg,
            data={
                "restart_required": bool(static_changed),
                "static_keys": list(static_changed),
            },
        )
    else:
        return HTTPResponse.error("Unable to Save Configuration", status=500)


@admin.post("/api/reload/")
@roles_required("Admin")
def api_app_reload() -> Response:
    """Refreshes configuration from config.json without restart."""
    ConfigManager.instance().force_reload()

    from enferno.tasks import refresh_celery_config

    refresh_celery_config.delay()
    return HTTPResponse.success(message="Configuration refreshed.")


@admin.post("/api/restart/")
@roles_required("Admin")
def api_app_restart() -> Response:
    """Full process restart for infrastructure/security config changes."""
    from enferno.tasks import reload_app, reload_celery

    reload_app()
    reload_celery.delay()
    return HTTPResponse.success(message="Restarting Bayanat...")


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
