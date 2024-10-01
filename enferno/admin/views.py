from __future__ import annotations

import os
import shutil
import unicodedata
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Literal, Optional, Tuple, Union
from uuid import uuid4
from unidecode import unidecode

import bleach
import boto3
from flask import Response, Blueprint, current_app, json, g, send_from_directory
from flask import request, jsonify, abort, session
from flask.templating import render_template
from flask_babel import gettext
from flask_security import logout_user
from flask_security.decorators import auth_required, current_user, roles_accepted, roles_required
from sqlalchemy import desc, or_
from werkzeug.utils import safe_join, secure_filename
from zxcvbn import zxcvbn
from flask_security.twofactor import tf_disable

import enferno.utils.typing as t
from enferno.admin.models import (
    Bulletin,
    Label,
    Source,
    Location,
    Eventtype,
    Media,
    Actor,
    Incident,
    IncidentHistory,
    BulletinHistory,
    ActorHistory,
    LocationHistory,
    PotentialViolation,
    ClaimedViolation,
    Activity,
    Query,
    LocationAdminLevel,
    LocationType,
    AppConfig,
    AtobInfo,
    AtoaInfo,
    BtobInfo,
    ItoiInfo,
    ItoaInfo,
    ItobInfo,
    Country,
    Ethnography,
    Dialect,
    MediaCategory,
    GeoLocationType,
    WorkflowStatus,
    ActorProfile,
)
from enferno.admin.validation.models import (
    ActorQueryRequestModel,
    ActorRequestModel,
    ActorReviewRequestModel,
    ActorSelfAssignRequestModel,
    AtoaInfoRequestModel,
    AtobInfoRequestModel,
    BtobInfoRequestModel,
    BulkUpdateRequestModel,
    BulletinBulkUpdateRequestModel,
    BulletinQueryRequestModel,
    BulletinRequestModel,
    BulletinReviewRequestModel,
    BulletinSelfAssignRequestModel,
    ClaimedViolationRequestModel,
    ComponentDataMixinRequestModel,
    ConfigRequestModel,
    CountryRequestModel,
    EventtypeRequestModel,
    GeoLocationTypeRequestModel,
    GraphVisualizeRequestModel,
    IncidentBulkUpdateRequestModel,
    IncidentQueryRequestModel,
    IncidentRequestModel,
    IncidentReviewRequestModel,
    IncidentSelfAssignRequestModel,
    ItoaInfoRequestModel,
    ItobInfoRequestModel,
    ItoiInfoRequestModel,
    LabelRequestModel,
    LocationAdminLevelRequestModel,
    LocationQueryRequestModel,
    LocationRequestModel,
    LocationTypeRequestModel,
    MediaCategoryRequestModel,
    MediaRequestModel,
    PotentialViolationRequestModel,
    RoleRequestModel,
    SourceRequestModel,
    UserForceResetRequestModel,
    UserNameCheckValidationModel,
    UserPasswordCheckValidationModel,
    UserRequestModel,
)
from enferno.admin.validation.util import validate_with
from enferno.extensions import rds, db
from enferno.tasks import (
    bulk_update_bulletins,
    bulk_update_actors,
    bulk_update_incidents,
    generate_graph,
)
from enferno.user.models import User, Role, Session
from enferno.utils.config_utils import ConfigManager
from enferno.utils.data_helpers import get_file_hash
from enferno.utils.graph_utils import GraphUtils
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_log_filenames, get_logger
from enferno.utils.search_utils import SearchUtils

root = os.path.abspath(os.path.dirname(__file__))
admin = Blueprint(
    "admin",
    __name__,
    template_folder=os.path.join(root, "templates"),
    static_folder=os.path.join(root, "static"),
    url_prefix="/admin",
)

# default global items per page
PER_PAGE = 30
REL_PER_PAGE = 5

logger = get_logger()

# History access decorators


def require_view_history(f):
    """
    Decorator to ensure the user has the required permissions to view history.
    """

    @wraps(f)
    # Ensure the user is logged in before checking permissions
    @auth_required("session")
    def decorated_function(*args, **kwargs):
        # Check if user has the required view history permissions
        if not (
            current_user.has_role("Admin")
            or current_user.view_simple_history
            or current_user.view_full_history
        ):
            return HTTPResponse.FORBIDDEN
        return f(*args, **kwargs)

    return decorated_function


def can_assign_roles(func):
    """
    Decorator to ensure the user has the required permissions to assign roles.
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        roles = request.json.get("item", {}).get("roles", [])
        if roles:
            if not has_role_assignment_permission(roles):
                Activity.create(
                    current_user,
                    Activity.ACTION_CREATE,
                    Activity.STATUS_DENIED,
                    request.json,
                    "bulletin",
                    details="Unauthorized attempt to assign roles.",
                )
                return HTTPResponse.UNAUTHORIZED
        return func(*args, **kwargs)

    return decorated_function


def has_role_assignment_permission(roles: list) -> bool:
    """
    Function to check if the current user has the required permissions to assign roles.

    Args:
        - roles: List of role ids to assign.

    Returns:
        - True if the user has the required permissions, False otherwise.
    """
    # admins can assign any roles
    if not current_user.has_role("Admin"):
        # non-admins can only assign their roles
        user_roles = {role.id for role in current_user.roles}
        requested_roles = set([role.get("id") for role in roles])
        if not requested_roles.issubset(user_roles) or not current_app.config.get(
            "AC_USERS_CAN_RESTRICT_NEW"
        ):
            return False

    return True


@admin.before_request
@auth_required("session")
def before_request() -> None:
    """
    Attaches the user object to all requests
    and a version number that is used to clear the static files cache globally.
    """
    g.user = current_user
    g.version = "5"


@admin.app_context_processor
def ctx() -> dict:
    """
    passes all users to the application, based on the current user's permissions.

    Returns:
        - dict of users
    """
    users = User.query.order_by(User.username).all()
    if current_user and current_user.is_authenticated:
        users = [u.to_compact() for u in users]
        return {"users": users}
    return {}


# Labels routes
@admin.route("/labels/")
@roles_accepted("Admin", "Mod")
def labels() -> str:
    """
    Endpoint to render the labels backend page.

    Returns:
        - html template of the labels backend page.
    """
    return render_template("admin/labels.html")


@admin.route("/api/labels/")
def api_labels() -> Response:
    """
    API endpoint feed and filter labels with paging

    Returns:
        - json response of label objects.
    """
    query = []
    q = request.args.get("q", None)

    if q:
        words = q.split(" ")
        query.extend([Label.title.ilike(f"%{word}%") for word in words])

    typ = request.args.get("typ", None)
    if typ and typ in ["for_bulletin", "for_actor", "for_incident", "for_offline"]:
        query.append(getattr(Label, typ) == True)
    fltr = request.args.get("fltr", None)

    if fltr == "verified":
        query.append(Label.verified == True)
    elif fltr == "all":
        pass
    else:
        query.append(Label.verified == False)

    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    # pull children only when specific labels are searched
    if q:
        result = Label.query.filter(*query).all()
        labels = [label for label in result]
        ids = []
        children = Label.get_children(labels)
        for label in labels + children:
            ids.append(label.id)
        # remove dups
        ids = list(set(ids))
        result = Label.query.filter(Label.id.in_(ids)).paginate(
            page=page, per_page=per_page, count=True
        )
    else:
        result = Label.query.filter(*query).paginate(page=page, per_page=per_page, count=True)

    response = {
        "items": [item.to_dict(request.args.get("mode", 1)) for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return Response(json.dumps(response), content_type="application/json"), 200


@admin.post("/api/label/")
@roles_accepted("Admin", "Mod")
@validate_with(LabelRequestModel)
def api_label_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a label.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    label = Label()
    created = label.from_json(validated_data["item"])
    if created.save():
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        return f"Created Label #{label.id}", 200
    else:
        return "Save Failed", 417


@admin.put("/api/label/<int:id>")
@roles_accepted("Admin", "Mod")
@validate_with(LabelRequestModel)
def api_label_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a label.

    Args:
        - id: id of the label.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.

    """
    label = Label.query.get(id)
    if label is not None:
        label = label.from_json(validated_data["item"])
        label.save()
        Activity.create(
            current_user, Activity.ACTION_UPDATE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        return f"Saved Label #{label.id}", 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.delete("/api/label/<int:id>")
@roles_required("Admin")
def api_label_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a label.

    Args:
        - id: id of the label.

    Returns:
        - success/error string based on the operation result.
    """
    label = Label.query.get(id)
    if label is None:
        return HTTPResponse.NOT_FOUND

    if label.delete():
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, label.to_mini(), "label"
        )
        return f"Deleted Label #{label.id}", 200
    else:
        return "Error deleting Label", 417


@admin.post("/api/label/import/")
@roles_required("Admin")
def api_label_import() -> str:
    """
    Endpoint to import labels via CSV

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Label.import_csv(request.files.get("csv"))
        return "Success", 200
    else:
        return "Error", 400


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Created Event #{eventtype.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    eventtype = eventtype.from_json(validated_data["item"])
    if eventtype.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            eventtype.to_mini(),
            "eventtype",
        )
        return f"Saved Event #{eventtype.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    if eventtype.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            eventtype.to_mini(),
            "eventtype",
        )
        return f"Deleted Event Type #{eventtype.id}", 200
    else:
        return "Error deleting Event Type", 417


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
        return "Success", 200
    else:
        return "Error", 400


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Created Potential Violation #{potentialviolation.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    potentialviolation = potentialviolation.from_json(validated_data["item"])
    if potentialviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            potentialviolation.to_mini(),
            "potentialviolation",
        )
        return f"Saved Potential Violation #{potentialviolation.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    if potentialviolation.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            potentialviolation.to_mini(),
            "potentialviolation",
        )
        return f"Deleted Potential Violation #{potentialviolation.id}", 200
    else:
        return "Error deleting Potential Violation", 417


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
        return "Success", 200
    else:
        return "Error", 400


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Created Claimed Violation #{claimedviolation.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    claimedviolation = claimedviolation.from_json(validated_data["item"])
    if claimedviolation.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            claimedviolation.to_mini(),
            "claimedviolation",
        )
        return f"Saved Claimed Violation #{claimedviolation.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    if claimedviolation.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            claimedviolation.to_mini(),
            "claimedviolation",
        )
        return f"Deleted Claimed Violation #{claimedviolation.id}", 200
    else:
        return "Error deleting Claimed Violation", 417


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
        return "Success", 200
    else:
        return "Error", 400


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Created Source #{source.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    source = source.from_json(validated_data["item"])
    if source.save():
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            source.to_mini(),
            "source",
        )
        return f"Saved Source #{source.id}", 200
    else:
        return "Save Failed", 417


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
        return HTTPResponse.NOT_FOUND

    if source.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            source.to_mini(),
            "source",
        )
        return f"Deleted Source #{source.id}", 200
    else:
        return "Error deleting Source", 417


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
        return "Success", 200
    else:
        return "Error", 400


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
    query = []
    su = SearchUtils(validated_data, cls="location")
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

    return Response(json.dumps(response), content_type="application/json"), 200


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
        return "User not allowed to create Locations", 400

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
        return f"Created Location #{location.id}", 200


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
        return "User not allowed to create Locations", 400

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
            return f"Saved Location #{location.id}", 200
        else:
            return "Save Failed", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if location.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            location.to_mini(),
            "location",
        )
        return f"Deleted Location #{location.id}", 200
    else:
        return "Error deleting Location", 417


