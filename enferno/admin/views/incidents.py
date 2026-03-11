from __future__ import annotations

from typing import Optional

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import select, func

from enferno.admin.constants import Constants
from enferno.admin.models import Incident, Activity, WorkflowStatus
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    IncidentQueryRequestModel,
    IncidentRequestModel,
    IncidentReviewRequestModel,
    IncidentBulkUpdateRequestModel,
    IncidentSelfAssignRequestModel,
)
from enferno.extensions import rds, db
from enferno.tasks import bulk_update_incidents
from enferno.user.models import Role
from enferno.utils.http_response import HTTPResponse
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE, REL_PER_PAGE, can_assign_roles


# Incident fields routes
@admin.route("/incident-fields/")
@roles_required("Admin")
def incident_fields() -> str:
    """Endpoint for incident fields configuration."""
    return render_template("admin/incident-fields.html")


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
    q = validated_data.get("q", {})
    if q and q != {}:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "incident",
        )

    cursor = validated_data.get("cursor")
    per_page = validated_data.get("per_page", PER_PAGE)
    include_count = validated_data.get("include_count", False)

    search = SearchUtils(q, cls="incident")
    base_query = search.get_query()

    if include_count and cursor is None:
        # Check if this is a simple listing query (no search filters)
        is_simple_listing = q == {} or not any(
            bool(filter_dict) for filter_dict in q if filter_dict
        )

        if is_simple_listing:
            # For simple listing: use fast COUNT(*) directly on table (~50ms)
            total_count = db.session.execute(select(func.count(Incident.id))).scalar()

            # Fast data query without window function overhead
            main_query = base_query.order_by(Incident.id.desc()).limit(per_page + 1)
            result = db.session.execute(main_query)
            items = result.scalars().unique().all()
        else:
            # For search queries: keep original window function approach
            count_subquery = (
                base_query.add_columns(func.count().over().label("total_count"))
                .order_by(Incident.id.desc())
                .limit(per_page + 1)
            )

            result = db.session.execute(count_subquery)
            rows = result.all()

            if rows:
                items = [row[0] for row in rows]  # Extract Incident objects
                total_count = rows[0].total_count if rows else 0
            else:
                items = []
                total_count = 0

        # Determine if there are more pages
        has_more = len(items) > per_page
        if has_more:
            items = items[:per_page]
            next_cursor = str(items[-1].id) if items else None
        else:
            next_cursor = None

    else:
        # Fast pagination approach: no counting overhead
        main_query = base_query.order_by(Incident.id.desc())
        if cursor:
            main_query = main_query.where(Incident.id < int(cursor))

        paginated_query = main_query.limit(per_page + 1)
        result = db.session.execute(paginated_query)
        items = result.scalars().unique().all()

        # Determine if there are more pages
        has_more = len(items) > per_page
        if has_more:
            items = items[:per_page]
            next_cursor = str(items[-1].id) if items else None
        else:
            next_cursor = None

        total_count = None

    # Minimal serialization for list view with permission checks
    serialized_items = []
    for item in items:
        if current_user and current_user.can_access(item):
            # User has access - return full details
            serialized_items.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "title_ar": item.title_ar,
                    "status": item.status,
                    "assigned_to": (
                        {"id": item.assigned_to.id, "name": item.assigned_to.name}
                        if item.assigned_to
                        else None
                    ),
                    "first_peer_reviewer": (
                        {"id": item.first_peer_reviewer.id, "name": item.first_peer_reviewer.name}
                        if item.first_peer_reviewer
                        else None
                    ),
                    "roles": (
                        [
                            {"id": role.id, "name": role.name, "color": role.color}
                            for role in item.roles
                        ]
                        if item.roles
                        else []
                    ),
                    "_status": item.status,
                    "review_action": item.review_action,
                }
            )
        else:
            # User doesn't have access - return restricted info only
            serialized_items.append({"id": item.id, "restricted": True})

    response = {
        "items": serialized_items,
        "nextCursor": next_cursor,
        "meta": {"currentPageSize": len(items), "hasMore": has_more, "isFirstPage": cursor is None},
    }

    # Add count if it was calculated
    if include_count and cursor is None and total_count is not None:
        response["total"] = total_count
        response["totalType"] = "exact"

    return HTTPResponse.success(data=response)


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
        # Select json encoding type
        mode = request.args.get("mode", "1")
        return HTTPResponse.created(
            message=f"Created Incident #{incident.id}",
            data={"item": incident.to_dict(mode=mode)},
        )
    else:
        return HTTPResponse.error("Error creating Incident", status=500)


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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Incident {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

        if not current_user.has_role("Admin") and current_user != incident.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "incident",
                details=f"Unauthorized attempt to update unassigned Incident {id}.",
            )
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update unassigned Incident {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

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
            return HTTPResponse.success(message=f"Saved Incident #{id}")
        else:
            return HTTPResponse.error(f"Error saving Incident {id}", status=500)
    else:
        return HTTPResponse.not_found("Incident not found")


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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Incident {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

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
            return HTTPResponse.success(message=f"Bulletin review updated #{id}")
        else:
            return HTTPResponse.error(f"Error saving Incident #{id}'s Review", status=500)
    else:
        return HTTPResponse.not_found("Incident not found")


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
        return HTTPResponse.success(message="Bulk update queued successfully")
    else:
        return HTTPResponse.error("No items selected, or nothing to update", status=400)


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
        return HTTPResponse.not_found("Incident not found")
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
            return HTTPResponse.success(data=incident.to_dict(mode))
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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to view restricted Incident {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")


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
        return HTTPResponse.error("Invalid class")
    incident = Incident.query.get(id)
    if not incident:
        return HTTPResponse.not_found("Incident not found")
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

        return HTTPResponse.success(data={"items": data, "more": False})

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

    return HTTPResponse.success(data={"items": data, "more": load_more})


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
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error", status=500)


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
        return HTTPResponse.forbidden("User not allowed to self assign")

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
        return HTTPResponse.forbidden("Restricted Access")

    if incident:
        i = validated_data.get("incident")
        # workflow check
        if incident.assigned_to_id and incident.assigned_to.active:
            return HTTPResponse.error("Item already assigned to an active user")

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
        return HTTPResponse.success(message=f"Saved Incident #{incident.id}")
    else:
        return HTTPResponse.not_found("Incident not found")
