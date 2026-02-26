from __future__ import annotations

from flask import Response, request, jsonify
from flask_security.decorators import auth_required, current_user, roles_required
from sqlalchemy import select, func, asc, desc

from enferno.admin.models import Activity
from enferno.admin.models.DynamicField import DynamicField
from enferno.admin.models.DynamicFormHistory import DynamicFormHistory
from enferno.admin.validation.models import DynamicFieldBulkSaveModel
from enferno.extensions import db
from enferno.utils.dynamic_field_utils import create_field, update_field, delete_field
from enferno.utils.form_history_utils import record_form_history
from enferno.utils.http_response import HTTPResponse
from enferno.utils.logging_utils import get_logger
from enferno.utils.validation_utils import validate_with
from . import admin

logger = get_logger()


def parse_filters(args):
    """
    Parse simple filter parameters from query string, following standard app patterns.
    Supports direct field parameters like: ?entity_type=bulletin&active=true&searchable=true
    """
    filters = []

    # Handle entity_type filter
    entity_type = args.get("entity_type")
    if entity_type:
        filters.append(DynamicField.entity_type == entity_type)

    # Handle boolean filters
    active = args.get("active")
    if active is not None and active.strip():
        filters.append(DynamicField.active == (active.lower() == "true"))

    searchable = args.get("searchable")
    if searchable is not None and searchable.strip():
        filters.append(DynamicField.searchable == (searchable.lower() == "true"))

    core = args.get("core")
    if core is not None and core.strip():
        filters.append(DynamicField.core == (core.lower() == "true"))

    # Handle field_type filter
    field_type = args.get("field_type")
    if field_type:
        filters.append(DynamicField.field_type == field_type)

    return filters


def parse_sort(args):
    """
    Parse the 'sort' query parameter and return a SQLAlchemy order_by clause.
    Supports sorting by regular fields and nested JSONB keys.
    Use '-field' for descending order.
    Example: ?sort=ui_config.sort_order or ?sort=-name
    """

    sort = args.get("sort")
    if not sort:
        return DynamicField.id.asc()
    direction = asc
    if sort.startswith("-"):
        direction = desc
        sort = sort[1:]

    # Block JSONB subfield sorting (not used in app, potential security risk)
    if "." in sort:
        return DynamicField.id.asc()

    # Handle regular field sorting
    if hasattr(DynamicField, sort):
        return direction(getattr(DynamicField, sort))
    return DynamicField.id.asc()


@admin.get("/api/dynamic-fields/")
def api_dynamic_fields():
    """
    List dynamic fields with optional filtering, sorting, and pagination.
    Also includes core fields for bulletin entity type.
    Query params:
      entity_type=value         (e.g. ?entity_type=bulletin)
      active=true/false         (e.g. ?active=true)
      searchable=true/false     (e.g. ?searchable=true)
      core=true/false           (e.g. ?core=false)
      field_type=value          (e.g. ?field_type=text)
      sort=field or sort=-field (e.g. ?sort=sort_order)
      limit, offset             (e.g. ?limit=10&offset=0)
    Returns a JSON response with 'data' (list of fields) and 'meta' (pagination info).
    """
    try:

        filters = parse_filters(request.args)
        sort_clause = parse_sort(request.args)

        # No default limit - return all fields by default (form builders need complete data)
        # Max cap of 1000 for safety
        MAX_LIMIT = 1000
        try:
            limit_param = request.args.get("limit")
            if limit_param is None:
                limit = None  # No limit = return all
            else:
                limit = int(limit_param)
                if limit > MAX_LIMIT:
                    return HTTPResponse.error(f"Limit cannot exceed {MAX_LIMIT}", status=400)
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return HTTPResponse.error("Invalid limit or offset", status=400)

        stmt = select(DynamicField).where(*filters).order_by(sort_clause).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        count_stmt = select(func.count()).select_from(DynamicField).where(*filters)
        total = db.session.execute(count_stmt).scalar_one()
        items = db.session.execute(stmt).scalars().all()
        data = [item.to_dict() for item in items]

        # Core fields are now stored in the database like regular dynamic fields
        # No special handling needed - they're included in the main query

        meta = {"total": total, "limit": limit, "offset": offset}
        return HTTPResponse.success(data={"data": data, "meta": meta})
    except Exception as e:
        logger.error(f"Error retrieving dynamic fields: {str(e)}", exc_info=True)
        return HTTPResponse.error(
            "An internal error occurred while retrieving dynamic fields", status=500
        )