@admin.post("/api/location/import/")
@roles_required("Admin")
def api_location_import() -> Response:
    """Endpoint for importing locations.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Location.import_csv(request.files.get("csv"))
        return "Success", 200
    else:
        return "Error", 400


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
        return HTTPResponse.NOT_FOUND
    else:
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_SUCCESS,
            location.to_mini(),
            "location",
        )
        return json.dumps(location.to_dict()), 200


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

    query = []
    result = (
        LocationAdminLevel.query.filter(*query)
        .order_by(-LocationAdminLevel.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return Response(json.dumps(response), content_type="application/json"), 200


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

    if admin_level.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            admin_level.to_mini(),
            "adminlevel",
        )
        return f"Item created successfully ID ${admin_level.id}", 200
    else:
        return "Creation failed.", 417


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
        admin_level.from_json(validated_data["item"])
        if admin_level.save():
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                admin_level.to_mini(),
                "adminlevel",
            )
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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

    query = []
    result = (
        LocationType.query.filter(*query)
        .order_by(-LocationType.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${location_type.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if location_type.delete():
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            location_type.to_mini(),
            "locationtype",
        )
        return f"Location Type Deleted #{location_type.id}", 200
    else:
        return "Error deleting Location Type", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${country.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if country.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            country.to_mini(),
            "country",
        )
        return f"Country Deleted #{country.id}", 200
    else:
        return "Error deleting Country", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${ethnography.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if ethnography.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            ethnography.to_mini(),
            "ethnography",
        )
        return f"Ethnography Deleted #{ethnography.id}", 200
    else:
        return "Error deleting Ethnography", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${dialect.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if dialect.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            dialect.to_mini(),
            "dialect",
        )
        return f"Dialect Deleted #{dialect.id}", 200
    else:
        return "Error deleting Dialect", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return "Title and Reverse Title are required.", 417

    if atoainfo.save():
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            atoainfo.to_mini(),
            "atoainfo",
        )
        return f"Item created successfully ID ${atoainfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if atoainfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            atoainfo.to_mini(),
            "atoainfo",
        )
        return f"AtoaInfo Deleted #{atoainfo.id}", 200
    else:
        return "Error deleting Atoa Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${atobinfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if atobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            atobinfo.to_mini(),
            "atobinfo",
        )
        return f"AtobInfo Deleted #{atobinfo.id}", 200
    else:
        return "Error deleting Atob Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${btobinfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Item created successfully ID ${btobinfo.id}", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if btobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            btobinfo.to_mini(),
            "btobinfo",
        )
        return f"BtobInfo Deleted #{btobinfo.id}", 200
    else:
        return "Error deleting Btob Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${itoainfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if itoainfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itoainfo.to_mini(),
            "itoainfo",
        )
        return f"ItoaInfo Deleted #{itoainfo.id}", 200
    else:
        return "Error deleting Itoa Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${itobinfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if itobinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itobinfo.to_mini(),
            "itobinfo",
        )
        return f"ItobInfo Deleted #{itobinfo.id}", 200
    else:
        return "Error deleting Itob Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID ${itoiinfo.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if itoiinfo.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            itoiinfo.to_mini(),
            "itoiinfo",
        )
        return f"ItoiInfo Deleted #{itoiinfo.id}", 200
    else:
        return "Error deleting Itoi Info", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID {mediacategory.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if mediacategory.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            mediacategory.to_mini(),
            "mediacategory",
        )
        return f"MediaCategory Deleted #{mediacategory.id}", 200
    else:
        return "Error deleting Media Category", 417


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
    return Response(json.dumps(response), content_type="application/json"), 200


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
        return f"Item created successfully ID {geolocationtype.id}", 200
    else:
        return "Creation failed.", 417


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
            return "Updated", 200
        else:
            return "Error saving item", 417
    else:
        return HTTPResponse.NOT_FOUND


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
        return HTTPResponse.NOT_FOUND

    if geolocationtype.delete():
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_DELETE,
            Activity.STATUS_SUCCESS,
            geolocationtype.to_mini(),
            "geolocationtype",
        )
        return f"GeoLocationType Deleted #{geolocationtype.id}", 200
    else:
        return "Error deleting GeoLocation Type", 417


@admin.route("/api/relation/info")
def relationship_info() -> Response:
    """Fetches information about various relationships and returns it as JSON."""
    atobInfo = [item.to_dict() for item in AtobInfo.query.all()]
    itobInfo = [item.to_dict() for item in ItobInfo.query.all()]
    btobInfo = [item.to_dict() for item in BtobInfo.query.all()]
    atoaInfo = [item.to_dict() for item in AtoaInfo.query.all()]
    itoaInfo = [item.to_dict() for item in ItoaInfo.query.all()]
    itoiInfo = [item.to_dict() for item in ItoiInfo.query.all()]

    return jsonify(
        {
            "atobInfo": atobInfo,
            "itobInfo": itobInfo,
            "btobInfo": btobInfo,
            "atoaInfo": atoaInfo,
            "itoaInfo": itoaInfo,
            "itoiInfo": itoiInfo,
        }
    )


# Bulletin routes
@admin.route("/bulletins/", defaults={"id": None})
@admin.route("/bulletins/<int:id>")
def bulletins(id: Optional[t.id]) -> str:
    """Endpoint for bulletins management."""

    statuses = [item.to_dict() for item in WorkflowStatus.query.all()]
    return render_template(
        "admin/bulletins.html",
        statuses=statuses,
    )


@admin.route("/api/bulletins/", methods=["POST", "GET"])
@validate_with(BulletinQueryRequestModel)
def api_bulletins(validated_data: dict) -> Response:
    """
    Returns bulletins in JSON format, allows search and paging.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - response: Response object
        - status code: 200
    """
    # log search query
    q = validated_data.get("q", None)
    if q and q != [{}]:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "bulletin",
        )

    su = SearchUtils(validated_data, cls="bulletin")
    queries, ops = su.get_query()
    result = Bulletin.query.filter(*queries.pop(0))

    # nested queries
    if len(queries) > 0:
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == "union":
                result = result.union(Bulletin.query.filter(*nextQuery))
            elif nextOp == "intersect":
                result = result.intersect(Bulletin.query.filter(*nextQuery))

    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    result = result.order_by(Bulletin.id.desc()).paginate(page=page, per_page=per_page, count=True)

    # Select json encoding type
    mode = request.args.get("mode", "1")
    response = {
        "items": [item.to_dict(mode=mode) for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json"), 200


@admin.post("/api/bulletin/")
@roles_accepted("Admin", "DA")
@can_assign_roles
@validate_with(BulletinRequestModel)
def api_bulletin_create(
    validated_data: dict,
) -> Response:
    """
    Creates a new bulletin.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    bulletin = Bulletin()
    bulletin.from_json(validated_data["item"])

    # assign automatically to the creator user
    bulletin.assigned_to_id = current_user.id

    roles = validated_data["item"].get("roles", [])
    if roles:
        role_ids = [x.get("id") for x in roles]
        new_roles = Role.query.filter(Role.id.in_(role_ids)).all()
        bulletin.roles = new_roles

    if bulletin.save():
        bulletin.create_revision()
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            bulletin.to_mini(),
            "bulletin",
        )

        return f"Created Bulletin #{bulletin.id}", 200
    else:
        return "Error creating Bulletin", 417


