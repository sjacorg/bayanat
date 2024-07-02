from pathlib import Path
from typing import Literal, Optional

from flask import request, Response, Blueprint, json, send_from_directory
from flask.templating import render_template
from flask_security.decorators import auth_required, current_user, roles_required
from enferno.admin.models import Activity
from enferno.export.models import Export
from enferno.tasks import generate_export
from enferno.utils.http_response import HTTPResponse
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


@export.before_request
@auth_required("session")
def export_before_request() -> Optional[Response]:
    """Check user's permissions."""
    # check user's permissions
    if not (current_user.has_role("Admin") or current_user.can_export):
        return HTTPResponse.FORBIDDEN


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
def export_bulletins() -> (
    tuple[str, Literal[200]] | tuple[Literal["Error creating export request"], Literal[417]]
):
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

        return f"Export request created successfully, id:  {export_request.id} ", 200
    return "Error creating export request", 417


@export.post("/api/actor/export")
def export_actors() -> (
    tuple[str, Literal[200]] | tuple[Literal["Error creating export request"], Literal[417]]
):
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
        return f"Export request created successfully, id:  {export_request.id} ", 200
    return "Error creating export request", 417


@export.post("/api/incident/export")
def export_incidents() -> (
    tuple[str, Literal[200]] | tuple[Literal["Error creating export request"], Literal[417]]
):
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
        return f"Export request created successfully, id:  {export_request.id} ", 200
    return "Error creating export request", 417


@export.get("/api/export/<int:id>")
def api_export_get(id: t.id) -> Response | tuple[str, Literal[200]]:
    """
    Endpoint to get a single export.

    Args:
        - id: The id of the export.

    Returns:
        - The export in json format / success or error.
    """
    export = Export.query.get(id)

    if export is None:
        return HTTPResponse.NOT_FOUND
    else:
        return json.dumps(export.to_dict()), 200


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

    return Response(json.dumps(response), content_type="application/json")


@export.put("/api/exports/status")
@roles_required("Admin")
def change_export_status() -> (
    tuple[Literal["Please check request action"], Literal[417]]
    | tuple[Literal["Invalid export request id"], Literal[417]]
    | tuple[Literal["Export request does not exist"], Literal[404]]
    | tuple[Literal["Export request approval will be processed shortly."], Literal[200]]
    | tuple[Literal["Export request rejected."], Literal[200]]
    | None
):
    """
    endpoint to approve or reject an export request.

    Returns:
        - success / error based on the operation outcome.
    """
    action = request.json.get("action")
    if not action or action not in ["approve", "reject"]:
        return "Please check request action", 417
    export_id = request.json.get("exportId")

    if not export_id:
        return "Invalid export request id", 417
    export_request = Export.query.get(export_id)

    if not export_request:
        return "Export request does not exist", 404

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

            return "Export request approval will be processed shortly.", 200

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

            return "Export request rejected.", 200


@export.put("/api/exports/expiry")
@roles_required("Admin")
def update_expiry() -> (
    Response
    | tuple[Literal["Invalid expiry date"], Literal[417]]
    | tuple[str, Literal[200]]
    | tuple[Literal["Save failed"], Literal[417]]
):
    """
    endpoint to set expiry date of an approved export.

    Returns:
        - success / error based on the operation outcome
    """
    export_id = request.json.get("exportId")
    new_date = request.json.get("expiry")
    export_request = Export.query.get(export_id)

    if export_request.expired:
        return HTTPResponse.FORBIDDEN
    else:
        try:
            export_request.set_expiry(new_date)
        except Exception as e:
            return "Invalid expiry date", 417

        if export_request.save():
            return f"Updated Export #{export_id}", 200
        else:
            return "Save failed", 417


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
                return HTTPResponse.FORBIDDEN

        if not export_id or not export:
            return HTTPResponse.NOT_FOUND
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
            return HTTPResponse.REQUEST_EXPIRED

    except Exception as e:
        print(f"Unable to decrypt export request uid {e}")
        return HTTPResponse.NOT_FOUND
