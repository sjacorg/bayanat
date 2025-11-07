"""Utilities for dynamic form history tracking."""

from enferno.extensions import db
from enferno.admin.models.DynamicField import DynamicField
from enferno.admin.models.DynamicFormHistory import DynamicFormHistory
from enferno.utils.logging_utils import get_logger

logger = get_logger()


def record_form_history(entity_type: str, user_id: int) -> DynamicFormHistory:
    """
    Record a snapshot of the current form layout for an entity type.

    Captures ALL fields (active, inactive, deleted) to enable accurate
    diff comparison and complete audit trail.

    Args:
        entity_type: The entity being modified (bulletin, actor, incident)
        user_id: ID of the user making the change

    Returns:
        The created DynamicFormHistory record
    """
    fields = (
        DynamicField.query.filter_by(entity_type=entity_type)
        .order_by(DynamicField.sort_order)
        .all()
    )

    history_entry = DynamicFormHistory(
        entity_type=entity_type,
        fields_snapshot=[f.to_dict() for f in fields],
        user_id=user_id,
    )

    try:
        db.session.add(history_entry)
        db.session.commit()
        logger.info(f"Recorded form history for {entity_type} by user {user_id}")
        return history_entry
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to record form history for {entity_type}: {e}")
        raise