@admin.put("/api/bulletin/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(BulletinRequestModel)
def api_bulletin_update(id: t.id, validated_data: dict) -> Response:
    """
    Updates a bulletin.

    Args:
        - id: id of the bulletin
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    bulletin = Bulletin.query.get(id)
    if bulletin is not None:
        if not current_user.can_access(bulletin):
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "bulletin",
                details=f"Unauthorized attempt to update restricted Bulletin {id}.",
            )
            return "Restricted Access", 403

        if not current_user.has_role("Admin") and current_user != bulletin.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "bulletin",
                details=f"Unauthorized attempt to update unassigned Bulletin {id}.",
            )
            return "Restricted Access", 403

        bulletin = bulletin.from_json(validated_data["item"])

        bulletin.create_revision()
        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            bulletin.to_mini(),
            "bulletin",
        )
        return f"Saved Bulletin #{bulletin.id}", 200
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review bulletin endpoint
@admin.put("/api/bulletin/review/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(BulletinReviewRequestModel)
def api_bulletin_review_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a bulletin review.

    Args:
        - id: id of the bulletin
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    bulletin = Bulletin.query.get(id)
    if bulletin is not None:
        if not current_user.can_access(bulletin):
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_DENIED,
                validated_data,
                "bulletin",
                details=f"Unauthorized attempt to update restricted Bulletin {id}.",
            )
            return "Restricted Access", 403

        bulletin.review = (
            validated_data["item"]["review"] if "review" in validated_data["item"] else ""
        )
        bulletin.review_action = (
            validated_data["item"]["review_action"]
            if "review_action" in validated_data["item"]
            else ""
        )

        if bulletin.status == "Peer Review Assigned":
            bulletin.comments = "Added Peer Review"
        if bulletin.status == "Peer Reviewed":
            bulletin.comments = "Updated Peer Review"

        bulletin.status = "Peer Reviewed"

        # append refs
        refs = validated_data.get("item", {}).get("revrefs", [])

        if bulletin.ref is None:
            bulletin.ref = []
        bulletin.ref = list(set(bulletin.ref + refs))

        if bulletin.save():
            # Create a revision using latest values
            # this method automatically commits
            #  bulletin changes (referenced)
            bulletin.create_revision()

            # Record Activity
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_SUCCESS,
                bulletin.to_mini(),
                "bulletin",
            )
            return f"Bulletin review updated #{bulletin.id}", 200
        else:
            return f"Error saving Bulletin #{id}", 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update bulletin endpoint
@admin.put("/api/bulletin/bulk/")
@roles_accepted("Admin", "Mod")
@validate_with(BulletinBulkUpdateRequestModel)
def api_bulletin_bulk_update(
    validated_data: dict,
) -> Response:
    """
    Endpoint to bulk update bulletins.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    ids = validated_data["items"]
    bulk = validated_data["bulk"]

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role("Admin"):
        # silently discard access roles
        bulk.pop("roles", None)

    if ids and len(bulk):
        job = bulk_update_bulletins.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = f"user{current_user.id}:{job.id}"
        rds.set(key, job.id)
        # expire in 3 hours
        rds.expire(key, 60 * 60 * 3)
        return "Bulk update queued successfully", 200
    else:
        return "No items selected, or nothing to update", 417


# get one bulletin
@admin.get("/api/bulletin/<int:id>")
def api_bulletin_get(
    id: t.id,
) -> Response:
    """
    Endpoint to get a single bulletin.

    Args:
        - id: id of the bulletin

    Returns:
        - bulletin in json format / success or error
    """
    bulletin = Bulletin.query.get(id)
    mode = request.args.get("mode", None)
    if not bulletin:
        return HTTPResponse.NOT_FOUND
    else:
        # hide review from view-only users
        if not current_user.roles:
            bulletin.review = None
        if current_user.can_access(bulletin):
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_SUCCESS,
                bulletin.to_mini(),
                "bulletin",
            )
            return json.dumps(bulletin.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_DENIED,
                bulletin.to_mini(),
                "bulletin",
                details=f"Unauthorized attempt to view restricted Bulletin {id}.",
            )
            return "Restricted Access", 403


