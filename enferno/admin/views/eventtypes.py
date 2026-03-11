from __future__ import annotations

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required

from enferno.admin.constants import Constants
from enferno.admin.models import Eventtype, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import EventtypeRequestModel
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


# EventType routes
@admin.route("/eventtypes/")
@roles_accepted("Admin", "Mod")
def eventtypes() -> str:
    """
    Endpoint to render event types backend

    Returns:
        - html template of the event types backend
    """
    return render_template("admin/eventtypes.html")


@admin.route("/api/eventtypes/")
def api_eventtypes() -> Response:
    """
    API endpoint to serve json feed of even types with paging support

    Returns:
        - json response of event types
    """
    query = []
    q = request.args.get("q", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    if q is not None:
        query.append(Eventtype.title.ilike("%" + q + "%"))

    typ = request.args.get("typ", None)
    if typ and typ in ["for_bulletin", "for_actor"]:
        query.append(getattr(Eventtype, typ) == True)
    result = (
        Eventtype.query.filter(*query)
        .order_by(Eventtype.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/eventtype/")
@roles_accepted("Admin", "Mod")
@validate_with(EventtypeRequestModel)
def api_eventtype_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an Event Type

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    eventtype = Eventtype()
    created = eventtype.from_json(validated_data["item"])
    if created.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            eventtype.to_mini(),
            "eventtype",
        )
        return HTTPResponse.created(
            message=f"Created Event #{eventtype.id}", data={"item": eventtype.to_dict()}
        )
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/eventtype/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(EventtypeRequestModel)
def api_eventtype_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an Event Type

    Args:
        - id: id of the event type.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    eventtype = Eventtype.query.get(id)
    if eventtype is None:
        return HTTPResponse.not_found("Event type not found")

    eventtype = eventtype.from_json(validated_data["item"])
    if eventtype.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            eventtype.to_mini(),
            "eventtype",
        )
        return HTTPResponse.success(message=f"Saved Event #{eventtype.id}")
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.delete("/api/eventtype/<int:id>")
@roles_required("Admin")
def api_eventtype_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an event type

    Args:
        - id: id of the event type.

    Returns:
        - success/error string based on the operation result.
    """
    eventtype = Eventtype.query.get(id)
    if eventtype is None:
        return HTTPResponse.not_found("Event type not found")

    if eventtype.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            eventtype.to_mini(),
            "eventtype",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Event Type Deleted",
            f"Event Type {eventtype.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Event Type #{eventtype.id}")
    else:
        return HTTPResponse.error("Error deleting Event Type", status=500)


@admin.post("/api/eventtype/import/")
@roles_required("Admin")
def api_eventtype_import() -> Response:
    """
    Endpoint to bulk import event types from a CSV file

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Eventtype.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error", status=400)
