from __future__ import annotations

from typing import Optional

from flask import Response, request
from flask.templating import render_template
from flask_security.decorators import current_user, roles_accepted, roles_required
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from enferno.admin.constants import Constants
from enferno.admin.models import Bulletin, Activity, WorkflowStatus
from enferno.admin.models.Notification import Notification
from enferno.admin.validation.models import (
    BulletinQueryRequestModel,
    BulletinRequestModel,
    BulletinReviewRequestModel,
    BulletinBulkUpdateRequestModel,
    BulletinSelfAssignRequestModel,
)
from enferno.extensions import rds, db
from enferno.tasks import bulk_update_bulletins
from enferno.user.models import Role
from enferno.utils.http_response import HTTPResponse
from enferno.utils.search_utils import SearchUtils
from enferno.utils.validation_utils import validate_with
import enferno.utils.typing as t
from . import admin, PER_PAGE, REL_PER_PAGE, can_assign_roles, reject_if_review_locked


# Bulletin fields routes
@admin.route("/bulletin-fields/")
@roles_required("Admin")
def bulletin_fields() -> str:
    """Endpoint for bulletin fields configuration."""
    return render_template("admin/bulletin-fields.html")


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
    # Log search query
    q = validated_data.get("q", [{}])
    if q and q != [{}]:
        Activity.create(
            current_user,
            Activity.ACTION_SEARCH,
            Activity.STATUS_SUCCESS,
            q,
            "bulletin",
        )

    cursor = validated_data.get("cursor")
    per_page = validated_data.get("per_page", PER_PAGE)
    include_count = validated_data.get("include_count", False)

    search = SearchUtils(q, "bulletin")
    base_query = search.get_query().options(
        selectinload(Bulletin.assigned_to),
        selectinload(Bulletin.first_peer_reviewer),
        selectinload(Bulletin.roles),
    )

    if include_count and cursor is None:
        # Check if this is a simple listing query (no search filters)
        is_simple_listing = q == [{}] or not any(
            bool(filter_dict) for filter_dict in q if filter_dict
        )

        if is_simple_listing:
            # For simple listing: use fast COUNT(*) directly on table (~50ms)
            total_count = db.session.execute(select(func.count(Bulletin.id))).scalar()

            # Fast data query without window function overhead
            main_query = base_query.order_by(Bulletin.id.desc()).limit(per_page + 1)
            result = db.session.execute(main_query)
            items = result.scalars().unique().all()
        else:
            # For search queries: separate data + count for faster first-page response
            main_query = base_query.order_by(Bulletin.id.desc()).limit(per_page + 1)
            result = db.session.execute(main_query)
            items = result.scalars().unique().all()

            # Separate count query - runs in parallel with serialization in practice
            count_query = select(func.count()).select_from(base_query.subquery())
            total_count = db.session.execute(count_query).scalar()

        # Determine if there are more pages
        has_more = len(items) > per_page
        if has_more:
            items = items[:per_page]
            next_cursor = str(items[-1].id) if items else None
        else:
            next_cursor = None

    else:
        # Fast pagination approach: no counting overhead
        main_query = base_query.order_by(Bulletin.id.desc())
        if cursor:
            main_query = main_query.where(Bulletin.id < int(cursor))

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
                    "sjac_title": item.sjac_title,
                    "sjac_title_ar": item.sjac_title_ar,
                    "status": item.status,
                    "assigned_to": (item.assigned_to.to_compact() if item.assigned_to else None),
                    "first_peer_reviewer": (
                        item.first_peer_reviewer.to_compact() if item.first_peer_reviewer else None
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

        # Select json encoding type
        mode = request.args.get("mode", "1")
        return HTTPResponse.created(
            message=f"Created Bulletin #{bulletin.id}", data={"item": bulletin.to_dict(mode=mode)}
        )
    else:
        return HTTPResponse.error("Error creating Bulletin", status=500)


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

    bulletin = db.session.get(Bulletin, id)
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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Bulletin {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

        if not current_user.has_role("Admin") and current_user != bulletin.assigned_to:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_DENIED,
                request.json,
                "bulletin",
                details=f"Unauthorized attempt to update unassigned Bulletin {id}.",
            )
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update unassigned Bulletin {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

        review_locked = reject_if_review_locked(bulletin, "bulletin", id)
        if review_locked:
            return review_locked

        # Non-Admin owners cannot reassign or set reviewers via the normal update
        # (BAY-01-022); assignment goes through the assign endpoint.
        if not current_user.has_role("Admin"):
            for field in ("assigned_to", "first_peer_reviewer", "second_peer_reviewer"):
                validated_data["item"].pop(field, None)

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
        return HTTPResponse.success(message=f"Saved Bulletin #{bulletin.id}")
    else:
        return HTTPResponse.not_found("Bulletin not found")


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
    bulletin = db.session.get(Bulletin, id)
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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to update restricted Bulletin {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")

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
        tags = validated_data.get("item", {}).get("revTags", [])

        if bulletin.tags is None:
            bulletin.tags = []
        bulletin.tags = list(set(bulletin.tags + tags))

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
            return HTTPResponse.success(message=f"Bulletin review updated #{bulletin.id}")
        else:
            return HTTPResponse.error(f"Error saving Bulletin #{id}", status=500)
    else:
        return HTTPResponse.not_found("Bulletin not found")


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
        bulk.pop("rolesReplace", None)

    if ids and len(bulk):
        job = bulk_update_bulletins.delay(ids, bulk, current_user.id)
        # store job id in user's session for status monitoring
        key = f"user{current_user.id}:{job.id}"
        rds.set(key, job.id)
        # expire in 3 hours
        rds.expire(key, 60 * 60 * 3)
        return HTTPResponse.success(message="Bulk update queued successfully")
    else:
        return HTTPResponse.error("No items selected, or nothing to update", status=400)


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
    bulletin = db.session.get(Bulletin, id)
    mode = request.args.get("mode", None)
    if not bulletin:
        return HTTPResponse.not_found("Bulletin not found")
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
            data = bulletin.to_dict(mode)
            # Debug-only shim for BYNT-1761 frontend path reveal work.
            debug_labels = [
                {
                    "id": -176101,
                    "title": "Arbitrary Arrest",
                    "title_ar": "الاعتقال التعسفي",
                    "path": "Violations > Detention > Arbitrary Arrest",
                    "path_ar": "الانتهاكات > الاحتجاز > الاعتقال التعسفي",
                },
                {
                    "id": -176102,
                    "title": "Other",
                    "title_ar": "أخرى",
                    "path": "Violations > Property Crimes",
                    "path_ar": "الانتهاكات > جرائم الممتلكات",
                },
                {
                    "id": -176103,
                    "title": "Shelling",
                    "title_ar": "القصف",
                    "path": "Violations > Attacks > Shelling",
                    "path_ar": "الانتهاكات > الهجمات > القصف",
                },
                {
                    "id": -176104,
                    "title": "Torture",
                    "title_ar": "تعذيب",
                    "path": "Violations > Detention",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176105,
                    "title": "Airstrike",
                    "title_ar": "غارة جوية",
                    "path": "Violations > Attacks",
                    "path_ar": "الانتهاكات > الهجمات",
                },
                {
                    "id": -176106,
                    "title": "Siege",
                    "title_ar": "حصار",
                    "path": "Violations > Military Operations",
                    "path_ar": "الانتهاكات > العمليات العسكرية",
                },
                {
                    "id": -176107,
                    "title": "Sniper Fire",
                    "title_ar": "نيران القناصة",
                    "path": "Violations > Attacks",
                    "path_ar": "الانتهاكات > الهجمات",
                },
                {
                    "id": -176108,
                    "title": "Displacement",
                    "title_ar": "تهجير",
                    "path": "Violations > Forced Movement",
                    "path_ar": "الانتهاكات > الحركة القسرية",
                },
                {
                    "id": -176109,
                    "title": "Unknown",
                    "title_ar": "غير معروف",
                    "path": "Violations > Detention",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176110,
                    "title": "Other",
                    "title_ar": "أخرى",
                    "path": "Violations > Attacks",
                    "path_ar": "الانتهاكات > الهجمات",
                },
                {
                    "id": -176111,
                    "title": "Looting",
                    "title_ar": "نهب",
                    "path": "Violations > Property Crimes",
                    "path_ar": "الانتهاكات > جرائم الممتلكات",
                },
                {
                    "id": -176112,
                    "title": "Destruction",
                    "title_ar": "تدمير",
                    "path": "Violations > Property Crimes",
                    "path_ar": "الانتهاكات > جرائم الممتلكات",
                },
                {
                    "id": -176113,
                    "title": "Enforced Disappearance",
                    "title_ar": "اختفاء قسري",
                    "path": "Violations > Detention",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176114,
                    "title": "Kidnapping",
                    "title_ar": "اختطاف",
                    "path": "Violations > Detention",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176115,
                    "title": "Mass Arrests",
                    "title_ar": "اعتقالات جماعية",
                    "path": "Violations > Detention",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176116,
                    "title": "Medical Neglect",
                    "title_ar": "إهمال طبي",
                    "path": "Violations > Detention > Prison Conditions",
                    "path_ar": "الانتهاكات > الاحتجاز > ظروف السجن",
                },
                {
                    "id": -176117,
                    "title": "Forced Recruitment",
                    "title_ar": "تجنيد قسري",
                    "path": "Violations > Children > Recruitment",
                    "path_ar": "الانتهاكات > الأطفال > التجنيد",
                },
                {
                    "id": -176118,
                    "title": "Child Soldier",
                    "title_ar": "طفل مجند",
                    "path": "Violations > Children > Recruitment",
                    "path_ar": "الانتهاكات > الأطفال > التجنيد",
                },
                {
                    "id": -176119,
                    "title": "Sexual Violence",
                    "title_ar": "عنف جنسي",
                    "path": "Violations > Sexual and Gender-Based Violence",
                    "path_ar": "الانتهاكات > العنف الجنسي والجندري",
                },
                {
                    "id": -176120,
                    "title": "Checkpoint Abuse",
                    "title_ar": "انتهاكات الحواجز",
                    "path": "Violations > Movement Restrictions > Checkpoints",
                    "path_ar": "الانتهاكات > قيود الحركة > الحواجز",
                },
                {
                    "id": -176121,
                    "title": "Root Label",
                    "title_ar": "تصنيف جذري",
                },
                {
                    "id": -176122,
                    "title": "No Arabic Title",
                    "path": "Violations > Documentation > Missing Translation",
                    "path_ar": "الانتهاكات > التوثيق > ترجمة مفقودة",
                },
                {
                    "id": -176123,
                    "title": "Same English Path",
                    "title_ar": "Same English Path",
                    "path": "Violations > Detention > Same English Path",
                    "path_ar": "Violations > Detention > Same English Path",
                },
                {
                    "id": -176124,
                    "title": "Very Long Leaf Name for Wrapping",
                    "title_ar": "اسم طويل جدا لاختبار الالتفاف",
                    "path": (
                        "Violations > Civilian Infrastructure > Health Facilities > "
                        "Hospitals and Emergency Medical Points"
                    ),
                },
                {
                    "id": -176125,
                    "title": "Arabic Path Only",
                    "title_ar": "مسار عربي فقط",
                    "path_ar": "الانتهاكات > التعليم > المدارس المتضررة",
                },
                {
                    "id": -176126,
                    "title": "Partial Arabic Fallback",
                    "title_ar": "بديل عربي جزئي",
                    "path": "Violations > Detention > Facilities > Informal Holding Sites",
                    "path_ar": "الانتهاكات > الاحتجاز",
                },
                {
                    "id": -176127,
                    "title": "Unknown",
                    "title_ar": "غير معروف",
                },
                {
                    "id": -176128,
                    "title": "Other",
                    "path": "Violations > Civil Documentation > Other",
                },
                {
                    "id": -176129,
                    "title": "Repeated Leaf",
                    "title_ar": "ورقة مكررة",
                    "path": "Violations > Legal Process > Appeals",
                    "path_ar": "الانتهاكات > الإجراءات القانونية > الاستئناف",
                },
                {
                    "id": -176130,
                    "title": "Repeated Leaf",
                    "title_ar": "ورقة مكررة",
                    "path": "Violations > Legal Process > Sentencing",
                    "path_ar": "الانتهاكات > الإجراءات القانونية > إصدار الأحكام",
                },
            ]
            for field in ("labels", "verLabels"):
                labels = data.setdefault(field, [])
                for index, label in enumerate(labels):
                    debug_label = debug_labels[index % len(debug_labels)]
                    label.update(
                        {
                            "path": debug_label.get("path"),
                            "path_ar": debug_label.get("path_ar"),
                        }
                    )
                labels.extend(label.copy() for label in debug_labels)
            return HTTPResponse.success(data=data)
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
            # Notify admins
            Notification.send_admin_notification_for_event(
                Constants.NotificationEvent.UNAUTHORIZED_ACTION,
                "Unauthorized Action",
                f"Unauthorized attempt to view restricted Bulletin {id}. User: {current_user.username}",
                is_urgent=True,
            )
            return HTTPResponse.forbidden("Restricted Access")


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
        return HTTPResponse.error("Invalid class", status=400)
    bulletin = db.session.get(Bulletin, id)
    if not bulletin:
        return HTTPResponse.not_found("Bulletin not found")
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

    return HTTPResponse.success(data={"items": data, "more": load_more})


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
        return HTTPResponse.success(message="Success")
    else:
        return HTTPResponse.error("Error", status=400)


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
        return HTTPResponse.forbidden("User not allowed to self assign")

    bulletin = db.session.get(Bulletin, id)

    if not current_user.can_access(bulletin):
        Activity.create(
            current_user,
            Activity.ACTION_SELF_ASSIGN,
            Activity.STATUS_DENIED,
            bulletin.to_mini(),
            "bulletin",
            details=f"Unauthorized attempt to self-assign restricted Bulletin {id}.",
        )
        return HTTPResponse.forbidden("Restricted Access")

    if bulletin:
        b = validated_data.get("bulletin")
        # workflow check
        if bulletin.assigned_to_id and bulletin.assigned_to.active:
            return HTTPResponse.error("Item already assigned to an active user", status=400)

        # update bulletin assignement
        bulletin.assigned_to_id = current_user.id
        bulletin.comments = b.get("comments")
        bulletin.tags = bulletin.tags or []
        bulletin.tags = bulletin.tags + b.get("tags", [])

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
        return HTTPResponse.success(message=f"Saved Bulletin #{bulletin.id}")
    else:
        return HTTPResponse.not_found("Bulletin not found")