# get bulletin relations
@admin.get("/api/bulletin/relations/<int:id>")
def bulletin_relations(id: t.id) -> Response:
    """
    Endpoint to return related entities of a bulletin.

    Args:
        - id: id of the bulletin

    Returns:
        - related entities in json format / success or error
    """
    cls = request.args.get("class", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", REL_PER_PAGE, int)
    if not cls or cls not in ["bulletin", "actor", "incident"]:
        return HTTPResponse.NOT_FOUND
    bulletin = Bulletin.query.get(id)
    if not bulletin:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == "bulletin":
        items = bulletin.bulletin_relations
    elif cls == "actor":
        items = bulletin.actor_relations
    elif cls == "incident":
        items = bulletin.incident_relations

    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True
    if data:
        if cls == "bulletin":
            data = [item.to_dict(exclude=bulletin) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({"items": data, "more": load_more}), 200


@admin.post("/api/bulletin/import/")
@roles_required("Admin")
def api_bulletin_import() -> Response:
    """
    Endpoint to import bulletins from csv data.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Bulletin.import_csv(request.files.get("csv"))
        return "Success", 200
    else:
        return "Error", 400


# ----- self assign endpoints -----


@admin.put("/api/bulletin/assign/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(BulletinSelfAssignRequestModel)
def api_bulletin_self_assign(id: t.id, validated_data: dict) -> Response:
    """
    assign a bulletin to the user.

    Args:
        - id: id of the bulletin
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    # permission check
    if not (current_user.has_role("Admin") or current_user.can_self_assign):
        return "User not allowed to self assign", 403

    bulletin = Bulletin.query.get(id)

    if not current_user.can_access(bulletin):
        Activity.create(
            current_user,
            Activity.ACTION_SELF_ASSIGN,
            Activity.STATUS_DENIED,
            bulletin.to_mini(),
            "bulletin",
            details=f"Unauthorized attempt to self-assign restricted Bulletin {id}.",
        )
        return "Restricted Access", 403

    if bulletin:
        b = validated_data.get("bulletin")
        # workflow check
        if bulletin.assigned_to_id and bulletin.assigned_to.active:
            return "Item already assigned to an active user", 400

        # update bulletin assignement
        bulletin.assigned_to_id = current_user.id
        bulletin.comments = b.get("comments")
        bulletin.ref = bulletin.ref or []
        bulletin.ref = bulletin.ref + b.get("ref", [])

        # Change status to assigned if needed
        if bulletin.status == "Machine Created" or bulletin.status == "Human Created":
            bulletin.status = "Assigned"

        # Create a revision using latest values
        # this method automatically commits
        # bulletin changes (referenced)
        bulletin.create_revision()

        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_SELF_ASSIGN,
            Activity.STATUS_SUCCESS,
            bulletin.to_mini(),
            "bulletin",
        )
        return f"Saved Bulletin #{bulletin.id}", 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.put("/api/actor/assign/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(ActorSelfAssignRequestModel)
def api_actor_self_assign(id: t.id, validated_data: dict) -> Response:
    """
    self assign an actor to the user.

    Args:
        - id: id of the actor
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    # permission check
    if not (current_user.has_role("Admin") or current_user.can_self_assign):
        return "User not allowed to self assign", 403

    actor = Actor.query.get(id)

    if not current_user.can_access(actor):
        Activity.create(
            current_user,
            Activity.ACTION_SELF_ASSIGN,
            Activity.STATUS_DENIED,
            validated_data,
            "actor",
            details=f"Unauthorized attempt to self-assign restricted Actor {id}.",
        )
        return "Restricted Access", 403

    if actor:
        a = validated_data.get("actor")
        # workflow check
        if actor.assigned_to_id and actor.assigned_to.active:
            return "Item already assigned to an active user", 400

        # update bulletin assignement
        actor.assigned_to_id = current_user.id
        actor.comments = a.get("comments")

        # Change status to assigned if needed
        if actor.status == "Machine Created" or actor.status == "Human Created":
            actor.status = "Assigned"

        actor.create_revision()

        # Record Activity
        Activity.create(
            current_user, Activity.ACTION_UPDATE, Activity.STATUS_SUCCESS, actor.to_mini(), "actor"
        )
        return f"Saved Actor #{actor.id}", 200
    else:
        return HTTPResponse.NOT_FOUND


@admin.put("/api/incident/assign/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(IncidentSelfAssignRequestModel)
def api_incident_self_assign(id: t.id, validated_data: dict) -> Response:
    """
    self assign an incident to the user.

    Args:
        - id: id of the incident
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    # permission check
    if not (current_user.has_role("Admin") or current_user.can_self_assign):
        return "User not allowed to self assign", 403

    incident = Incident.query.get(id)

    if not current_user.can_access(incident):
        Activity.create(
            current_user,
            Activity.ACTION_SELF_ASSIGN,
            Activity.STATUS_DENIED,
            validated_data,
            "incident",
            details=f"Unauthorized attempt to self-assign restricted Incident {id}.",
        )
        return "Restricted Access", 403

    if incident:
        i = validated_data.get("incident")
        # workflow check
        if incident.assigned_to_id and incident.assigned_to.active:
            return "Item already assigned to an active user", 400

        # update bulletin assignement
        incident.assigned_to_id = current_user.id
        incident.comments = i.get("comments")

        # Change status to assigned if needed
        if incident.status == "Machine Created" or incident.status == "Human Created":
            incident.status = "Assigned"

        incident.create_revision()

        # Record Activity
        Activity.create(
            current_user,
            Activity.ACTION_UPDATE,
            Activity.STATUS_SUCCESS,
            incident.to_mini(),
            "incident",
        )
        return f"Saved Incident #{incident.id}", 200
    else:
        return HTTPResponse.NOT_FOUND


# Media special endpoints


@admin.post("/api/media/chunk")
@roles_accepted("Admin", "DA")
def api_medias_chunk() -> Response:
    """
    Endpoint for uploading media files based on file system settings.

    Returns:
        - success/error string based on the operation result.
    """
    file = request.files["file"]

    # to check if file is uploaded from media import tool
    import_upload = "/import/media/" in request.referrer
    # validate file extensions based on user and referrer
    if import_upload:
        # uploads from media import tool
        # must be Admin user
        if current_user.has_role("Admin"):
            allowed_extensions = current_app.config["ETL_VID_EXT"]
            if not Media.validate_file_extension(file.filename, allowed_extensions):
                return "This file type is not allowed", 415
        else:
            Activity.create(
                current_user,
                Activity.ACTION_UPLOAD,
                Activity.STATUS_DENIED,
                request.json,
                "media",
                details="Non-admin user attempted to upload media file using import endpoint.",
            )
            return HTTPResponse.UNAUTHORIZED
    else:
        # normal uploads by DA or Admin users
        allowed_extensions = current_app.config["MEDIA_ALLOWED_EXTENSIONS"]
        if not Media.validate_file_extension(file.filename, allowed_extensions):
            Activity.create(
                current_user,
                Activity.STATUS_DENIED,
                Activity.ACTION_UPLOAD,
                request.json,
                "media",
                details="User attempted to upload unallowed file type.",
            )
            return "This file type is not allowed", 415
    decoded = unidecode(file.filename)
    filename = Media.generate_file_name(decoded)
    filepath = (Media.media_dir / filename).as_posix()

    dz_uuid = request.form.get("dzuuid")

    # Chunked upload
    try:
        current_chunk = int(request.form["dzchunkindex"])
        total_chunks = int(request.form["dztotalchunkcount"])
        total_size = int(request.form["dztotalfilesize"])
    except KeyError as err:
        raise abort(400, body=f"Not all required fields supplied, missing {err}")
    except ValueError:
        raise abort(400, body=f"Values provided were not in expected format")

    # validate dz_uuid
    if not safe_join(str(Media.media_file), dz_uuid):
        return "Invalid Request", 425

    save_dir = Media.media_dir / secure_filename(dz_uuid)

    # validate current chunk
    if not safe_join(str(save_dir), str(current_chunk)) or current_chunk.__class__ != int:
        return "Invalid Request", 425

    if not save_dir.exists():
        save_dir.mkdir(exist_ok=True, parents=True)

    # Save the individual chunk
    with open(save_dir / secure_filename(str(current_chunk)), "wb") as f:
        file.save(f)

    # See if we have all the chunks downloaded
    completed = current_chunk == total_chunks - 1

    # Concat all the files into the final file when all are downloaded
    if completed:
        with open(filepath, "wb") as f:
            for file_number in range(total_chunks):
                f.write((save_dir / str(file_number)).read_bytes())

        if os.stat(filepath).st_size != total_size:
            raise abort(400, body=f"Error uploading the file")

        shutil.rmtree(save_dir)
        # get md5 hash
        etag = get_file_hash(filepath)

        # validate etag here // if it exists // reject the upload and send an error code
        if Media.query.filter(Media.etag == etag, Media.deleted is not True).first():
            return "Error, file already exists", 409

        if not current_app.config["FILESYSTEM_LOCAL"] and not import_upload:
            s3 = boto3.resource(
                "s3",
                aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
                region_name=current_app.config["AWS_REGION"],
            )
            s3.Bucket(current_app.config["S3_BUCKET"]).upload_file(filepath, filename)
            # Clean up file if s3 mode is selected
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(e, exc_info=True)

        response = {"etag": etag, "filename": filename}
        Activity.create(
            current_user, Activity.ACTION_UPLOAD, Activity.STATUS_SUCCESS, response, "media"
        )
        return Response(json.dumps(response), content_type="application/json"), 200

    return "Chunk upload successful", 200


@admin.post("/api/media/upload/")
@roles_accepted("Admin", "DA")
def api_medias_upload() -> Response:
    """
    Endpoint to upload screenshots based on file system settings.

    Returns:
        - success/error string based on the operation result.
    """
    file = request.files.get("file")
    if not file:
        return "Invalid request params", 417

    # normal uploads by DA or Admin users
    allowed_extensions = current_app.config["MEDIA_ALLOWED_EXTENSIONS"]
    if not Media.validate_file_extension(file.filename, allowed_extensions):
        Activity.create(
            current_user,
            Activity.STATUS_DENIED,
            Activity.ACTION_UPLOAD,
            request.json,
            "media",
            details="User attempted to upload unallowed file type.",
        )
        return "This file type is not allowed", 415

    if current_app.config["FILESYSTEM_LOCAL"]:
        file = request.files.get("file")
        # final file
        decoded = unidecode(file.filename)
        filename = Media.generate_file_name(decoded)
        filepath = (Media.media_dir / filename).as_posix()

        with open(filepath, "wb") as f:
            file.save(f)
        # get md5 hash
        etag = get_file_hash(filepath)
        # check if file already exists
        if Media.query.filter(Media.etag == etag, Media.deleted is not True).first():
            return "Error: File already exists", 409

        response = {"etag": etag, "filename": filename}

        return Response(json.dumps(response), content_type="application/json"), 200
    else:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
        )

        # final file
        decoded = unidecode(file.filename)
        filename = Media.generate_file_name(decoded)
        # filepath = (Media.media_dir/filename).as_posix()

        response = s3.Bucket(current_app.config["S3_BUCKET"]).put_object(Key=filename, Body=file)

        etag = response.get()["ETag"].replace('"', "")

        # check if file already exists
        if Media.query.filter(Media.etag == etag, Media.deleted is not True).first():
            return "Error: File already exists", 409

        return json.dumps({"filename": filename, "etag": etag}), 200


GRACE_PERIOD = timedelta(hours=2)  # 2 hours
S3_URL_EXPIRY = 3600  # 2 hours


# return signed url from s3 valid for some time
@admin.route("/api/media/<filename>")
def serve_media(
    filename: str,
) -> Response:
    """
    Endpoint to generate file urls to be served (based on file system type.)

    Args:
        - filename: name of the file.

    Returns:
        - temporarily accessible url of the file.
    """

    if current_app.config["FILESYSTEM_LOCAL"]:
        file_path = safe_join("/admin/api/serve/media", filename)
        if file_path:
            return file_path, 200
        else:
            return "Invalid Request", 425
    else:
        # validate access control
        media = Media.query.filter(Media.media_file == filename).first()

        s3 = boto3.client(
            "s3",
            aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
            region_name=current_app.config["AWS_REGION"],
        )

        # allow generation of s3 urls for a short period while the media is not created
        if media is None:
            # this means the file is not in the database
            # we allow serving it briefly while the user is still creating the media
            try:
                # Get the last modified time of the file
                resp = s3.head_object(Bucket=current_app.config["S3_BUCKET"], Key=filename)
                last_modified = resp["LastModified"]

                # Check if file is uploaded within the grace period
                if datetime.utcnow() - last_modified.replace(tzinfo=None) <= GRACE_PERIOD:
                    params = {"Bucket": current_app.config["S3_BUCKET"], "Key": filename}
                    url = s3.generate_presigned_url("get_object", Params=params, ExpiresIn=36000)
                    return url, 200
                else:
                    Activity.create(
                        current_user,
                        Activity.ACTION_VIEW,
                        Activity.STATUS_DENIED,
                        {"file": filename},
                        "media",
                        details="Unauthorized attempt to access restricted media file.",
                    )
                    return HTTPResponse.FORBIDDEN
            except s3.exceptions.NoSuchKey:
                return HTTPResponse.NOT_FOUND
            except Exception as e:
                return HTTPResponse.INTERNAL_SERVER_ERROR
        else:
            # media exists in the database, check access control restrictions
            if not current_user.can_access(media):
                Activity.create(
                    current_user,
                    Activity.ACTION_VIEW,
                    Activity.STATUS_DENIED,
                    request.json,
                    "media",
                    details="Unauthorized attempt to access restricted media file.",
                )
                return "Restricted Access", 403

            params = {"Bucket": current_app.config["S3_BUCKET"], "Key": filename}
            if filename.lower().endswith("pdf"):
                params["ResponseContentType"] = "application/pdf"
            return s3.generate_presigned_url("get_object", Params=params, ExpiresIn=S3_URL_EXPIRY)


@admin.route("/api/serve/media/<filename>")
def api_local_serve_media(
    filename: str,
) -> Response:
    """
    serves file from local file system.

    Args:
        - filename: name of the file.

    Returns:
        - file to be served.
    """

    media = Media.query.filter(Media.media_file == filename).first()

    if media and not current_user.can_access(media):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            request.json,
            "media",
            details="Unauthorized attempt to access restricted media file.",
        )
        return "Restricted Access", 403
    else:
        if media:
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_SUCCESS,
                media.to_mini() if media else {"file": filename},
                "media",
            )
        return send_from_directory("media", filename)


@admin.post("/api/inline/upload")
@roles_accepted("Admin", "DA")
def api_inline_medias_upload() -> Response:
    """
    Endpoint to upload inline media files.

    Returns:
        - success/error string based on the operation result.
    """
    try:
        f = request.files.get("file")

        # final file
        decoded = unidecode(f.filename)
        filename = Media.generate_file_name(decoded)
        filepath = (Media.inline_dir / filename).as_posix()
        f.save(filepath)
        response = {"location": filename}

        return Response(json.dumps(response), content_type="application/json"), 200
    except Exception as e:
        logger.error(e, exc_info=True)
        return "Request Failed", 417


@admin.route("/api/serve/inline/<filename>")
def api_local_serve_inline_media(filename: str) -> Response:
    """
    serves inline media files - only for authenticated users.

    Args:
        - filename: name of the file.

    Returns:
        - file to be served.
    """
    return send_from_directory("media/inline", filename)


# Medias routes


@admin.put("/api/media/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(MediaRequestModel)
def api_media_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a media item.

    Args:
        - id: id of the media
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    media = Media.query.get(id)
    if media is None:
        return HTTPResponse.NOT_FOUND

    if not current_user.can_access(media):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            validated_data,
            "media",
            details="Unauthorized attempt to update restricted media.",
        )
        return "Restricted Access", 403

    media = media.from_json(validated_data["item"])
    if media.save():
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_SUCCESS,
            validated_data,
            "media",
        )
        return "Media {id} updated", 200
    else:
        return "Error updating Media", 417


# Actor routes
@admin.route("/actors/", defaults={"id": None})
@admin.route("/actors/<int:id>")
def actors(id: Optional[t.id]) -> str:
    """Endpoint to render actors page."""

    statuses = [item.to_dict() for item in WorkflowStatus.query.all()]
    return render_template(
        "admin/actors.html",
        statuses=statuses,
    )


