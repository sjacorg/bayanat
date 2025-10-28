"""Utilities for dynamic field CRUD operations.

Contains core business logic for creating, updating, and deleting dynamic fields.
Used by both single-field endpoints and the bulk-save endpoint.

Key characteristics:
- No HTTP request/response handling
- No db.session.commit() - caller controls transactions
- Returns (result, error_message) tuples for consistent error handling
"""

import time
from uuid import uuid4

from sqlalchemy import select

from enferno.admin.models import DynamicField
from enferno.extensions import db
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def create_field(field_data, entity_type):
    """
    Create a new dynamic field.

    Args:
        field_data: Dictionary containing validated field configuration (from Pydantic)
        entity_type: Entity type (bulletin, actor, incident) - already validated

    Returns:
        Tuple of (field, error_message). If successful, error_message is None.
    """
    # Generate unique field name
    timestamp_ms = int(time.time() * 1000)
    random_suffix = uuid4().hex[:6]
    field_data["name"] = f"field_{timestamp_ms}_{random_suffix}"

    # Handle schema_config
    schema_config = field_data.get("schema_config", {})
    if "required" in field_data:
        schema_config["required"] = field_data["required"]

    # Create field instance
    field = DynamicField(
        name=field_data["name"],
        title=field_data["title"],
        entity_type=entity_type,
        field_type=field_data["field_type"],
        ui_component=field_data.get("ui_component"),
        schema_config=schema_config,
        ui_config=field_data.get("ui_config", {}),
        validation_config=field_data.get("validation_config", {}),
        options=field_data.get("options", []),
        active=field_data.get("active", True),
        searchable=field_data.get("searchable", False),
        sort_order=field_data.get("sort_order", 0),
    )

    # Validate using model logic
    try:
        field.validate_field()
    except ValueError as e:
        return None, str(e)

    # Ensure options have IDs for select fields
    if field.field_type == DynamicField.SELECT:
        field.ensure_option_ids()

    # Add to session and create column
    try:
        db.session.add(field)
        db.session.flush()  # Get the ID without committing
        field.create_column()
    except Exception as e:
        logger.error(f"Failed to create field: {e}", exc_info=True)
        return None, f"Database error: {str(e)}"

    return field, None


def update_field(field_id, field_data):
    """
    Update an existing dynamic field.

    Args:
        field_id: ID of the field to update
        field_data: Dictionary containing validated updated field configuration (from Pydantic)

    Returns:
        Tuple of (field, error_message). If successful, error_message is None.
    """
    # Get field
    stmt = select(DynamicField).where(DynamicField.id == field_id)
    field = db.session.execute(stmt).scalars().first()

    if not field:
        return None, "Field not found"

    # Store original values
    original_name = field.name
    original_field_type = field.field_type

    # Prevent name changes
    if field_data.get("name") and field_data["name"] != original_name:
        return None, "Field name cannot be changed"

    # Prevent field type changes
    if field_data.get("field_type") and field_data["field_type"] != original_field_type:
        return None, "Cannot change field type"

    # Apply updates based on field type
    if field.core:
        # Core fields can only update: title, active, sort_order
        field.title = field_data.get("title", field.title)
        field.active = field_data.get("active", field.active)
        field.sort_order = field_data.get("sort_order", field.sort_order)

        # Clear deleted flag when reactivating
        if field.active and field.deleted:
            field.deleted = False
    else:
        # Handle schema_config
        schema_config = field_data.get("schema_config", {})
        if "required" in field_data:
            schema_config["required"] = field_data["required"]

        # Prevent max_length changes for text fields
        if field.field_type == "text":
            old_max_length = field.schema_config.get("max_length")
            new_max_length = schema_config.get("max_length")
            if old_max_length != new_max_length:
                return None, "Cannot change max_length after field creation"

        # Custom fields can update everything
        field.title = field_data.get("title", field.title)
        field.entity_type = field_data.get("entity_type", field.entity_type)
        field.ui_component = field_data.get("ui_component", field.ui_component)
        field.schema_config = schema_config
        field.ui_config = field_data.get("ui_config", field.ui_config or {})
        field.validation_config = field_data.get("validation_config", field.validation_config or {})
        field.options = field_data.get("options", field.options or [])
        field.active = field_data.get("active", field.active)
        field.searchable = field_data.get("searchable", field.searchable)
        field.sort_order = field_data.get("sort_order", field.sort_order)

        # Clear deleted flag when reactivating
        if field.active and field.deleted:
            field.deleted = False

        # Validate updated field (custom fields only)
        try:
            field.validate_field()
        except ValueError as e:
            return None, str(e)

        # Ensure options have IDs for select fields
        if field.field_type == DynamicField.SELECT:
            field.ensure_option_ids()

    # Add to session
    try:
        db.session.add(field)
        db.session.flush()
    except Exception as e:
        logger.error(f"Failed to update field: {e}", exc_info=True)
        return None, f"Database error: {str(e)}"

    return field, None


def delete_field(field_id):
    """
    Soft-delete a dynamic field by marking it inactive and deleted.

    Args:
        field_id: ID of the field to delete

    Returns:
        Tuple of (field, error_message). If successful, error_message is None.
    """
    # Get field
    stmt = select(DynamicField).where(DynamicField.id == field_id)
    field = db.session.execute(stmt).scalars().first()

    if not field:
        return None, "Field not found"

    # Soft delete: mark inactive AND deleted
    field.active = False
    field.deleted = True

    try:
        db.session.add(field)
        db.session.flush()
    except Exception as e:
        logger.error(f"Failed to delete field: {e}", exc_info=True)
        return None, f"Database error: {str(e)}"

    return field, None
