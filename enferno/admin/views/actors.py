from __future__ import annotations

from typing import Optional

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import select, func

from enferno.admin.constants import Constants
from enferno.admin.models import Actor, ActorProfile, Activity, WorkflowStatus
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    ActorQueryRequestModel,
    ActorRequestModel,
    ActorReviewRequestModel,
    ActorBulkUpdateRequestModel,
    ActorSelfAssignRequestModel,
)
from enferno.extensions import rds, db
from enferno.tasks import bulk_update_actors
from enferno.user.models import Role
from enferno.utils.http_response import HTTPResponse
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE, REL_PER_PAGE, can_assign_roles


# Actor fields routes
@admin.route("/actor-fields/")
@roles_required("Admin")
def actor_fields() -> str:
    """Endpoint for actor fields configuration."""
    return render_template("admin/actor-fields.html")


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
    q = validated_data.get("q", [{}])
    if q and q != [{}]:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "actor",
        )

    cursor = validated_data.get("cursor")
    per_page = validated_data.get("per_page", PER_PAGE)
    include_count = validated_data.get("include_count", False)

    search = SearchUtils(q, "actor")
    base_query = search.get_query()

    if include_count and cursor is None:
        # Check if this is a simple listing query (no search filters)
        is_simple_listing = q == [{}] or not any(
            bool(filter_dict) for filter_dict in q if filter_dict
        )

        if is_simple_listing:
            # For simple listing: use fast COUNT(*) directly on table (~50ms)
            total_count = db.session.execute(select(func.count(Actor.id))).scalar()

            # Fast data query without window function overhead
            main_query = base_query.order_by(Actor.id.desc()).limit(per_page + 1)
            result = db.session.execute(main_query)
            items = result.scalars().unique().all()
        else:
            # For search queries: keep original window function approach
            count_subquery = (
                base_query.add_columns(func.count().over().label("total_count"))
                .order_by(Actor.id.desc())
                .limit(per_page + 1)
            )

            result = db.session.execute(count_subquery)
            rows = result.all()

            if rows:
                items = [row[0] for row in rows]  # Extract Actor objects
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
        main_query = base_query.order_by(Actor.id.desc())
        if cursor:
            main_query = main_query.where(Actor.id < int(cursor))

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
                    "name": item.name,
                    "name_ar": item.name_ar,
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
        # Select json encoding type
        mode = request.args.get("mode", "1")
        return HTTPResponse.created(
            message=f"Created Actor #{actor.id}",
            data={"item": actor.to_dict(mode=mode)},
        )
    else:
        return HTTPResponse.error("Error creating Actor", status=500)


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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Actor {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

        if not current_user.has_role("Admin") and current_user != actor.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "actor",
                details=f"Unauthorized attempt to update unassigned Actor {id}.",
            )
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update unassigned Actor {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")
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
            return HTTPResponse.success(message=f"Saved Actor #{actor.id}")
        else:
            return HTTPResponse.error(f"Error saving Actor #{id}", status=500)
    else:
        return HTTPResponse.not_found("Actor not found")


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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Actor {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

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
            return HTTPResponse.success(message=f"Actor review updated #{id}")
        else:
            return HTTPResponse.error(f"Error saving Actor #{id}'s Review", status=500)
    else:
        return HTTPResponse.not_found("Actor not found")


# bulk update actor endpoint
@admin.put("/api/actor/bulk/")
@roles_accepted("Admin", "Mod")
@validate_with(ActorBulkUpdateRequestModel)
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
        return HTTPResponse.success(message="Bulk update queued successfully.")
    else:
        return HTTPResponse.error("No items selected, or nothing to update", status=400)


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
        return HTTPResponse.not_found("Actor not found")
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
            return HTTPResponse.success(data=actor.to_dict(mode))
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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to view restricted Actor {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")


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
        return HTTPResponse.not_found("Actor not found")

    if not current_user.can_access(actor):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            actor.to_mini(),
            "actor",
            details="Unauthorized attempt to view restricted Actor profiles.",
        )
        # Notify admins
        Notification.send_admin_notification_for_event(
            Constants.NotificationEvent.UNAUTHORIZED_ACTION,
            "Unauthorized Action",
            f"Unauthorized attempt to view restricted Actor profiles. User: {current_user.username}",
            is_urgent=True,
        )
        return HTTPResponse.forbidden("Restricted Access")

    profiles = actor.actor_profiles
    profiles_data = [profile.to_dict() for profile in profiles]
    return HTTPResponse.success(data=profiles_data)


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
        return HTTPResponse.error("Invalid class")
    actor = Actor.query.get(id)
    if not actor:
        return HTTPResponse.not_found("Actor not found")
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

    return HTTPResponse.success(data={"items": data, "more": load_more})


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
        return HTTPResponse.not_found("Actor profile not found")

    if not current_user.can_access(profile.actor):
        Activity.create(
            current_user,
            Activity.ACTION_VIEW,
            Activity.STATUS_DENIED,
            profile.actor.to_mini(),
            "actor",
            details="Unauthorized attempt to view restricted Actor.",
        )
        return HTTPResponse.forbidden("Restricted Access")

    return HTTPResponse.success(data=profile.mp_json())


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
        return HTTPResponse.forbidden("User not allowed to self assign")

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
        return HTTPResponse.forbidden("Restricted Access")

    if actor:
        a = validated_data.get("actor")
        # workflow check
        if actor.assigned_to_id and actor.assigned_to.active:
            return HTTPResponse.error("Item already assigned to an active user")

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
        return HTTPResponse.success(message=f"Saved Actor #{actor.id}")
    else:
        return HTTPResponse.not_found("Actor not found")