@admin.route("/api/actors/", methods=["POST", "GET"])
@validate_with(ActorQueryRequestModel)
def api_actors(validated_data: dict) -> Response:
    """
    Returns actors in JSON format, allows search and paging.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - actors in json format / success or error
    """
    # log search query
    if request.method == "POST":
        q = validated_data.get("q", [{}])
    else:
        q = request.args.get("q", [{}])
    if q and q != [{}]:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "actor",
        )

    su = SearchUtils({"q": q}, cls="actor")
    queries, ops = su.get_query()
    result = Actor.query.filter(*queries.pop(0))

    # nested queries
    if len(queries) > 0:
        while queries:
            nextOp = ops.pop(0)
            nextQuery = queries.pop(0)
            if nextOp == "union":
                result = result.union(Actor.query.filter(*nextQuery))
            elif nextOp == "intersect":
                result = result.intersect(Actor.query.filter(*nextQuery))

    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    result = result.paginate(page=page, per_page=per_page, count=True)
    # Select json encoding type
    mode = request.args.get("mode", "1")
    response = {
        "items": [item.to_dict(mode=mode) for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json"), 200


# create actor endpoint
@admin.post("/api/actor/")
@roles_accepted("Admin", "DA")
@validate_with(ActorRequestModel)
@can_assign_roles
def api_actor_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create an Actor item.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    actor = Actor()
    actor.from_json(validated_data["item"])

    # assign actor to creator by default
    actor.assigned_to_id = current_user.id

    roles = validated_data["item"].get("roles")
    if roles:
        role_ids = [x.get("id") for x in roles]
        new_roles = Role.query.filter(Role.id.in_(role_ids)).all()
        actor.roles = new_roles

    if actor.save():
        # the below will create the first revision by default
        actor.create_revision()
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, actor.to_mini(), "actor"
        )
        return f"Created Actor #{actor.id}", 200
    else:
        return "Error creating Actor", 417


# update actor endpoint
@admin.put("/api/actor/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(ActorRequestModel)
def api_actor_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an Actor item.

    Args:
        - id: id of the actor
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    actor = Actor.query.get(id)
    if actor is not None:
        # check for restrictions
        if not current_user.can_access(actor):
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "actor",
                details=f"Unauthorized attempt to update restricted Actor {id}.",
            )
            return "Restricted Access", 403

        if not current_user.has_role("Admin") and current_user != actor.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "actor",
                details=f"Unauthorized attempt to update unassigned Actor {id}.",
            )
            return "Restricted Access", 403
        actor = actor.from_json(validated_data["item"])
        # Create a revision using latest values
        # this method automatically commits
        # actor changes (referenced)
        if actor.save():
            actor.create_revision()
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                actor.to_mini(),
                "actor",
            )
            return f"Saved Actor #{actor.id}", 200
        else:
            return f"Error saving Actor #{id}", 417
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review actor endpoint
@admin.put("/api/actor/review/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(ActorReviewRequestModel)
def api_actor_review_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an Actor's review item.

    Args:
        - id: id of the actor
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    actor = Actor.query.get(id)
    if actor is not None:
        if not current_user.can_access(actor):
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_DENIED,
                validated_data,
                "actor",
                details=f"Unauthorized attempt to update restricted Actor {id}.",
            )
            return "Restricted Access", 403

        actor.review = (
            validated_data["item"]["review"] if "review" in validated_data["item"] else ""
        )
        actor.review_action = (
            validated_data["item"]["review_action"]
            if "review_action" in validated_data["item"]
            else ""
        )

        actor.status = "Peer Reviewed"

        # Create a revision using latest values
        # this method automatically commits
        #  actor changes (referenced)
        if actor.save():
            actor.create_revision()
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_SUCCESS,
                actor.to_mini(),
                "actor",
            )
            return f"Actor review updated #{id}", 200
        else:
            return f"Error saving Actor #{id}'s Review", 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update actor endpoint
@admin.put("/api/actor/bulk/")
@roles_accepted("Admin", "Mod")
@validate_with(BulkUpdateRequestModel)
def api_actor_bulk_update(
    validated_data: dict,
) -> Response:
    """
    Endpoint to bulk update actors.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    ids = validated_data["items"]
    bulk = validated_data["bulk"]

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role("Admin"):
        # silently discard access roles
        bulk.pop("roles", None)

    if ids and len(bulk):
        job = bulk_update_actors.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = f"user{current_user.id}:{job.id}"
        rds.set(key, job.id)
        # expire in 3 hour
        rds.expire(key, 60 * 60 * 3)
        return "Bulk update queued successfully.", 200
    else:
        return "No items selected, or nothing to update", 417


# get one actor


@admin.get("/api/actor/<int:id>")
def api_actor_get(
    id: t.id,
) -> Response:
    """
    Endpoint to get a single actor.

    Args:
        - id: id of the actor

    Returns:
        - actor data in json format / success or error in case of failure.
    """
    actor = Actor.query.get(id)
    if not actor:
        return HTTPResponse.NOT_FOUND
    else:
        mode = request.args.get("mode", None)
        if current_user.can_access(actor):
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_SUCCESS,
                actor.to_mini(),
                "actor",
            )
            return json.dumps(actor.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_DENIED,
                actor.to_mini(),
                "actor",
                details="Unauthorized attempt to view restricted Actor.",
            )
            return "Restricted Access", 403


@admin.get("/api/actor/<int:actor_id>/profiles")
def api_actor_profiles(actor_id: t.id) -> Response:
    """
    Endpoint to get all profiles associated with a specific actor.

    Args:
        - actor_id: ID of the actor.

    Returns:
        - JSON array of actor profiles or an error message.
    """
    actor = Actor.query.get(actor_id)
    if not actor:
        return HTTPResponse.NOT_FOUND

    if not current_user.can_access(actor):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            actor.to_mini(),
            "actor",
            details="Unauthorized attempt to view restricted Actor profiles.",
        )
        return HTTPResponse.FORBIDDEN

    profiles = actor.actor_profiles
    profiles_data = [profile.to_dict() for profile in profiles]
    return json.dumps(profiles_data), 200


# get actor relations
@admin.get("/api/actor/relations/<int:id>")
def actor_relations(id: t.id) -> Response:
    """
    Endpoint to return related entities of an Actor.

    Args:
        - id: id of the actor.

    Returns:
        - related entities in json format.
    """
    cls = request.args.get("class", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", REL_PER_PAGE, int)
    if not cls or cls not in ["bulletin", "actor", "incident"]:
        return HTTPResponse.NOT_FOUND
    actor = Actor.query.get(id)
    if not actor:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == "bulletin":
        items = actor.bulletin_relations
    elif cls == "actor":
        items = actor.actor_relations
    elif cls == "incident":
        items = actor.incident_relations

    # pagination
    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True

    if data:
        if cls == "actor":
            data = [item.to_dict(exclude=actor) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({"items": data, "more": load_more}), 200


@admin.get("/api/actormp/<int:id>")
def api_actor_mp_get(id: t.id) -> Response:
    """
    Endpoint to get missing person data for an actor profile.

    Args:
        - id: id of the actor profile.

    Returns:
        - actor profile data in json format / success or error in case of failure.
    """
    profile = ActorProfile.query.get(id)
    if not profile:
        return HTTPResponse.NOT_FOUND

    if not current_user.can_access(profile.actor):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            profile.actor.to_mini(),
            "actor",
            details="Unauthorized attempt to view restricted Actor.",
        )
        return HTTPResponse.FORBIDDEN

    return json.dumps(profile.mp_json()), 200


# Bulletin History Helpers


@admin.route("/api/bulletinhistory/<int:bulletinid>")
@require_view_history
def api_bulletinhistory(bulletinid: t.id) -> Response:
    """
    Endpoint to get revision history of a bulletin.

    Args:
        - bulletinid: id of the bulletin item.

    Returns:
        - json feed of item's history / error.
    """
    result = (
        BulletinHistory.query.filter_by(bulletin_id=bulletinid)
        .order_by(desc(BulletinHistory.created_at))
        .all()
    )

    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return Response(json.dumps(response), content_type="application/json"), 200


# Actor History Helpers


@admin.route("/api/actorhistory/<int:actorid>")
@require_view_history
def api_actorhistory(actorid: t.id) -> Response:
    """
    Endpoint to get revision history of an actor.

    Args:
        - actorid: id of the actor item.

    Returns:
        - json feed of item's history / error.
    """
    result = (
        ActorHistory.query.filter_by(actor_id=actorid).order_by(desc(ActorHistory.created_at)).all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return Response(json.dumps(response), content_type="application/json"), 200


# Incident History Helpers


@admin.route("/api/incidenthistory/<int:incidentid>")
@require_view_history
def api_incidenthistory(incidentid: t.id) -> Response:
    """
    Endpoint to get revision history of an incident item.

    Args:
        - incidentid: id of the incident item.

    Returns:
        - json feed of item's history / error.
    """
    result = (
        IncidentHistory.query.filter_by(incident_id=incidentid)
        .order_by(desc(IncidentHistory.created_at))
        .all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return Response(json.dumps(response), content_type="application/json"), 200


# Location History Helpers


@admin.route("/api/locationhistory/<int:locationid>")
@require_view_history
def api_locationhistory(locationid: t.id) -> Response:
    """
    Endpoint to get revision history of a location.

    Args:
        - locationid: id of the location item.

    Returns:
        - json feed of item's history / error.
    """
    result = (
        LocationHistory.query.filter_by(location_id=locationid)
        .order_by(desc(LocationHistory.created_at))
        .all()
    )
    # For standardization
    response = {"items": [item.to_dict() for item in result]}
    return Response(json.dumps(response), content_type="application/json"), 200


# user management routes


@admin.route("/api/users/")
@roles_accepted("Admin", "Mod")
def api_users() -> Response:
    """
    API endpoint to feed users data in json format , supports paging and search.

    Returns:
        - json feed of users / error.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    q = request.args.get("q")
    query = []
    if q is not None:
        query.append(User.name.ilike("%" + q + "%"))
    result = (
        User.query.filter(*query)
        .order_by(User.username)
        .paginate(page=page, per_page=per_page, count=True)
    )

    response = {
        "items": [
            item.to_dict() if current_user.has_role("Admin") else item.to_compact()
            for item in result.items
        ],
        "perPage": per_page,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json"), 200


@admin.get("/users/", defaults={"id": None})
@admin.get("/users/<int:id>")
@roles_required("Admin")
def users(id) -> str:
    """
    Endpoint to render the users backend page.

    Returns:
        - html page of the users backend.
    """
    return render_template("admin/users.html")


@admin.get("/api/user/<int:id>")
@roles_required("Admin")
def api_user_get(id) -> Response:
    """
    Endpoint to get a user
    :param id: id of the user
    :return: user data in json format + success or error in case of failure
    """
    user = User.query.get(id)
    if not user:
        return HTTPResponse.NOT_FOUND
    else:
        return user.to_dict()


@admin.get("/api/user/<int:id>/sessions")
@roles_required("Admin")
def api_user_sessions(id: int) -> Any:
    """
    Retrieve paginated session data for a specific user.

    Args:
        id (int): The ID of the user whose sessions are to be retrieved.

    Returns:
        Any: A dictionary with session details and pagination info, or an error message and HTTP status code.
    """

    session_redis = current_app.config["SESSION_REDIS"]
    session_interface = current_app.session_interface
    per_page = request.args.get("per_page", PER_PAGE, int)
    page = request.args.get("page", 1, int)

    try:
        # Fetch the user to ensure they exist and to collect their session tokens
        user = User.query.get(id)
        if not user:
            return HTTPResponse.NOT_FOUND
        sessions_paginated = (
            Session.query.filter(Session.user_id == id).order_by(Session.created_at.desc())
        ).paginate(page=page, per_page=per_page, error_out=False)

        # Collect tokens from user's sessions to filter Redis keys
        user_session_tokens = {s.session_token for s in sessions_paginated.items}

        user_redis_keys = [f"session:{token}" for token in user_session_tokens if token]

        # Retrieve and decode session details from Redis, storing in a dictionary
        redis_sessions_details = {}
        for key in user_redis_keys:
            data = session_redis.get(key)
            if data:
                token = key.split(":")[1]
                session_data = session_interface.serializer.decode(data)
                # hide session details from the response
                redis_sessions_details[token] = {"_fresh": session_data.get("_fresh")}

        # Prepare the session data for response including the details
        sessions_data = []

        for s in sessions_paginated.items:
            session_info = s.to_dict()
            if s.session_token in redis_sessions_details:
                session_info["details"] = redis_sessions_details[s.session_token]
            session_info["active"] = s.session_token == session.sid
            sessions_data.append(session_info)

        # Determine if there are more items left
        more = sessions_paginated.has_next

        return {"items": sessions_data, "more": more}

    except Exception as e:
        return {"error": "Expectation failed", "message": str(e)}, 417


@admin.delete("/api/session/logout")
@roles_required("Admin")
def logout_session() -> Response:
    """
    Handle session logout by session id (admin only).

    Returns appropriate messages based on the success or failure of the logout operation.
    """

    # get the sessid from the JSON payload
    sessid = request.json.get("sessid", None)
    if not sessid:
        return "Invalid request. Please provide a session ID.", 400
    try:
        # Query the database to get the session token using the sessid
        session_ = Session.query.get(sessid)

        if not session_:
            return f"Session ID {sessid} not found.", 404

        token = session_.session_token

        if token == session.sid:
            logout_user()
            # Use a custom JSON response with a specific field to signal a redirect to the front-end
            return {"logout": "successful", "redirect": True}

        rds = current_app.config["SESSION_REDIS"]
        session_key = f"session:{token}"

        # Check if the session key exists in Redis
        if rds.exists(session_key):
            # Delete the session key from Redis
            rds.delete(session_key)
            return f"Session {sessid} logged out successfully."
        else:
            return f"Session {sessid} not found in Redis.", 404

    except Exception as e:
        return f"Error while logging out session: {str(e)}", 500


@admin.delete("/api/user/<int:user_id>/sessions/logout")
@roles_required("Admin")
def logout_all_sessions(user_id: int) -> Any:
    """
    Log out all sessions for a given user.

    Args:
        user_id (int): The ID of the user whose sessions will be logged out.

    Returns:
        Tuple[Union[str, dict], int]: A response message and HTTP status code.
    """
    # Fetch the user to ensure they exist
    user = User.query.get(user_id)
    if not user:
        return "User not found", 404

    rds = current_app.config["SESSION_REDIS"]
    errors = []
    current_session_logout_needed = False

    # Iterate over user's sessions and delete them from Redis, except the current session
    for s in user.sessions:
        if s.session_token == session.sid:
            current_session_logout_needed = True
            continue

        try:
            session_key = f"session:{s.session_token}"
            if rds.exists(session_key):
                rds.delete(session_key)
        except Exception as e:
            errors.append(f"Failed to delete session {s.session_token}: {str(e)}")

    # Logout current session last if needed
    if current_session_logout_needed:
        logout_user()

    # Build response
    if errors:
        return {"errors": errors}, 500
    return f"All sessions for user {user_id} logged out successfully", 200


@admin.delete("/api/user/revoke_2fa")
@roles_required("Admin")
def revoke_2fa() -> Response:
    """
    Revoke 2FA for a specified user.

    Returns:
        Tuple[str, int]: A success message and HTTP status code.
    """
    user_id: int = request.args.get("user_id", default=None, type=int)

    if not user_id:
        return HTTPResponse.BAD_REQUEST

    user = User.query.get(user_id)
    if not user:
        return HTTPResponse.BAD_REQUEST

    tf_disable(user)
    # also clear all webauthn credentials
    for cred in user.webauthn:
        db.session.delete(cred)
    user.save()

    return f"2FA revoked for user {user_id} successfully", 200


@admin.post("/api/user/")
@roles_required("Admin")
@validate_with(UserRequestModel)
def api_user_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a user item.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    # validate existing
    u = validated_data.get("item")
    username = u.get("username")

    exists = User.query.filter(User.username == username).first()
    if len(username) < 4:
        return "Error, username too short", 417
    if len(username) > 32:
        return "Error, username too long", 417
    if exists:
        return "Error, username already exists", 417
    user = User()
    user.fs_uniquifier = uuid4().hex
    user.from_json(u)
    result = user.save()
    if result:
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )
        return f"User {username} has been created successfully", 200
    else:
        return "Error creating user", 417


