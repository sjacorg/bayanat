from typing import Any

from sqlalchemy.dialects.postgresql import JSONB

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper


class DynamicFormHistory(db.Model, BaseMixin):
    """
    Audit trail for dynamic form layout changes.

    Stores snapshots of active dynamic fields whenever the form builder is updated.
    Each row captures:
    - entity_type: The entity being modified (bulletin, actor, incident)
    - fields_snapshot: Ordered list of active field definitions at the time of change
    - user_id: Who made the change
    - created_at: When the change occurred (inherited from BaseMixin)
    """

    __tablename__ = "dynamic_form_history"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)  # bulletin, actor, incident
    fields_snapshot = db.Column(JSONB, nullable=False)  # Ordered list of field dicts

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="form_histories", foreign_keys=[user_id])

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the history entry."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "fields_snapshot": self.fields_snapshot,
            "created_at": DateHelper.serialize_datetime(self.created_at),
            "user": self.user.to_dict() if self.user else {},
        }
