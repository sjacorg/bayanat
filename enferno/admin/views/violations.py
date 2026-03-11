from __future__ import annotations

from flask import Response, request
from flask_security.decorators import current_user, roles_accepted, roles_required

from enferno.admin.constants import Constants
from enferno.admin.models import PotentialViolation, ClaimedViolation, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    PotentialViolationRequestModel,
    ClaimedViolationRequestModel,
)
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


@admin.route("/api/potentialviolation/", defaults={"page": 1})
@admin.route("/api/potentialviolation/<int:page>/")
def api_potentialviolations(page: int) -> Response:
    """
    API endpoint that feeds json data of potential violations with paging and search support

    Args:
        - page: page number to fetch.

    Returns:
        - json response of potential violations.
    """
    query = []
    q = request.args.get("q", None)
    per_page = request.args.get("per_page", PER_PAGE, int)
    if q is not None:
        query.append(PotentialViolation.title.ilike("%" + q + "%"))
    result = (
        PotentialViolation.query.filter(*query)
        .order_by(PotentialViolation.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": PER_PAGE,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/potentialviolation/")
@roles_accepted("Admin", "Mod")
@validate_with(PotentialViolationRequestModel)
def api_potentialviolation_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a potential violation

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    potentialviolation = PotentialViolation()
    potentialviolation = potentialviolation.from_json(validated_data["item"])
    if potentialviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            potentialviolation.to_mini(),
            "potentialviolation",
        )
        return HTTPResponse.created(
            message=f"Created Potential Violation #{potentialviolation.id}",
            data={"item": potentialviolation.to_dict()},
        )
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/potentialviolation/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(PotentialViolationRequestModel)
def api_potentialviolation_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a potential violation

    Args:
        - id: id of the item to update.

    Returns:
        - success/error string based on the operation result.
    """
    potentialviolation = PotentialViolation.query.get(id)
    if potentialviolation is None:
        return HTTPResponse.not_found("Potential Violation not found")

    potentialviolation = potentialviolation.from_json(validated_data["item"])
    if potentialviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            potentialviolation.to_mini(),
            "potentialviolation",
        )
        return HTTPResponse.success(message=f"Saved Potential Violation #{potentialviolation.id}")
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.delete("/api/potentialviolation/<int:id>")
@roles_required("Admin")
def api_potentialviolation_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a potential violation

    Args:
        - id: id of the item to delete.

    Returns:
        - success/error string based on the operation result.
    """
    potentialviolation = PotentialViolation.query.get(id)
    if potentialviolation is None:
        return HTTPResponse.not_found("Potential Violation not found")

    if potentialviolation.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            potentialviolation.to_mini(),
            "potentialviolation",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Potential Violation Deleted",
            f"Potential Violation {potentialviolation.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Potential Violation #{potentialviolation.id}")
    else:
        return HTTPResponse.error("Error deleting Potential Violation", status=500)


@admin.post("/api/potentialviolation/import/")
@roles_required("Admin")
def api_potentialviolation_import() -> Response:
    """
    Endpoint to import potential violations from csv file

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        PotentialViolation.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error", status=400)


@admin.route("/api/claimedviolation/", defaults={"page": 1})
@admin.route("/api/claimedviolation/<int:page>")
def api_claimedviolations(page: int) -> Response:
    """
    API endpoint to feed json items of claimed violations, supports paging and search

    Args:
        - page: page number to fetch.

    Returns:
        - json response of claimed violations.
    """
    query = []
    q = request.args.get("q", None)
    per_page = request.args.get("per_page", PER_PAGE, int)
    if q is not None:
        query.append(ClaimedViolation.title.ilike("%" + q + "%"))
    result = (
        ClaimedViolation.query.filter(*query)
        .order_by(ClaimedViolation.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": PER_PAGE,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/claimedviolation/")
@roles_accepted("Admin", "Mod")
@validate_with(ClaimedViolationRequestModel)
def api_claimedviolation_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a claimed violation.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    claimedviolation = ClaimedViolation()
    claimedviolation = claimedviolation.from_json(validated_data["item"])
    if claimedviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            claimedviolation.to_mini(),
            "claimedviolation",
        )
        return HTTPResponse.created(
            message=f"Created Claimed Violation #{claimedviolation.id}",
            data={"item": claimedviolation.to_dict()},
        )
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.put("/api/claimedviolation/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(ClaimedViolationRequestModel)
def api_claimedviolation_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a claimed violation.

    Args:
        - id: id of the item to update.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    claimedviolation = ClaimedViolation.query.get(id)
    if claimedviolation is None:
        return HTTPResponse.not_found("Claimed Violation not found")

    claimedviolation = claimedviolation.from_json(validated_data["item"])
    if claimedviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            claimedviolation.to_mini(),
            "claimedviolation",
        )
        return HTTPResponse.success(message=f"Saved Claimed Violation #{claimedviolation.id}")
    else:
        return HTTPResponse.error("Save Failed", status=500)


@admin.delete("/api/claimedviolation/<int:id>")
@roles_required("Admin")
def api_claimedviolation_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a claimed violation

    Args:
        - id: id of the item to delete.

    Returns:
        - success/error string based on the operation result.
    """
    claimedviolation = ClaimedViolation.query.get(id)
    if claimedviolation is None:
        return HTTPResponse.not_found("Claimed Violation not found")

    if claimedviolation.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            claimedviolation.to_mini(),
            "claimedviolation",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Claimed Violation Deleted",
            f"Claimed Violation {claimedviolation.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Claimed Violation #{claimedviolation.id}")
    else:
        return HTTPResponse.error("Error deleting Claimed Violation", status=500)


@admin.post("/api/claimedviolation/import/")
@roles_required("Admin")
def api_claimedviolation_import() -> Response:
    """
    Endpoint to import claimed violations from a CSV file.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        ClaimedViolation.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error")