@admin.post("/api/checkuser/")
@roles_required("Admin")
@validate_with(UserNameCheckValidationModel)
def api_user_check(
    validated_data: dict,
) -> Response:
    """
    API endpoint to validate a username.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    data = validated_data.get("item")
    if not data:
        return "Please select a username", 417

    # validate illegal charachters
    uclean = bleach.clean(data.strip(), strip=True)
    if uclean != data:
        return "Illegal characters detected", 417

    # validate disallowed charachters
    cats = [unicodedata.category(c)[0] for c in data]
    if any([cat not in ["L", "N"] for cat in cats]):
        return "Disallowed characters detected", 417

    u = User.query.filter(User.username == data).first()
    if u:
        return "Username already exists", 417
    else:
        return "Username ok", 200


@admin.put("/api/user/")
@roles_required("Admin")
@validate_with(UserRequestModel)
def api_user_update(
    validated_data: dict,
) -> Response:
    """
    Endpoint to update a user.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    item = validated_data.get("item")
    user = User.query.get(item.get("id"))
    if user is not None:
        u = validated_data.get("item")
        user = user.from_json(u)
        if user.save():
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                user.to_mini(),
                "user",
            )
            return f"Saved User {user.id} {user.name}", 200
        else:
            return f"Error saving User {user.id} {user.name}", 417
    else:
        return HTTPResponse.NOT_FOUND


@admin.post("/api/password/")
@validate_with(UserPasswordCheckValidationModel)
def api_check_password(
    validated_data: dict,
) -> Response:
    """
    API Endpoint to validate a password and check its strength.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    # Retrieve the password from the request's JSON body
    password = validated_data.get("password")

    # Check if the password is provided
    if not password:
        return "No password provided", 400

    result = zxcvbn(password)
    score = result.get("score")
    if score >= current_app.config.get("SECURITY_ZXCVBN_MINIMUM_SCORE"):
        return "Password is ok", 200
    else:
        return "Weak Password Score", 409


@admin.post("/api/user/force-reset")
@roles_required("Admin")
@validate_with(UserForceResetRequestModel)
def api_user_force_reset(validated_data: dict) -> Response:
    """
    Endpoint to force a password reset for a user.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    item = validated_data.get("item")
    if not item:
        abort(400)
    user = User.query.get(item.get("id"))
    if not user:
        abort(400)
    if reset_key := user.security_reset_key:
        message = f"Forced password reset already requested: {reset_key}"
        return Response(message, mimetype="text/plain")
    user.set_security_reset_key()
    message = f"Forced password reset has been set for user {user.username}"
    return Response(message, mimetype="text/plain")


@admin.post("/api/user/force-reset-all")
@roles_required("Admin")
def api_user_force_reset_all() -> Response:
    """
    sets a redis flag to force password reset for all users.

    Returns:
        - success response after setting all redis flags (if not already set)
    """
    for user in User.query.all():
        # check if user already has a password reset flag
        if not user.security_reset_key:
            user.set_security_reset_key()
    return "Forced password reset has been set for all users", 200


@admin.delete("/api/user/<int:id>")
@roles_required("Admin")
def api_user_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a user.

    Args:
        - id: id of the user to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    user = User.query.get(id)
    if user is None:
        return HTTPResponse.NOT_FOUND

    if user.active:
        return "User is active, make inactive before deleting", 403

    if user.delete():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, user.to_mini(), "user"
        )
        return "Deleted", 200
    else:
        return "Error deleting User", 417


# Roles routes
@admin.route("/roles/")
@roles_required("Admin")
def roles() -> str:
    """
    Endpoint to redner roles backend page.

    Returns:
        - html page of the roles backend.
    """
    return render_template("admin/roles.html")


@admin.get("/api/roles/")
@roles_required("Admin")
def api_roles() -> Response:
    """
    API endpoint to feed roles items in josn format - supports paging and search.

    Returns:
        - json feed of roles / error.
    """
    query = []
    q = request.args.get("q", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)
    if q is not None:
        query.append(Role.name.ilike("%" + q + "%"))
    result = (
        Role.query.filter(*query)
        .order_by(Role.id)
        .paginate(page=page, per_page=per_page, count=True)
    )
    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }
    return Response(json.dumps(response), content_type="application/json"), 200


