from __future__ import annotations

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import desc

from enferno.admin.constants import Constants
from enferno.admin.models import Source, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import SourceRequestModel
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


# Sources routes
@admin.route("/sources/")
@roles_accepted("Admin", "Mod")
def sources() -> str:
    """
    Endpoint to render sources backend page.

    Returns:
        - html template of the sources backend page.
    """
    return render_template("admin/sources.html")


@admin.route("/api/sources/")
def api_sources() -> Response:
    """

    API Endpoint to feed json data of sources, supports paging and search.

    Returns:
        - json response of sources.
    """
    q = request.args.get("q")
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = Source.query

    if q:
        words = q.split(" ")
        for word in words:
            query = query.filter(Source.title.ilike(f"%{word}%"))

        sources = query.all()
        children = Source.get_children(sources)
        ids = {source.id for source in sources + children}

        query = Source.query.filter(Source.id.in_(ids))

    result = query.order_by(desc(Source.id)).paginate(page=page, per_page=per_page, error_out=False)

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/source/")
@roles_accepted("Admin", "Mod")
@validate_with(SourceRequestModel)
def api_source_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a source.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    source = Source()
    source = source.from_json(validated_data["item"])
    if source.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            source.to_mini(),
            "source",
        )
        return HTTPResponse.created(
            message=f"Created Source #{source.id}", data={"item": source.to_dict()}
        )
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/source/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(SourceRequestModel)
def api_source_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a source.

    Args:
        - id: id of the item to update.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    source = Source.query.get(id)
    if source is None:
        return HTTPResponse.not_found("Source not found")

    source = source.from_json(validated_data["item"])
    if source.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            source.to_mini(),
            "source",
        )
        return HTTPResponse.success(message=f"Saved Source #{source.id}")
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.delete("/api/source/<int:id>")
@roles_required("Admin")
def api_source_delete(
    id: t.id,
) -> Response:
    """
    Endopint to delete a source item.

    Args:
        - id: id of the item to delete.

    Returns:
        - success/error string based on the operation result.
    """
    source = Source.query.get(id)
    if source is None:
        return HTTPResponse.not_found("Source not found")

    if source.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            source.to_mini(),
            "source",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Source Deleted",
            f"Source {source.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Source #{source.id}")
    else:
        return HTTPResponse.error("Error deleting Source", status=500)


@admin.post("/api/source/import/")
@roles_required("Admin")
def api_source_import() -> Response:
    """
    Endpoint to import sources from CSV data.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Source.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error")
