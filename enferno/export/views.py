from pathlib import Path
from typing import Literal, Optional

from flask import current_app, request, Response, Blueprint, json, send_from_directory
from flask.templating import render_template
from flask_security.decorators import auth_required, current_user, roles_required
from enferno.admin.constants import Constants
from enferno.admin.models import Activity
from enferno.admin.models.Notification import Notification
from enferno.export.models import Export
from enferno.tasks import generate_export
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
import enferno.utils.typing as t

export = Blueprint(
    "export",
    __name__,
    static_folder="../static",
    template_folder="../export/templates",
    cli_group=None,
    url_prefix="/export",
)

PER_PAGE = 30

logger = get_logger()


@export.before_request
@auth_required("session")
def export_before_request() -> Optional[Response]:
    """Check user's permissions."""
    # check user's permissions
    if not (current_user.has_role("Admin") or current_user.can_export):
        return HTTPResponse.forbidden("Forbidden")


@export.route("/dashboard/")
@export.get("/dashboard/<int:id>")
def exports_dashboard(id: Optional[t.id] = None) -> str:
    """
    Endpoint to render the exports dashboard.

    Args:
        - id: Optional export id.

    Returns:
        - The html page of the exports dashboard.
    """
    return render_template("export-dashboard.html")


@export.post("/api/bulletin/export")
def export_bulletins() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("bulletin", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (bulletin) request {export_request.id} has been created by {current_user.username} successfully.",
        )

        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.post("/api/actor/export")
def export_actors() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("actor", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (actor) request {export_request.id} has been created by {current_user.username} successfully.",
        )

        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.post("/api/incident/export")
def export_incidents() -> Response:
    """
    just creates an export request.

    Returns:
        - success code / failure if something goes wrong.
    """
    # create an export request
    export_request = Export()
    export_request.from_json("incident", request.json)
    if export_request.save():
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            export_request.to_mini(),
            Export.__table__.name,
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.NEW_EXPORT,
            "New Export Request",
            f"Export (incident) request {export_request.id} has been created by {current_user.username} successfully.",
        )
        return HTTPResponse.created(
            message=f"Export request created successfully, id:  {export_request.id} ",
            data={"item": export_request.to_dict()},
        )
    return HTTPResponse.error("Error creating export request", status=417)


@export.get("/api/export/<int:id>")
def api_export_get(id: t.id) -> Response:
    """
    Endpoint to get a single export.

    Args:
        - id: The id of the export.

    Returns:
        - The export in json format / success or error.
    """
    export = Export.query.get(id)

    if export is None:
        return HTTPResponse.not_found("Export not found")
    else:
        return HTTPResponse.success(data=export.to_dict(), message="Export retrieved successfully")


@export.post("/api/exports/")
def api_exports() -> Response:
    """
    API endpoint to feed export request items in josn format - supports paging
    and generated based on user role.

    Returns:
        - successful json feed or error
    """
    page = request.json.get("page", 1)
    per_page = request.json.get("per_page", PER_PAGE)

    if current_user.has_role("Admin"):
        result = Export.query.order_by(-Export.id).paginate(
            page=page, per_page=per_page, count=True
        )

    else:
        # if a normal authenticated user, get own export requests only
        result = (
            Export.query.filter(Export.requester_id == current_user.id)
            .order_by(-Export.id)
            .paginate(page=page, per_page=per_page, count=True)
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": PER_PAGE,
        "total": result.total,
    }

    return HTTPResponse.success(data=response)


@export.put("/api/exports/status")
@roles_required("Admin")
def change_export_status() -> Response:
    """
    endpoint to approve or reject an export request.

    Returns:
        - success / error based on the operation outcome.
    """
    action = request.json.get("action")
    if not action or action not in ["approve", "reject"]:
        return HTTPResponse.error("Please check request action", status=417)
    export_id = request.json.get("exportId")

    if not export_id:
        return HTTPResponse.error("Invalid export request id", status=417)
    export_request = Export.query.get(export_id)

    if not export_request:
        return HTTPResponse.not_found("Export request does not exist")

    if action == "approve":
        export_request = export_request.approve()
        if export_request.save():
            # record activity
            Activity.create(
                current_user,
                Activity.ACTION_APPROVE_EXPORT,
                Activity.STATUS_SUCCESS,
                export_request.to_mini(),
                Export.__table__.name,
            )
            # implement celery task chaining
            res = generate_export(export_id)
            # not sure if there is a scenario where the result has no uuid
            # store export background task id, to be used for fetching progress
            export_request.uuid = res.id
            export_request.save()

            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.APPROVE_EXPORT,
                "Export Request Approved",
                f"Export request {export_request.id} has been approved by {current_user.username} successfully.",
            )

            return HTTPResponse.success(
                message="Export request approval will be processed shortly."
            )

    if action == "reject":
        export_request = export_request.reject()
        if export_request.save():
            # record activity
            Activity.create(
                current_user,
                Activity.ACTION_REJECT_EXPORT,
                Activity.STATUS_SUCCESS,
                export_request.to_mini(),
                Export.__table__.name,
            )

            return HTTPResponse.success(message="Export request rejected.")


@export.put("/api/exports/expiry")
@roles_required("Admin")
def update_expiry() -> Response:
    """
    endpoint to set expiry date of an approved export.

    Returns:
        - success / error based on the operation outcome
    """
    export_id = request.json.get("exportId")
    new_date = request.json.get("expiry")
    export_request = Export.query.get(export_id)

    if export_request.expired:
        return HTTPResponse.forbidden("Forbidden")
    else:
        try:
            export_request.set_expiry(new_date)
        except Exception as e:
            return HTTPResponse.error("Invalid expiry date", status=417)

        if export_request.save():
            return HTTPResponse.success(message=f"Updated Export #{export_id}")
        else:
            return HTTPResponse.error("Save failed", status=417)


@export.get("/api/exports/download")
def download_export_file() -> Response:
    """
    Endpoint to Download an export file. Expects the export id as a query parameter.

    Returns:
        - The file to download or access denied response if the export has expired.
    """
    uid = request.args.get("exportId")

    try:
        export_id = Export.decrypt_unique_id(uid)
        export = Export.query.get(export_id)

        # check permissions for download
        # either admin or user is requester
        if not current_user.has_role("Admin"):
            if current_user.id != export.requester.id:
                return HTTPResponse.forbidden("Forbidden")

        if not export_id or not export:
            return HTTPResponse.not_found("Export not found")
        # check expiry
        if not export.expired:
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_DOWNLOAD,
                Activity.STATUS_SUCCESS,
                export.to_mini(),
                Export.__table__.name,
            )
            return send_from_directory(
                f"{Path(*Export.export_dir.parts[1:])}", f"{export.file_id}.zip"
            )
        else:
            return HTTPResponse.error("Request expired", status=410)

    except Exception as e:
        logger.error(f"Unable to decrypt export request uid {e}")
        return HTTPResponse.not_found("Unable to decrypt export request uid")
