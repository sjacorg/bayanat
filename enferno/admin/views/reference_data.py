from __future__ import annotations

from flask import Response, request
from flask_security.decorators import current_user, roles_required
from sqlalchemy import or_

from enferno.admin.constants import Constants
from enferno.admin.models import Country, Ethnography, Dialect, IDNumberType, Activity
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    CountryRequestModel,
    ComponentDataMixinRequestModel,
)
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


@admin.route("/api/countries/", methods=["GET", "POST"])
def api_countries() -> Response:
    """
    Endpoint to get countries with paging support.

    Returns:
        - json response of countries.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    q = request.args.get("q")
    if q:
        result = (
            Country.query.filter(
                or_(Country.title.ilike(f"%{q}%"), Country.title_tr.ilike(f"%{q}%"))
            )
            .order_by(-Country.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = Country.query.order_by(-Country.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/country")
@roles_required("Admin")
@validate_with(CountryRequestModel)
def api_country_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a country.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    country = Country()
    country.from_json(validated_data["item"])

    if country.save():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            country.to_mini(),
            "country",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{country.id}", data={"item": country.to_dict()}
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/country/<int:id>")
@roles_required("Admin")
@validate_with(CountryRequestModel)
def api_country_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a country.

    Args:
        - id: id of the country.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    country = Country.query.get(id)

    if country:
        country.from_json(validated_data.get("item"))
        if country.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                country.to_mini(),
                "country",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("Country not found")


@admin.delete("/api/country/<int:id>")
@roles_required("Admin")
def api_country_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a country.

    Args:
        - id: id of the country.

    Returns:
        - success/error string based on the operation result.
    """
    country = Country.query.get(id)
    if country is None:
        return HTTPResponse.not_found("Country not found")

    if country.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            country.to_mini(),
            "country",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Country Deleted",
            f"Country {country.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Country Deleted #{country.id}")
    else:
        return HTTPResponse.error("Error deleting Country", status=500)


@admin.route("/api/ethnographies/", methods=["GET", "POST"])
def api_ethnographies() -> Response:
    """
    Endpoint to get ethnographies with paging support.

    Returns:
        - json response of ethnographies.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    q = request.args.get("q")
    if q:
        result = (
            Ethnography.query.filter(
                or_(Ethnography.title.ilike(f"%{q}%"), Ethnography.title_tr.ilike(f"%{q}%"))
            )
            .order_by(-Ethnography.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = Ethnography.query.order_by(-Ethnography.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/ethnography")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_ethnography_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an ethnography.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    ethnography = Ethnography()
    ethnography.from_json(validated_data["item"])

    if ethnography.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            ethnography.to_mini(),
            "ethnography",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{ethnography.id}",
            data={"item": ethnography.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/ethnography/<int:id>")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_ethnography_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an ethnography.

    Args:
        - id: id of the ethnography.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    ethnography = Ethnography.query.get(id)

    if ethnography:
        ethnography.from_json(validated_data.get("item"))
        if ethnography.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                ethnography.to_mini(),
                "ethnography",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("Ethnography not found")


@admin.delete("/api/ethnography/<int:id>")
@roles_required("Admin")
def api_ethnography_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an ethnography

    Args:
        - id: id of the ethnography.

    Returns:
        - success/error string based on the operation result.
    """
    ethnography = Ethnography.query.get(id)
    if ethnography is None:
        return HTTPResponse.not_found("Ethnography not found")

    if ethnography.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            ethnography.to_mini(),
            "ethnography",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Ethnography Deleted",
            f"Ethnography {ethnography.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Ethnography Deleted #{ethnography.id}")
    else:
        return HTTPResponse.error("Error deleting Ethnography", status=500)


@admin.route("/api/dialects/", methods=["GET", "POST"])
def api_dialects() -> Response:
    """
    Returns Dialects in JSON format, allows search and paging.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    q = request.args.get("q")
    if q:
        result = (
            Dialect.query.filter(
                or_(Dialect.title.ilike(f"%{q}%"), Dialect.title_tr.ilike(f"%{q}%"))
            )
            .order_by(-Dialect.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = Dialect.query.order_by(-Dialect.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/dialect")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_dialect_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a dialect.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    dialect = Dialect()
    dialect.from_json(validated_data["item"])

    if dialect.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            dialect.to_mini(),
            "dialect",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{dialect.id}", data={"item": dialect.to_dict()}
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/dialect/<int:id>")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_dialect_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a dialect.

    Args:
        - id: id of the dialect.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    dialect = Dialect.query.get(id)

    if dialect:
        dialect.from_json(validated_data.get("item"))
        if dialect.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                dialect.to_mini(),
                "dialect",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("Dialect not found")


@admin.delete("/api/dialect/<int:id>")
@roles_required("Admin")
def api_dialect_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a dialect.

    Args:
        - id: id of the dialect.

    Returns:
        - success/error string based on the operation result.
    """
    dialect = Dialect.query.get(id)
    if dialect is None:
        return HTTPResponse.not_found("Dialect not found")

    if dialect.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            dialect.to_mini(),
            "dialect",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Dialect Deleted",
            f"Dialect {dialect.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"Dialect Deleted #{dialect.id}")
    else:
        return HTTPResponse.error("Error deleting Dialect", status=500)


@admin.route("/api/idnumbertypes/", methods=["GET", "POST"])
def api_id_number_types() -> Response:
    """
    Returns ID Number Types in JSON format, allows search and paging.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    q = request.args.get("q")
    if q:
        result = (
            IDNumberType.query.filter(
                or_(IDNumberType.title.ilike(f"%{q}%"), IDNumberType.title_tr.ilike(f"%{q}%"))
            )
            .order_by(-IDNumberType.id)
            .paginate(page=page, per_page=per_page, count=True)
        )
    else:
        result = IDNumberType.query.order_by(-IDNumberType.id).paginate(
            page=page, per_page=per_page, count=True
        )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/idnumbertype")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_id_number_type_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an ID number type.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    id_number_type = IDNumberType()
    id_number_type.from_json(validated_data["item"])

    if id_number_type.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            id_number_type.to_mini(),
            "idnumbertype",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{id_number_type.id}",
            data={"item": id_number_type.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/idnumbertype/<int:id>")
@roles_required("Admin")
@validate_with(ComponentDataMixinRequestModel)
def api_id_number_type_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an ID number type.

    Args:
        - id: id of the ID number type.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    id_number_type = IDNumberType.query.get(id)

    if id_number_type:
        id_number_type.from_json(validated_data.get("item"))
        if id_number_type.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                id_number_type.to_mini(),
                "idnumbertype",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("ID Number Type not found")


@admin.delete("/api/idnumbertype/<int:id>")
@roles_required("Admin")
def api_id_number_type_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an ID number type.

    Args:
        - id: id of the ID number type.

    Returns:
        - success/error string based on the operation result.
    """
    id_number_type = IDNumberType.query.get(id)
    if id_number_type is None:
        return HTTPResponse.not_found("ID Number Type not found")

    # Check if this ID number type is referenced by any actor.id_number[].type
    referenced_count = id_number_type.get_ref_count()

    if referenced_count > 0:
        return HTTPResponse.error(
            f"Cannot delete ID Number Type #{id_number_type.id}. It is referenced by {referenced_count} actor(s).",
            status=409,
        )

    if id_number_type.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            id_number_type.to_mini(),
            "idnumbertype",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "ID Number Type Deleted",
            f"ID Number Type {id_number_type.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"ID Number Type Deleted #{id_number_type.id}")
    else:
        return HTTPResponse.error("Error deleting ID Number Type", status=500)
