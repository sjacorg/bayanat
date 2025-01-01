import json
from typing import Any

from sqlalchemy import JSON

from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.logging_utils import get_logger
from enferno.admin.models import Bulletin, Actor, Incident

logger = get_logger()


class Query(db.Model, BaseMixin):
    """
    SQL Alchemy model for saved searches
    """

    TYPES = [Bulletin.__tablename__, Actor.__tablename__, Incident.__tablename__]

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="unique_user_queryname"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="queries", foreign_keys=[user_id])
    data = db.Column(JSON)
    query_type = db.Column(db.String, nullable=False, default=Bulletin.__tablename__)

    # serialize data
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the query."""
        return {"id": self.id, "name": self.name, "data": self.data, "query_type": self.query_type}

    def to_json(self) -> str:
        """Return a JSON representation of the query."""
        return json.dumps(self.to_dict())
