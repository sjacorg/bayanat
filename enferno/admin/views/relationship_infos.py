from __future__ import annotations

from flask import Response, request
from flask_security.decorators import current_user, roles_required

from enferno.admin.constants import Constants
from enferno.admin.models import (
    AtoaInfo,
    AtobInfo,
    BtobInfo,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    MediaCategory,
    GeoLocationType,
    Activity,
)
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    AtoaInfoRequestModel,
    AtobInfoRequestModel,
    BtobInfoRequestModel,
    ItoaInfoRequestModel,
    ItobInfoRequestModel,
    ItoiInfoRequestModel,
    MediaCategoryRequestModel,
    GeoLocationTypeRequestModel,
)
from enferno.utils.http_response import HTTPResponse
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE


@admin.route("/api/atoainfos/", methods=["GET", "POST"])
def api_atoainfos() -> Response:
    """Returns AtoaInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        AtoaInfo.query.filter(*query)
        .order_by(-AtoaInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/atoainfo")
@roles_required("Admin")
@validate_with(AtoaInfoRequestModel)
def api_atoainfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an AtoaInfo

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    atoainfo = AtoaInfo()
    atoainfo.from_json(validated_data["item"])

    if not (atoainfo.title and atoainfo.reverse_title):
        return HTTPResponse.error("Title and Reverse Title are required.", status=400)

    if atoainfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            atoainfo.to_mini(),
            "atoainfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{atoainfo.id}",
            data={"item": atoainfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/atoainfo/<int:id>")
@roles_required("Admin")
@validate_with(AtoaInfoRequestModel)
def api_atoainfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an AtoaInfo

    Args:
        - id: id of the AtoaInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    atoainfo = AtoaInfo.query.get(id)

    if atoainfo:
        atoainfo.from_json(validated_data.get("item"))
        if atoainfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                atoainfo.to_mini(),
                "atoainfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("AtoaInfo not found")


@admin.delete("/api/atoainfo/<int:id>")
@roles_required("Admin")
def api_atoainfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an AtoaInfo.

    Args:
        - id: id of the AtoaInfo to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    atoainfo = AtoaInfo.query.get(id)
    if atoainfo is None:
        return HTTPResponse.not_found("AtoaInfo not found")

    if atoainfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            atoainfo.to_mini(),
            "atoainfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "AtoaInfo Deleted",
            f"AtoaInfo {atoainfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"AtoaInfo Deleted #{atoainfo.id}")
    else:
        return HTTPResponse.error("Error deleting Atoa Info", status=500)


@admin.route("/api/atobinfos/", methods=["GET", "POST"])
def api_atobinfos() -> Response:
    """Returns AtobInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        AtobInfo.query.filter(*query)
        .order_by(-AtobInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/atobinfo")
@roles_required("Admin")
@validate_with(AtobInfoRequestModel)
def api_atobinfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an AtobInfo.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    atobinfo = AtobInfo()
    atobinfo.from_json(validated_data["item"])

    if atobinfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            atobinfo.to_mini(),
            "atobinfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{atobinfo.id}",
            data={"item": atobinfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/atobinfo/<int:id>")
@roles_required("Admin")
@validate_with(AtobInfoRequestModel)
def api_atobinfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an AtobInfo.

    Args:
        - id: id of the AtobInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    atobinfo = AtobInfo.query.get(id)

    if atobinfo:
        atobinfo.from_json(validated_data.get("item"))
        if atobinfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                atobinfo.to_mini(),
                "atobinfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("AtobInfo not found")


@admin.delete("/api/atobinfo/<int:id>")
@roles_required("Admin")
def api_atobinfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an AtobInfo.

    Args:
        - id: id of the AtobInfo to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    atobinfo = AtobInfo.query.get(id)
    if atobinfo is None:
        return HTTPResponse.not_found("AtobInfo not found")

    if atobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            atobinfo.to_mini(),
            "atobinfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "AtobInfo Deleted",
            f"AtobInfo {atobinfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"AtobInfo Deleted #{atobinfo.id}")
    else:
        return HTTPResponse.error("Error deleting Atob Info", status=500)


@admin.route("/api/btobinfos/", methods=["GET", "POST"])
def api_btobinfos() -> Response:
    """Returns BtobInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        BtobInfo.query.filter(*query)
        .order_by(-BtobInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/btobinfo")
@roles_required("Admin")
@validate_with(BtobInfoRequestModel)
def api_btobinfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a BtobInfo.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    btobinfo = BtobInfo()
    btobinfo.from_json(validated_data["item"])

    if btobinfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            btobinfo.to_mini(),
            "btobinfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{btobinfo.id}",
            data={"item": btobinfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/btobinfo/<int:id>")
@roles_required("Admin")
@validate_with(BtobInfoRequestModel)
def api_btobinfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a BtobInfo.

    Args:
        - id: id of the BtobInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    btobinfo = BtobInfo.query.get(id)

    if btobinfo:
        btobinfo.from_json(validated_data.get("item"))
        if btobinfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                btobinfo.to_mini(),
                "btobinfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("BtobInfo not found")


@admin.delete("/api/btobinfo/<int:id>")
@roles_required("Admin")
def api_btobinfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a BtobInfo.

    Args:
        - id: id of the BtobInfo to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    btobinfo = BtobInfo.query.get(id)
    if btobinfo is None:
        return HTTPResponse.not_found("BtobInfo not found")

    if btobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            btobinfo.to_mini(),
            "btobinfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "BtobInfo Deleted",
            f"BtobInfo {btobinfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"BtobInfo Deleted #{btobinfo.id}")
    else:
        return HTTPResponse.error("Error deleting Btob Info", status=500)


@admin.route("/api/itoainfos/", methods=["GET", "POST"])
def api_itoainfos() -> Response:
    """Returns ItoaInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        ItoaInfo.query.filter(*query)
        .order_by(-ItoaInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/itoainfo")
@roles_required("Admin")
@validate_with(ItoaInfoRequestModel)
def api_itoainfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an ItoaInfo.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itoainfo = ItoaInfo()
    itoainfo.from_json(validated_data["item"])

    if itoainfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            itoainfo.to_mini(),
            "itoainfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{itoainfo.id}",
            data={"item": itoainfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/itoainfo/<int:id>")
@roles_required("Admin")
@validate_with(ItoaInfoRequestModel)
def api_itoainfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an ItoaInfo.

    Args:
        - id: id of the ItoaInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itoainfo = ItoaInfo.query.get(id)

    if itoainfo:
        itoainfo.from_json(validated_data.get("item"))
        if itoainfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                itoainfo.to_mini(),
                "itoainfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("ItoaInfo not found")


@admin.delete("/api/itoainfo/<int:id>")
@roles_required("Admin")
def api_itoainfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an ItoaInfo.

    Args:
        - id: id of the ItoaInfo to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    itoainfo = ItoaInfo.query.get(id)
    if itoainfo is None:
        return HTTPResponse.not_found("ItoaInfo not found")

    if itoainfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itoainfo.to_mini(),
            "itoainfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "ItoaInfo Deleted",
            f"ItoaInfo {itoainfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"ItoaInfo Deleted #{itoainfo.id}")
    else:
        return HTTPResponse.error("Error deleting Itoa Info", status=500)


@admin.route("/api/itobinfos/", methods=["GET", "POST"])
def api_itobinfos() -> Response:
    """Returns ItobInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        ItobInfo.query.filter(*query)
        .order_by(-ItobInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/itobinfo")
@roles_required("Admin")
@validate_with(ItobInfoRequestModel)
def api_itobinfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an ItobInfo.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itobinfo = ItobInfo()
    itobinfo.from_json(validated_data["item"])

    if itobinfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            itobinfo.to_mini(),
            "itobinfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{itobinfo.id}",
            data={"item": itobinfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/itobinfo/<int:id>")
@roles_required("Admin")
@validate_with(ItobInfoRequestModel)
def api_itobinfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an ItobInfo.

    Args:
        - id: id of the ItobInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itobinfo = ItobInfo.query.get(id)

    if itobinfo:
        itobinfo.from_json(validated_data.get("item"))
        if itobinfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                itobinfo.to_mini(),
                "itobinfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("ItobInfo not found")


@admin.delete("/api/itobinfo/<int:id>")
@roles_required("Admin")
def api_itobinfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an ItobInfo
    :param id: id of the ItobInfo to be deleted
    :return: success/error
    """
    itobinfo = ItobInfo.query.get(id)
    if itobinfo is None:
        return HTTPResponse.not_found("ItobInfo not found")

    if itobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itobinfo.to_mini(),
            "itobinfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "ItobInfo Deleted",
            f"ItobInfo {itobinfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"ItobInfo Deleted #{itobinfo.id}")
    else:
        return HTTPResponse.error("Error deleting Itob Info", status=500)


@admin.route("/api/itoiinfos/", methods=["GET", "POST"])
def api_itoiinfos() -> Response:
    """Returns ItoiInfos in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        ItoiInfo.query.filter(*query)
        .order_by(-ItoiInfo.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/itoiinfo")
@roles_required("Admin")
@validate_with(ItoiInfoRequestModel)
def api_itoiinfo_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an ItoiInfo.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itoiinfo = ItoiInfo()
    itoiinfo.from_json(validated_data["item"])

    if itoiinfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            itoiinfo.to_mini(),
            "itoiinfo",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{itoiinfo.id}",
            data={"item": itoiinfo.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/itoiinfo/<int:id>")
@roles_required("Admin")
@validate_with(ItoiInfoRequestModel)
def api_itoiinfo_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an ItoiInfo.

    Args:
        - id: id of the ItoiInfo
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    itoiinfo = ItoiInfo.query.get(id)

    if itoiinfo:
        itoiinfo.from_json(validated_data.get("item"))
        if itoiinfo.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                itoiinfo.to_mini(),
                "itoiinfo",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("ItoiInfo not found")


@admin.delete("/api/itoiinfo/<int:id>")
@roles_required("Admin")
def api_itoiinfo_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete an ItoiInfo.

    Args:
        - id: id of the ItoiInfo to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    itoiinfo = ItoiInfo.query.get(id)
    if itoiinfo is None:
        return HTTPResponse.not_found("ItoiInfo not found")

    if itoiinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itoiinfo.to_mini(),
            "itoiinfo",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "ItoiInfo Deleted",
            f"ItoiInfo {itoiinfo.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"ItoiInfo Deleted #{itoiinfo.id}")
    else:
        return HTTPResponse.error("Error deleting Itoi Info", status=500)


@admin.route("/api/mediacategories/", methods=["GET", "POST"])
def api_mediacategories() -> Response:
    """Returns MediaCategories in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        MediaCategory.query.filter(*query)
        .order_by(-MediaCategory.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/mediacategory")
@roles_required("Admin")
@validate_with(MediaCategoryRequestModel)
def api_mediacategory_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a MediaCategory.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    mediacategory = MediaCategory()
    mediacategory.from_json(validated_data["item"])

    if mediacategory.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            mediacategory.to_mini(),
            "mediacategory",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{mediacategory.id}",
            data={"item": mediacategory.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/mediacategory/<int:id>")
@roles_required("Admin")
@validate_with(MediaCategoryRequestModel)
def api_mediacategory_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a MediaCategory.
    Args:
        - id: id of the MediaCategory
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    mediacategory = MediaCategory.query.get(id)

    if mediacategory:
        mediacategory.from_json(validated_data.get("item"))
        if mediacategory.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                mediacategory.to_mini(),
                "mediacategory",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("MediaCategory not found")


@admin.delete("/api/mediacategory/<int:id>")
@roles_required("Admin")
def api_mediacategory_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a MediaCategory.

    Args:
        - id: id of the MediaCategory to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    mediacategory = MediaCategory.query.get(id)
    if mediacategory is None:
        return HTTPResponse.not_found("MediaCategory not found")

    if mediacategory.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            mediacategory.to_mini(),
            "mediacategory",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "Media Category Deleted",
            f"Media Category {mediacategory.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"MediaCategory Deleted #{mediacategory.id}")
    else:
        return HTTPResponse.error("Error deleting Media Category", status=500)


@admin.route("/api/geolocationtypes/", methods=["GET", "POST"])
def api_geolocationtypes() -> Response:
    """Returns GeoLocationTypes in JSON format, allows search and paging."""
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    query = []
    result = (
        GeoLocationType.query.filter(*query)
        .order_by(-GeoLocationType.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return HTTPResponse.success(data=response)


@admin.post("/api/geolocationtype")
@roles_required("Admin")
@validate_with(GeoLocationTypeRequestModel)
def api_geolocationtype_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a GeoLocationType.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    geolocationtype = GeoLocationType()
    geolocationtype.from_json(validated_data["item"])

    if geolocationtype.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            geolocationtype.to_mini(),
            "geolocationtype",
        )
        return HTTPResponse.created(
            message=f"Item created successfully ID #{geolocationtype.id}",
            data={"item": geolocationtype.to_dict()},
        )
    else:
        return HTTPResponse.error("Creation failed.", status=500)


@admin.put("/api/geolocationtype/<int:id>")
@roles_required("Admin")
@validate_with(GeoLocationTypeRequestModel)
def api_geolocationtype_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a GeoLocationType.

    Args:
        - id: id of the GeoLocationType
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    geolocationtype = GeoLocationType.query.get(id)

    if geolocationtype:
        geolocationtype.from_json(validated_data.get("item"))
        if geolocationtype.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                geolocationtype.to_mini(),
                "geolocationtype",
            )
            return HTTPResponse.success(message="Updated")
        else:
            return HTTPResponse.error("Error saving item", status=500)
    else:
        return HTTPResponse.not_found("GeoLocationType not found")


@admin.delete("/api/geolocationtype/<int:id>")
@roles_required("Admin")
def api_geolocationtype_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a GeoLocationType.

    Args:
        - id: id of the GeoLocationType to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    geolocationtype = GeoLocationType.query.get(id)
    if geolocationtype is None:
        return HTTPResponse.not_found("GeoLocationType not found")

    if geolocationtype.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            geolocationtype.to_mini(),
            "geolocationtype",
        )
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.ITEM_DELETED,
            "GeoLocation Type Deleted",
            f"GeoLocation Type {geolocationtype.title} has been deleted by {current_user.username} successfully.",
        )
        return HTTPResponse.success(message=f"GeoLocationType Deleted #{geolocationtype.id}")
    else:
        return HTTPResponse.error("Error deleting GeoLocation Type", status=500)


@admin.route("/api/relation/info")
def relationship_info() -> Response:
    """Fetches information about various relationships and returns it as JSON."""
    atobInfo = [item.to_dict() for item in AtobInfo.query.all()]
    itobInfo = [item.to_dict() for item in ItobInfo.query.all()]
    btobInfo = [item.to_dict() for item in BtobInfo.query.all()]
    atoaInfo = [item.to_dict() for item in AtoaInfo.query.all()]
    itoaInfo = [item.to_dict() for item in ItoaInfo.query.all()]
    itoiInfo = [item.to_dict() for item in ItoiInfo.query.all()]

    return HTTPResponse.success(
        data={
            "atobInfo": atobInfo,
            "itobInfo": itobInfo,
            "btobInfo": btobInfo,
            "atoaInfo": atoaInfo,
            "itoaInfo": itoaInfo,
            "itoiInfo": itoiInfo,
        },
    )
