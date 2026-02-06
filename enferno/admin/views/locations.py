from __future__ import annotations

from typing import Optional

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required

from enferno.admin.constants import Constants
from enferno.admin.models import Location, LocationAdminLevel, LocationType, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    LocationQueryRequestModel,
    LocationRequestModel,
    LocationAdminLevelRequestModel,
    LocationAdminLevelReorderRequestModel,
    LocationTypeRequestModel,
)
from enferno.extensions import rds
from enferno.tasks import regenerate_locations
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE

logger = get_logger()

# locations routes


@admin.route("/locations/", defaults={"id": None})
@admin.route("/locations/<int:id>")
@roles_accepted("Admin", "Mod", "DA")
def locations(id: Optional[t.id]) -> str:
    """
    Endpoint for locations management.

    Args:
        - id: id of the location.

    Returns:
        - html template of the locations backend page.
    """
    return render_template("admin/locations.html")


@admin.route("/api/locations/", methods=["POST", "GET"])
@validate_with(LocationQueryRequestModel)
def api_locations(validated_data: dict) -> Response:
    """
    Returns locations in JSON format, allows search and paging.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - json response of locations.
    """
    q = validated_data.get("q", {})
    su = SearchUtils(q, cls="location")
    query = su.get_query()

    options = validated_data.get("options")
    page = options.get("page", 1)
    per_page = options.get("itemsPerPage", PER_PAGE)

    result = (
        Location.query.filter(*query)
        .order_by(Location.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return HTTPResponse.success(data=response)


@admin.post("/api/location/")
@roles_accepted("Admin", "Mod", "DA")
@validate_with(LocationRequestModel)
def api_location_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint for creating locations.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    if not current_user.roles_in(["Admin", "Mod"]) and not current_user.can_edit_locations:
        return HTTPResponse.forbidden("User not allowed to create Locations")

    location = Location()
    location = location.from_json(validated_data["item"])

    if location.save():
        location.full_location = location.get_full_string()
        location.id_tree = location.get_id_tree()
        location.create_revision()
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            location.to_mini(),
            "location",
        )
        return HTTPResponse.created(
            message=f"Created Location #{location.id}", data={"item": location.to_dict()}
        )
    return HTTPResponse.error("Failed to create Location")


@admin.put("/api/location/<int:id>")
@roles_accepted("Admin", "Mod", "DA")
@validate_with(LocationRequestModel)
def api_location_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint for updating locations.

    Args:
        - id: id of the location.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    if not current_user.roles_in(["Admin", "Mod"]) and not current_user.can_edit_locations:
        return HTTPResponse.forbidden("User not allowed to create Locations")

    location = Location.query.get(id)
    if location is not None:
        location = location.from_json(validated_data["item"])
        # we need to commit this change to db first, to utilize CTE
        if location.save():
            # then update the location full string
            location.full_location = location.get_full_string()
            location.id_tree = location.get_id_tree()
            location.create_revision()
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                location.to_mini(),
                "location",
            )
            return HTTPResponse.success(message=f"Saved Location #{location.id}")
        else:
            return HTTPResponse.error("Save Failed", status=500)
    else:
        return HTTPResponse.not_found("Location not found")


@admin.delete("/api/location/<int:id>")
@roles_required("Admin")
def api_location_delete(
    id: t.id,
) -> Response:
    """Endpoint for deleting locations.

    Args:
        - id: id of the location.

    Returns:
        - success/error string based on the operation result.
    """
    location = Location.query.get(id)
    if location is None:
        return HTTPResponse.not_found("Location not found")

    if location.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            location.to_mini(),
            "location",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Location Deleted",
            f"Location {location.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Deleted Location #{location.id}")
    else:
        return HTTPResponse.error("Error deleting Location", status=500)


