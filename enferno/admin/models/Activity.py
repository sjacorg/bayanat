from typing import Any, Optional

from sqlalchemy import JSON

import enferno.utils.typing as t
from enferno.extensions import db
from enferno.settings import Config
from enferno.user.models import User
from enferno.utils.base import BaseMixin
from enferno.utils.date_helper import DateHelper
from enferno.utils.logging_utils import get_logger

logger = get_logger()


class Activity(db.Model, BaseMixin):
    """
    SQL Alchemy model for activity
    """

    STATUS_SUCCESS = "SUCCESS"
    STATUS_DENIED = "DENIED"

    ACTION_VIEW = "VIEW"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_CREATE = "CREATE"
    ACTION_REVIEW = "REVIEW"
    ACTION_UPLOAD = "UPLOAD"
    ACTION_BULK_UPDATE = "BULK"
    ACTION_REQUEST_EXPORT = "REQUEST"
    ACTION_APPROVE_EXPORT = "APPROVE"
    ACTION_REJECT_EXPORT = "REJECT"
    ACTION_DOWNLOAD = "DOWNLOAD"
    ACTION_SEARCH = "SEARCH"
    ACTION_SELF_ASSIGN = "SELF-ASSIGN"
    ACTION_LOGIN = "LOGIN"
    ACTION_LOGOUT = "LOGOUT"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)
    action = db.Column(db.String(100))
    status = db.Column(db.String(100))
    model = db.Column(db.String(100))
    subject = db.Column(JSON)
    details = db.Column(db.Text)

    @staticmethod
    def get_action_values() -> list[str]:
        """Return a list of action values."""
        return [getattr(Activity, attr) for attr in dir(Activity) if attr.startswith("ACTION_")]

    # serialize data
    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the activity."""
        # Ensure self.subject is a dictionary.
        if isinstance(self.subject, dict) and self.subject.get("class") == "user":
            user_id = self.subject.get("id")
            if user_id:
                user = User.query.get(user_id)
                if user:
                    # Directly add the username to the subject dictionary.
                    self.subject["username"] = user.username

        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "status": self.status,
            "subject": self.subject,  # Now includes the username if applicable.
            "model": self.model,
            "details": self.details,
            "created_at": DateHelper.serialize_datetime(self.created_at),
        }

    # helper static method to create different type of activities (tags)
    @staticmethod
    def create(
        user: "User",
        action: str,
        status: str,
        subject: dict,
        model: str,
        details: Optional[str] = None,
    ) -> None:
        """
        Create an activity.

        Args:
            - user: the user object.
            - action: the action.
            - status: the status.
            - subject: the subject dict (e.g. from to_mini()).
            - model: the model.
            - details: the details.
        """
        # this will check if the action is
        # enabled in system settings
        # if disabled the activity will not be logged
        # denied actions will be always logged
        if not status == Activity.STATUS_DENIED and not action in Config.get("ACTIVITIES_LIST"):
            return

        try:
            activity = Activity()
            activity.user_id = user.id
            activity.action = action
            activity.status = status
            activity.subject = subject
            activity.model = model
            activity.details = details
            activity.save()

        except Exception:
            logger.error("Error creating activity", exc_info=True)