@admin.post("/api/role/")
@roles_required("Admin")
@validate_with(RoleRequestModel)
def api_role_create(
    validated_data: dict,
) -> Response:
    """
    Endpoint to create a role item.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role()
    created = role.from_json(validated_data["item"])
    if created.save():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_CREATE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
        )
        return "Created", 200

    else:
        return "Save Failed", 417


@admin.put("/api/role/<int:id>")
@roles_required("Admin")
@validate_with(RoleRequestModel)
def api_role_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update a role item.

    Args:
        - id: id of the role to be updated.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role.query.get(id)
    if role is None:
        return HTTPResponse.NOT_FOUND

    if role.name in ["Admin", "Mod", "DA"]:
        return "Cannot edit System Roles", 403

    role = role.from_json(validated_data["item"])
    role.save()
    # Record activity
    Activity.create(
        current_user, Activity.ACTION_UPDATE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
    )
    return f"Role {id} Updated", 200


@admin.delete("/api/role/<int:id>")
@roles_required("Admin")
def api_role_delete(
    id: t.id,
) -> Response:
    """
    Endpoint to delete a role item.

    Args:
        - id: id of the role to be deleted.

    Returns:
        - success/error string based on the operation result.
    """
    role = Role.query.get(id)

    if role is None:
        return HTTPResponse.NOT_FOUND

    # forbid deleting system roles
    if role.name in ["Admin", "Mod", "DA"]:
        return "Cannot delete System Roles", 403
    # forbid delete roles assigned to restricted items
    if role.bulletins.first() or role.actors.first() or role.incidents.first():
        return "Role assigned to restricted items", 403

    if role.delete():
        # Record activity
        Activity.create(
            current_user, Activity.ACTION_DELETE, Activity.STATUS_SUCCESS, role.to_mini(), "role"
        )
        return "Deleted", 200
    else:
        return "Error deleting Role", 417


@admin.post("/api/role/import/")
@roles_required("Admin")
def api_role_import() -> Response:
    """
    Endpoint to import role items from a CSV file.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Role.import_csv(request.files.get("csv"))
        return "Success", 200
    else:
        return "Error", 400


# Incident routes
@admin.route("/incidents/", defaults={"id": None})
@admin.route("/incidents/<int:id>")
def incidents(id: Optional[t.id]) -> str:
    """
    Endpoint to render incidents backend page.

    Args:
        - id: id of the incident item.

    Returns:
        - html page of the incidents backend.
    """

    statuses = [item.to_dict() for item in WorkflowStatus.query.all()]
    return render_template(
        "admin/incidents.html",
        statuses=statuses,
    )


@admin.route("/api/incidents/", methods=["POST", "GET"])
@validate_with(IncidentQueryRequestModel)
def api_incidents(validated_data: dict) -> Response:
    """
    Returns incidents in JSON format, allows search and paging.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - incidents in json format / success or error
    """
    # log search query
    q = validated_data.get("q", None)
    if q and q != [{}]:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "incident",
        )

    query = []

    su = SearchUtils(validated_data, cls="incident")

    query = su.get_query()

    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", PER_PAGE, int)

    result = (
        Incident.query.filter(*query)
        .order_by(Incident.id.desc())
        .paginate(page=page, per_page=per_page, count=True)
    )
    # Select json encoding type
    mode = request.args.get("mode", "1")
    response = {
        "items": [item.to_dict(mode=mode) for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json"), 200


@admin.post("/api/incident/")
@roles_accepted("Admin", "DA")
@can_assign_roles
@validate_with(IncidentRequestModel)
def api_incident_create(
    validated_data: dict,
) -> Response:
    """
    API endpoint to create an incident.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    incident = Incident()
    incident.from_json(validated_data["item"])

    # assign to creator by default
    incident.assigned_to_id = current_user.id

    roles = validated_data["item"].get("roles", [])
    if roles:
        role_ids = [x.get("id") for x in roles]
        new_roles = Role.query.filter(Role.id.in_(role_ids)).all()
        incident.roles = new_roles

    if incident.save():
        # the below will create the first revision by default
        incident.create_revision()
        # Record activity
        Activity.create(
            current_user,
            Activity.ACTION_CREATE,
            Activity.STATUS_SUCCESS,
            incident.to_mini(),
            "incident",
        )
        return f"Created Incident #{incident.id}", 200
    else:
        return "Error creating Incident", 417


# update incident endpoint
@admin.put("/api/incident/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(IncidentRequestModel)
def api_incident_update(id: t.id, validated_data: dict) -> Response:
    """
    API endpoint to update an incident.

    Args:
        - id: id of the incident.
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    incident = Incident.query.get(id)

    if incident is not None:
        if not current_user.can_access(incident):
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "incident",
                details=f"Unauthorized attempt to update restricted Incident {id}.",
            )
            return "Restricted Access", 403

        if not current_user.has_role("Admin") and current_user != incident.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "incident",
                details=f"Unauthorized attempt to update unassigned Incident {id}.",
            )
            return "Restricted Access", 403

        incident = incident.from_json(validated_data["item"])

        # Create a revision using latest values
        # this method automatically commits
        # incident changes (referenced)
        if incident:
            incident.create_revision()
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                incident.to_mini(),
                "incident",
            )
            return f"Saved Incident #{id}", 200
        else:
            return f"Error saving Incident {id}", 417
    else:
        return HTTPResponse.NOT_FOUND


# Add/Update review incident endpoint
@admin.put("/api/incident/review/<int:id>")
@roles_accepted("Admin", "DA")
@validate_with(IncidentReviewRequestModel)
def api_incident_review_update(id: t.id, validated_data: dict) -> Response:
    """
    Endpoint to update an incident review item.

    Args:
        - id: id of the incident
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """
    incident = Incident.query.get(id)
    if incident is not None:
        if not current_user.can_access(incident):
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_DENIED,
                validated_data,
                "incident",
                details=f"Unauthorized attempt to update restricted Incident {id}.",
            )
            return "Restricted Access", 403

        incident.review = (
            validated_data["item"]["review"] if "review" in validated_data["item"] else ""
        )
        incident.review_action = (
            validated_data["item"]["review_action"]
            if "review_action" in validated_data["item"]
            else ""
        )

        incident.status = "Peer Reviewed"
        if incident.save():
            # Create a revision using latest values
            # this method automatically commi
            # incident changes (referenced)
            incident.create_revision()
            # Record activity
            Activity.create(
                current_user,
                Activity.ACTION_REVIEW,
                Activity.STATUS_SUCCESS,
                incident.to_mini(),
                "incident",
            )
            return f"Bulletin review updated #{id}", 200
        else:
            return f"Error saving Incident #{id}'s Review", 417
    else:
        return HTTPResponse.NOT_FOUND


# bulk update incident endpoint
@admin.put("/api/incident/bulk/")
@roles_accepted("Admin", "Mod")
@validate_with(IncidentBulkUpdateRequestModel)
def api_incident_bulk_update(
    validated_data: dict,
) -> Response:
    """
    endpoint to handle bulk incidents updates.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - success/error string based on the operation result.
    """

    ids = validated_data["items"]
    bulk = validated_data["bulk"]

    # non-intrusive hard validation for access roles based on user
    if not current_user.has_role("Admin"):
        # silently discard access roles
        bulk.pop("roles", None)
        bulk.pop("rolesReplace", None)
        bulk.pop("restrictRelated", None)

    if ids and len(bulk):
        job = bulk_update_incidents.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = f"user{current_user.id}:{job.id}"
        rds.set(key, job.id)
        # expire in 3 hour
        rds.expire(key, 60 * 60 * 3)
        return "Bulk update queued successfully", 200
    else:
        return "No items selected, or nothing to update", 417


# get one incident
@admin.get("/api/incident/<int:id>")
def api_incident_get(
    id: t.id,
) -> Response:
    """
    Endopint to get a single incident by id.

    Args:
        - id: id of the incident.

    Returns:
        - incident data in json format / success or error in case of failure.
    """
    incident = Incident.query.get(id)
    if not incident:
        return HTTPResponse.NOT_FOUND
    else:
        mode = request.args.get("mode", None)
        if current_user.can_access(incident):
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_SUCCESS,
                incident.to_mini(),
                "incident",
            )
            return json.dumps(incident.to_dict(mode)), 200
        else:
            # block access altogether here, doesn't make sense to send only the id
            Activity.create(
                current_user,
                Activity.ACTION_VIEW,
                Activity.STATUS_DENIED,
                incident.to_mini(),
                "incident",
                details=f"Unauthorized attempt to view restricted Incident {id}.",
            )
            return "Restricted Access", 403


# get incident relations
@admin.get("/api/incident/relations/<int:id>")
def incident_relations(id: t.id) -> Response:
    """
    Endpoint to return related entities of an Incident.

    Args:
        - id: id of the incident.

    Returns:
        - related entities in json format.
    """
    cls = request.args.get("class", None)
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", REL_PER_PAGE, int)
    if not cls or cls not in ["bulletin", "actor", "incident"]:
        return HTTPResponse.NOT_FOUND
    incident = Incident.query.get(id)
    if not incident:
        return HTTPResponse.NOT_FOUND
    items = []

    if cls == "bulletin":
        items = incident.bulletin_relations
    elif cls == "actor":
        items = incident.actor_relations
    elif cls == "incident":
        items = incident.incident_relations

    # add support for loading all relations at once
    if page == 0:
        if cls == "incident":
            data = [item.to_dict(exclude=incident) for item in items]
        else:
            data = [item.to_dict() for item in items]

        return json.dumps({"items": data, "more": False}), 200

    # pagination
    start = (page - 1) * per_page
    end = start + per_page
    data = items[start:end]

    load_more = False if end >= len(items) else True

    if data:
        if cls == "incident":
            data = [item.to_dict(exclude=incident) for item in data]
        else:
            data = [item.to_dict() for item in data]

    return json.dumps({"items": data, "more": load_more}), 200