@admin.post("/api/location/import/")
@roles_required("Admin")
def api_location_import() -> Response:
    """Endpoint for importing locations.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Location.import_csv(request.files.get("csv"))
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error")


# get one location
@admin.get("/api/location/<int:id>")
def api_location_get(id: t.id) -> Response:
    """
    Endpoint to get a single location

    Args:
        - id: id of the location.

    Returns:
        - location in json format / success or error.
    """
    location = Location.query.get(id)

    if location is None:
        return HTTPResponse.not_found("Location not found")
    else:
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_SUCCESS,
            location.to_mini(),
            "location",
        )
        return HTTPResponse.success(data=location.to_dict())


@admin.post("/api/location/regenerate/")
@roles_required("Admin")
def api_location_regenerate() -> Response:
    """Endpoint for regenerating locations."""
    if rds.get(Location.CELERY_FLAG):
        return HTTPResponse.error(
            "Full Location texts regeneration already in progress, try again in a few moments.",
            status=429,
        )
    regenerate_locations.delay()
    return HTTPResponse.success(
        message="Full Location texts regeneration is queued successfully. This task will need a few moments to complete."
    )


@admin.route("/component-data/", defaults={"id": None})
@roles_required("Admin")
def locations_config(id: Optional[t.id]):
    """Endpoint for locations configurations."""
    return render_template("admin/component-data.html")


# location admin level endpoints
@admin.route("/api/location-admin-levels/", methods=["GET", "POST"])
def api_location_admin_levels() -> Response:
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = request.args.get("q")
    if query:
        result = (
            LocationAdminLevel.query.filter(LocationAdminLevel.title.ilike(f"%{query}%"))
            .order_by(-LocationAdminLevel.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = LocationAdminLevel.query.order_by(-LocationAdminLevel.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/location-admin-level")
@roles_required("Admin")
@validate_with(LocationAdminLevelRequestModel)
def api_location_admin_level_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a location admin level

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    admin_level = LocationAdminLevel()
    admin_level.from_json(validated_data["item"])
    all_codes = [level.code for level in LocationAdminLevel.query.all()]
    max_code = max(all_codes) if len(all_codes) > 0 else 0

    if admin_level.code is None:
        admin_level.code = max_code + 1
    elif admin_level.code != max_code + 1:
        return HTTPResponse.error(
            "Code must be unique and one more than the highest code", status=400
        )

    if admin_level.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            admin_level.to_mini(),
            "adminlevel",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{admin_level.id}",
            data={"item": admin_level.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/location-admin-level/<int:id>")
@roles_required("Admin")
@validate_with(LocationAdminLevelRequestModel)
def api_location_admin_level_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a location admin level

    Args:
        - id: id of the location admin level.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    admin_level = LocationAdminLevel.query.get(id)
    if admin_level:
        if validated_data["item"]["code"] != admin_level.code:
            return HTTPResponse.error("Cannot change the code of a level", status=400)
        admin_level.from_json(validated_data["item"])
        if admin_level.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                admin_level.to_mini(),
                "adminlevel",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("Location Admin Level not found")


@admin.delete("/api/location-admin-level/<int:id>")
@roles_required("Admin")
def api_location_admin_level_delete(id: t.id) -> Response:
    """
    Endpoint to delete a location admin level.

    Args:
        - id: id of the location admin level.

    Returns:
        - success/error string based on the operation result.
    """
    if id in [1, 2, 3] or LocationAdminLevel.query.count() <= 3:
        return HTTPResponse.error("Cannot delete the first 3 levels", status=400)
    admin_level = LocationAdminLevel.query.get(id)
    if admin_level is None:
        return HTTPResponse.not_found("Location Admin Level not found")
    if Location.query.filter(Location.admin_level_id == id).count() > 0:
        return HTTPResponse.error("Cannot delete a level that is in use by a location", status=409)

    max_code = max([level.code for level in LocationAdminLevel.query.all()])
    if admin_level.code != max_code:
        return HTTPResponse.error("Only the highest level can be deleted.", status=400)

    if admin_level.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            admin_level.to_mini(),
            "adminlevel",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Location Admin Level Deleted",
            f"Location Admin Level {admin_level.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Location Admin Level Deleted #{admin_level.id}")
    else:
        return HTTPResponse.error("Error deleting Location Admin Level", status=500)


@admin.post("/api/location-admin-levels/reorder")
@roles_required("Admin")
@validate_with(LocationAdminLevelReorderRequestModel)
def api_location_admin_levels_reorder(validated_data: dict) -> Response:
    """
    Endpoint to reorder location admin levels.
    """
    new_order = validated_data.get("order")
    try:
        LocationAdminLevel.reorder(new_order)
    except Exception as e:
        logger.error(f"Failed to reorder location admin levels: {str(e)}", exc_info=True)
        return HTTPResponse.error(
            "An internal error occurred while reordering location admin levels", status=500
        )
    return HTTPResponse.success(
        message="Updated, user should regenerate full locations from system settings"
    )


# location type endpoints
@admin.route("/api/location-types/", methods=["GET", "POST"])
def api_location_types() -> Response:
    """
    Endpoint to get location types with paging support

    Returns:
        - json response of location types.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = request.args.get("q")
    if query:
        result = (
            LocationType.query.filter(LocationType.title.ilike(f"%{query}%"))
            .order_by(-LocationType.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = LocationType.query.order_by(-LocationType.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/location-type")
@roles_required("Admin")
@validate_with(LocationTypeRequestModel)
def api_location_type_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a location type

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    location_type = LocationType()
    location_type.from_json(validated_data["item"])

    if location_type.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            location_type.to_mini(),
            "locationtype",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{location_type.id}",
            data={"item": location_type.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/location-type/<int:id>")
@roles_required("Admin")
@validate_with(LocationTypeRequestModel)
def api_location_type_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a location type

    Args:
        - id: id of the location type.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    location_type = LocationType.query.get(id)

    if location_type:
        location_type.from_json(validated_data.get("item"))
        if location_type.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                location_type.to_mini(),
                "locationtype",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("Location Type not found")


@admin.delete("/api/location-type/<int:id>")
@roles_required("Admin")
def api_location_type_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a location type.

    Args:
        - id: id of the location type.

    Returns:
        - success/error string based on the operation result.
    """
    location_type = LocationType.query.get(id)
    if location_type is None:
        return HTTPResponse.not_found("Location Type not found")

    if location_type.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            location_type.to_mini(),
            "locationtype",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Location Type Deleted",
            f"Location Type {location_type.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Location Type Deleted #{location_type.id}")
    else:
        return HTTPResponse.error("Error deleting Location Type", status=500)
