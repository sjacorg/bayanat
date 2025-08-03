import json
from typing import Any, Optional

from dateutil.parser import parse
from sqlalchemy import and_, or_, func

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Event(db.Model, BaseMixin):
    """
    SQL Alchemy model for events
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    title_ar = db.Column(db.String, index=True)
    comments = db.Column(db.String)
    comments_ar = db.Column(db.String)

    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), index=True)
    location = db.relationship("Location", backref="location_events", foreign_keys=[location_id])
    eventtype_id = db.Column(db.Integer, db.ForeignKey("eventtype.id"), index=True)
    eventtype = db.relationship(
        "Eventtype", backref="eventtype_events", foreign_keys=[eventtype_id]
    )
    from_date = db.Column(db.DateTime)
    to_date = db.Column(db.DateTime)
    estimated = db.Column(db.Boolean)

    @staticmethod
    def get_event_filters(
        dates: Optional[list] = None,
        eventtype_id: Optional[t.id] = None,
        event_location_id: Optional[t.id] = None,
    ) -> list:
        """
        Get the filters for querying events based on the given parameters.

        Args:
            - dates: list of dates to filter by.
            - eventtype_id: the event type id to filter by.
            - event_location_id: the event location id to filter by.

        Returns:
            - list of conditions to filter by.
        """
        conditions = []

        if dates:
            start_date = parse(dates[0]).date()
            if len(dates) == 1:
                end_date = start_date
            else:
                end_date = parse(dates[1]).date()

            date_condition = or_(
                and_(
                    func.date(Event.from_date) <= start_date, func.date(Event.to_date) >= end_date
                ),
                func.date(Event.from_date).between(start_date, end_date),
                func.date(Event.to_date).between(start_date, end_date),
            )
            conditions.append(date_condition)

        if event_location_id:
            conditions.append(Event.location_id == event_location_id)
        if eventtype_id:
            conditions.append(Event.eventtype_id == eventtype_id)

        return conditions

    # custom serialization method
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the event."""
        return {
            "id": self.id,
            "title": self.title if self.title else None,
            "title_ar": self.title_ar if self.title_ar else None,
            "comments": self.comments if self.comments else None,
            "comments_ar": self.comments_ar if self.comments_ar else None,
            "location": self.location.to_dict() if self.location else None,
            "eventtype": self.eventtype.to_dict() if self.eventtype else None,
            "from_date": DateHelper.serialize_datetime(self.from_date) if self.from_date else None,
            "to_date": DateHelper.serialize_datetime(self.to_date) if self.to_date else None,
            "estimated": self.estimated if self.estimated else None,
            "updated_at": DateHelper.serialize_datetime(self.updated_at),
        }

    def to_json(self) -> str:
        """Return a JSON representation of the event."""
        return json.dumps(self.to_dict())

    # populates model from json dict
    def from_json(self, json: dict[str, Any]) -> "Event":
        """
        Create an event object from a json dictionary.

        Args:
            - json: the json dictionary to create the event from.

        Returns:
            - the event object.
        """
        self.title = json["title"] if "title" in json else None
        self.title_ar = json["title_ar"] if "title_ar" in json else None
        self.comments = json["comments"] if "comments" in json else None
        self.comments_ar = json["comments_ar"] if "comments_ar" in json else None

        self.location_id = (
            json["location"]["id"] if "location" in json and json["location"] else None
        )
        self.eventtype_id = (
            json["eventtype"]["id"] if "eventtype" in json and json["eventtype"] else None
        )

        from_date = json.get("from_date", None)
        self.from_date = DateHelper.parse_date(from_date) if from_date else None

        to_date = json.get("to_date", None)
        self.to_date = DateHelper.parse_date(to_date) if to_date else None

        self.estimated = json["estimated"] if "estimated" in json else None

        return self