@admin.post("/api/dynamic-fields/bulk-save")
@roles_required("Admin")
@validate_with(DynamicFieldBulkSaveModel)
def api_dynamic_fields_bulk_save(validated_data: dict) -> Response:
    """
    Bulk save dynamic fields (create, update, delete) in a single transaction.
    Creates only one history snapshot after all changes are applied.

    Request body:
        {
            "entity_type": "bulletin|actor|incident",
            "changes": {
                "create": [{ field_data }, ...],
                "update": [{ "id": 123, "item": { field_data } }, ...],
                "delete": [field_id, ...]
            }
        }

    Returns:
        Response with all active fields for the entity type
    """
    try:
        entity_type = validated_data["entity_type"]
        changes = validated_data.get("changes", {})

        created_count = 0
        updated_count = 0
        deleted_count = 0

        # All operations in single transaction
        # Creates
        for item in changes.get("create", []):
            field_title = item.get("title", "Unknown")
            field, error = create_field(item, entity_type)
            if error:
                db.session.rollback()
                status = 500 if error.startswith("Database error:") else 400

                return HTTPResponse.error(
                    f"Failed to create field '{field_title}'", status=status, errors=[error]
                )
            created_count += 1

        # Updates
        for update_item in changes.get("update", []):
            field_id = update_item.get("id")
            if not field_id:
                continue
            item_data = update_item.get("item", {})
            field_title = item_data.get("title", f"ID {field_id}")
            field, error = update_field(field_id, item_data)
            if error:
                db.session.rollback()
                if "not found" in error.lower():
                    status = 404
                elif error.startswith("Database error:"):
                    status = 500
                else:
                    status = 400
                return HTTPResponse.error(
                    f"Failed to update field '{field_title}'", status=status, errors=[error]
                )
            updated_count += 1

        # Deletes
        for field_id in changes.get("delete", []):
            if not field_id or str(field_id).startswith("temp-"):
                continue
            field, error = delete_field(field_id)
            if error:
                # For deletes, log warning but continue (non-blocking)
                logger.warning(f"Failed to delete field ID {field_id}: {error}")
                continue
            deleted_count += 1

        # Commit all changes at once
        db.session.commit()

        # Log activity after successful commit
        if created_count > 0 or updated_count > 0 or deleted_count > 0:
            Activity.create(
                current_user,
                Activity.ACTION_UPDATE,
                Activity.STATUS_SUCCESS,
                {
                    "entity_type": entity_type,
                    "created": created_count,
                    "updated": updated_count,
                    "deleted": deleted_count,
                },
                "dynamic_field_bulk",
            )

        # Record single history snapshot
        try:
            record_form_history(entity_type, current_user.id)
        except Exception as e:
            logger.warning(f"Failed to record form history for {entity_type}: {e}")

        # Return all fields (including inactive and deleted)
        stmt = (
            select(DynamicField)
            .where(DynamicField.entity_type == entity_type)
            .order_by(DynamicField.sort_order)
        )
        fields = db.session.execute(stmt).scalars().all()

        return HTTPResponse.success(
            message=f"Bulk save completed: {created_count} created, {updated_count} updated, {deleted_count} deleted",
            data={"fields": [f.to_dict() for f in fields]},
        )

    except Exception as e:
        logger.error(f"Error in bulk save: {str(e)}")
        db.session.rollback()
        return HTTPResponse.error("Bulk save failed", status=500)


@admin.get("/api/dynamic-fields/history/<entity_type>")
@roles_required("Admin")
def api_dynamic_fields_history(entity_type):
    """
    Get history of dynamic form changes for an entity type.

    Args:
        entity_type: The entity type (actor, bulletin, incident)

    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 20)

    Returns:
        Paginated list of history snapshots ordered by created_at DESC
    """
    try:
        # Validate entity_type
        if entity_type not in ["actor", "bulletin", "incident"]:
            return HTTPResponse.error("Invalid entity type", status=400)

        # Get pagination params
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        if page < 1 or per_page < 1 or per_page > 100:
            return HTTPResponse.error("Invalid pagination parameters", status=400)

        # Query history with pagination
        stmt = (
            select(DynamicFormHistory)
            .where(DynamicFormHistory.entity_type == entity_type)
            .order_by(DynamicFormHistory.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        count_stmt = (
            select(func.count())
            .select_from(DynamicFormHistory)
            .where(DynamicFormHistory.entity_type == entity_type)
        )

        total = db.session.execute(count_stmt).scalar_one()
        items = db.session.execute(stmt).scalars().all()

        return HTTPResponse.success(
            data={
                "items": [item.to_dict() for item in items],
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching history for {entity_type}: {str(e)}")
        return HTTPResponse.error("Failed to fetch history", status=500)


@admin.route("/api/session-check")
@auth_required("session")
def api_session_check() -> Response:
    """
    Lightweight endpoint to check if current session is still valid.
    Used by frontend to detect when session is restored after expiration.

    Returns:
        - 200: Session is valid
        - 401: Session expired (handled by auth decorator)
    """
    return jsonify({"status": "valid"})