@admin.post("/api/incident/import/")
@roles_required("Admin")
def api_incident_import() -> Response:
    """
    Endpoint to handle incident imports.

    Returns:
        - success/error string based on the operation result.
    """
    if "csv" in request.files:
        Incident.import_csv(request.files.get("csv"))
        return "Success", 200
    else:
        return "Error", 417


# Activity routes
@admin.route("/activity/")
@roles_required("Admin")
def activity() -> str:
    """
    Endpoint to render activity backend page.

    Returns:
        - html page of the activity backend.
    """
    atobInfo = [item.to_dict() for item in AtobInfo.query.all()]
    btobInfo = [item.to_dict() for item in BtobInfo.query.all()]
    atoaInfo = [item.to_dict() for item in AtoaInfo.query.all()]
    itobInfo = [item.to_dict() for item in ItobInfo.query.all()]
    itoaInfo = [item.to_dict() for item in ItoaInfo.query.all()]
    itoiInfo = [item.to_dict() for item in ItoiInfo.query.all()]
    statuses = [item.to_dict() for item in WorkflowStatus.query.all()]

    return render_template(
        "admin/activity.html",
        actions_types=Activity.get_action_values(),
        atoaInfo=atoaInfo,
        itoaInfo=itoaInfo,
        itoiInfo=itoiInfo,
        atobInfo=atobInfo,
        btobInfo=btobInfo,
        itobInfo=itobInfo,
        statuses=statuses,
    )


@admin.route("/api/activities/", methods=["POST", "GET"])
@roles_required("Admin")
def api_activities() -> Response:
    """Returns activities in JSON format, allows search and paging."""
    su = SearchUtils(request.json, cls="Activity")
    query = su.get_query()

    options = request.json.get("options")
    page = options.get("page", 1)
    per_page = options.get("itemsPerPage", PER_PAGE)

    result = (
        Activity.query.filter(*query)
        .order_by(-Activity.id)
        .paginate(page=page, per_page=per_page, count=True)
    )

    response = {
        "items": [item.to_dict() for item in result.items],
        "perPage": per_page,
        "total": result.total,
    }

    return Response(json.dumps(response), content_type="application/json"), 200


@admin.route("/api/bulk/status/")
@roles_accepted("Admin", "Mod")
def bulk_status() -> Response:
    """Endpoint to get status update about background bulk operations."""
    uid = current_user.id
    cursor, jobs = rds.scan(0, f"user{uid}:*", 1000)
    tasks = []
    for key in jobs:
        result = {}
        id = key.decode("utf-8").split(":")[-1]
        type = request.args.get("type")
        status = None
        if type == "bulletin":
            status = bulk_update_bulletins.AsyncResult(id).status
        elif type == "actor":
            status = bulk_update_incidents.AsyncResult(id).status
        elif type == "incident":
            status = bulk_update_actors.AsyncResult(id).status
        else:
            return HTTPResponse.NOT_FOUND

        # handle job failure
        if status == "FAILURE":
            rds.delete(key)
        if status != "SUCCESS":
            result["id"] = id
            result["status"] = status
            tasks.append(result)

        else:
            rds.delete(key)
    return json.dumps(tasks)


# Saved Searches
@admin.route("/api/queries/")
def api_queries() -> Response:
    """
    Endpoint to get user saved searches.

    Returns:
        - successful json feed of saved searches or error.
    """
    user_id = current_user.id
    query_type = request.args.get("type")
    if query_type not in Query.TYPES:
        return "Invalid query type", 400
    queries = Query.query.filter(Query.user_id == user_id, Query.query_type == query_type)
    return json.dumps([query.to_dict() for query in queries]), 200


@admin.get("/api/query/<string:name>/exists")
def api_query_check_name_exists(
    name: str,
) -> Response:
    """
    API Endpoint check if a query with that provided name exists.
    Queries are tied to the current (request) user.

    Args:
        - name: name of the query to check.

    Returns:
        - success/error string based on the operation result.
    """
    if Query.query.filter_by(name=name, user_id=current_user.id).first():
        return "Query name already exists", 409

    return "Query name is available", 200


@admin.post("/api/query/")
def api_query_create() -> Response:
    """
    API Endpoint save a query search object (advanced search.)

    Returns:
        - success/error string based on the operation result.
    """
    q = request.json.get("q", None)
    name = request.json.get("name", None)
    query_type = request.json.get("type")
    # current saved searches types
    if query_type not in Query.TYPES:
        return "Invalid Request", 400
    if q and name:
        query = Query()
        query.name = name
        query.data = q
        query.query_type = query_type
        query.user_id = current_user.id
        query.save()
        return "Query successfully saved", 200
    else:
        return "Error parsing query data", 417


@admin.put("/api/query/<int:id>")
def api_query_update(
    id: t.id,
) -> Response:
    """
    API Endpoint update a query search object (advanced search).
    Updated searches are tied to the current (request) user.

    Args:
        - id: id of the query to update.

    Returns:
        - success/error string based on the operation result.
    """
    if not (q := request.json.get("q")):
        return "q parameter not provided", 417

    query = Query.query.get(id)

    if not query:
        return "Query not found", 404

    if query.user_id != current_user.id:
        return HTTPResponse.FORBIDDEN

    query.data = q
    if query.save():
        return f"Query {query.name} updated", 200

    return "Query update failed", 409


@admin.delete("/api/query/<int:id>")
def api_query_delete(
    id: t.id,
) -> Response:
    """
    API Endpoint delete a query search object (advanced search).
    Deleted searches are tied to the current (request) user.

    Args:
        - id: id of the query to delete.

    Returns:
        - success/error string based on the operation result.
    """
    query = Query.query.get(id)

    if not query:
        return "Query not found", 404

    if query.user_id != current_user.id:
        return HTTPResponse.FORBIDDEN

    if query.delete():
        return f"Query {query.name} deleted", 200

    return "Query delete failed", 409


@admin.get("/api/graph/json")
def graph_json() -> Optional[str]:
    """
    API Endpoint to return graph data in json format.

    Returns:
        - graph data in json format.
    """
    id = request.args.get("id")
    entity_type = request.args.get("type")
    expanded = request.args.get("expanded")
    graph_utils = GraphUtils(current_user)
    if expanded == "false":
        return graph_utils.get_graph_json(entity_type, id)
    else:
        return graph_utils.expanded_graph(entity_type, id)


@admin.post("/api/graph/visualize")
@validate_with(GraphVisualizeRequestModel)
def graph_visualize(validated_data: dict) -> Response:
    """
    Endpoint to visualize a graph.

    Args:
        - validated_data: validated data from the request.

    Returns:
        - task_id of the graph visualization task.
    """
    user_id = current_user.id
    # Get the type from URL query parameter
    graph_type = request.args.get("type")

    # Check if the type is valid
    if graph_type not in ["actor", "bulletin", "incident"]:
        return abort(400, description="Invalid type provided")

    task_id = generate_graph.delay(validated_data, graph_type, user_id)
    return jsonify({"task_id": task_id.id})


@admin.get("/api/graph/data")
def get_graph_data() -> Response:
    """
    Endpoint to retrieve graph data from Redis.

    Returns:
        - graph data in JSON format.
    """
    user_id = current_user.id

    # Construct the key to retrieve the graph data from Redis
    graph_data_key = f"user{user_id}:graph:data"

    # Retrieve the graph data from Redis
    graph_data = rds.get(graph_data_key)

    if graph_data:
        # Return the graph data as a JSON response
        return Response(graph_data, mimetype="application/json")
    else:
        # If data is not found in Redis
        return HTTPResponse.NOT_FOUND


@admin.get("/api/graph/status")
def check_graph_status() -> Response:
    """Returns the status of the graph visualization task."""
    user_id = current_user.id

    status_key = f"user{user_id}:graph:status"
    status = rds.get(status_key)

    if not status:
        return HTTPResponse.NOT_FOUND

    response_body = json.dumps({"status": status.decode("utf-8")})
    return Response(response_body, status=200, content_type="application/json")


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
    return Response(json.dumps(response), content_type="application/json"), 200


@admin.get("/api/configuration/")
@roles_required("Admin")
def api_config() -> str:
    """Returns serialized app configurations."""
    response = {"config": ConfigManager.serialize(), "labels": dict(ConfigManager.CONFIG_LABELS)}
    return json.dumps(response)


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
        return "Configuration Saved Successfully", 200
    else:
        return "Unable to Save Configuration", 417


@admin.post("/api/reload/")
@roles_required("Admin")
def api_app_reload() -> Response:
    """
    Reloads Flask and Celery.
    """
    from enferno.tasks import reload_app, reload_celery

    reload_app()
    reload_celery.delay()
    return "Reloaded Bayanat", 200


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


# Logging


@admin.route("/logs/")
@roles_required("Admin")
def logs() -> str:
    """
    Endpoint to render the logs backend page.

    Returns:
        - html page of the logs backend.
    """
    return render_template("admin/system-logs.html")


@admin.route("/api/logfiles/")
@roles_required("Admin")
def api_logfiles() -> str:
    """Endpoint to return a dict containing list of log file names and
    the date of the current open log."""
    files = get_log_filenames()
    # read the current log file's first line and extract the date
    log_dir = current_app.config.get("LOG_DIR")
    log_file = current_app.config.get("LOG_FILE")
    log_path = os.path.join(log_dir, log_file)
    date = None
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            timestamp = json.loads(f.readline().strip())["timestamp"]
            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    return json.dumps({"files": files, "date": date})


@admin.route("/api/logs/")
@roles_required("Admin")
def api_logs() -> Response:
    """Endpoint to return the content of the log file."""
    filename = request.args.get("filename", current_app.config.get("LOG_FILE"))
    log_file = secure_filename(filename)
    log_dir = current_app.config.get("LOG_DIR")
    if os.path.exists(safe_join(log_dir, log_file)):
        try:
            return send_from_directory(os.path.abspath(log_dir), log_file)
        except Exception as e:
            logger.error(f"Error sending log file: {e}", exc_info=True)
            return "Error sending log file", 417
    else:
        return "Log file not found", 404
